from __future__ import annotations

import re
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal

from prismguard.config.loader import TriageConfig, load_triage_config
from prismguard.runtime.fusion import fuse_signals
from prismguard.runtime.guard_model import GuardModel, GuardModelVerdict
from prismguard.runtime.llm_judge import LLMJudge
from prismguard.runtime.normalize import normalize_prompt
from prismguard.runtime.thresholds import resolve_thresholds
from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.embedder import Embedder, create_embedder

if TYPE_CHECKING:
    from prismguard.feedback.review import FeedbackReviewService
from prismguard.taxonomy.graph import TaxonomyGraphEngine
from prismguard.taxonomy.ingest import ingest_seed_vectors, iter_all_seed_entries
from prismguard.taxonomy.mapping import TaxonomyEngine, build_mapping_from_parsed_seed

Decision = Literal["block", "allow", "gray"]
ResolutionGate = Literal[
    "tier1_rule",
    "corpus_match",
    "benign_fast_path",
    "fusion_block",
    "fusion_allow",
    "fusion_gray",
    "fusion_gray_fail_open",
    "fusion_gray_fail_closed",
    "guard_model",
    "llm_judge",
    "uninitialized",
]


class CheckOutcome(str, Enum):
    BLOCK = "block"
    ALLOW = "allow"
    GRAY = "gray"


@dataclass
class CheckResult:
    decision: Decision
    resolution_gate: ResolutionGate
    fused_score: float = 0.0
    attack_sim: float = 0.0
    benign_sim: float = 0.0
    matched_category: str | None = None
    matched_rule_id: str | None = None
    top_attack_entry_id: str | None = None
    normalized_prompt: str = ""
    details: dict = field(default_factory=dict)


def route_fusion_decision(
    *,
    fused_score: float,
    weak_signal_count: int,
    block_threshold: float,
    allow_threshold: float,
    min_weak_signals_for_gray: int,
) -> tuple[Decision, ResolutionGate]:
    """Return (decision, resolution_gate) from fusion scores."""
    if fused_score >= block_threshold:
        return "block", "fusion_block"
    if fused_score <= allow_threshold:
        return "allow", "fusion_allow"
    if weak_signal_count >= min_weak_signals_for_gray:
        return "gray", "fusion_gray"
    return "allow", "fusion_allow"


def guard_model_required(config: TriageConfig) -> bool:
    """True when runtime should attempt to load/use a Guard Model."""
    if not config.guard_model.enabled:
        return False
    return config.guard_model.classifier_mode == "parallel" or config.gray_zone_policy == "escalate"


def guard_model_required_at_init(config: TriageConfig) -> bool:
    """Strict init check — escalate policy must have a model; parallel degrades if missing."""
    return config.guard_model.enabled and config.gray_zone_policy == "escalate"


class RuntimeChecker:
    """
    Tiered firewall: normalize → Tier-1 → dual ANN → fusion → gray policy →
    Guard Model (Phase 2) → LLM Judge (Phase 3, uncertain guard only).
    """

    def __init__(
        self,
        storage: StorageBackend,
        engine: TaxonomyEngine,
        *,
        embedder: Embedder | None = None,
        config: TriageConfig | None = None,
        guard_model: GuardModel | None = None,
        llm_judge: LLMJudge | None = None,
        feedback_review: FeedbackReviewService | None = None,
    ) -> None:
        self._storage = storage
        self._engine = engine
        self._embedder = embedder or create_embedder(prefer_transformer=False)
        self._config = config or load_triage_config()
        self._guard_model = guard_model
        self._llm_judge = llm_judge
        self._feedback_review = feedback_review
        self._judge_circuit_open = False
        self._classifier_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prismguard-clf")
        if guard_model_required_at_init(self._config) and self._guard_model is None:
            raise ValueError(
                "gray_zone_policy='escalate' requires a configured GuardModel at RuntimeChecker init"
            )
        seed_texts: list[tuple[str, str]] = []
        for category in storage.relational.list_categories():
            for entry in storage.vector.list_seed_entries_by_category(category.slug):
                if entry.raw_text:
                    seed_texts.append((entry.raw_text, entry.category_slug))
        self._graph_engine = TaxonomyGraphEngine.from_mapping(
            mapping_dict=engine.mapping_dict,
            embedder=self._embedder,
            attack_categories=engine.attack_categories,
            seed_texts=seed_texts[:800],
        )

    @classmethod
    def from_storage(
        cls,
        storage: StorageBackend,
        parsed_seed,
        *,
        embedder: Embedder | None = None,
        config: TriageConfig | None = None,
        force_embed: bool = False,
        guard_model: GuardModel | None = None,
        llm_judge: LLMJudge | None = None,
        feedback_review: FeedbackReviewService | None = None,
    ) -> RuntimeChecker:
        engine = build_mapping_from_parsed_seed(parsed_seed)
        emb = embedder or create_embedder(prefer_transformer=False)
        from prismguard.taxonomy.constants import CATEGORY_VECTOR_DIM

        needs_embed = force_embed or any(
            not (
                e.embedding_semantic
                and e.embedding_category
                and len(e.embedding_category) == CATEGORY_VECTOR_DIM
            )
            for e in iter_all_seed_entries(storage)
        )
        if needs_embed:
            ingest_seed_vectors(storage, engine, emb, force=force_embed)
        config = config or load_triage_config()
        if guard_model is None and guard_model_required(config):
            from prismguard.runtime.guard_model import create_guard_model

            guard_model = create_guard_model(config.guard_model)
        if guard_model is None and config.gray_zone_policy == "escalate":
            config = config.model_copy(update={"gray_zone_policy": "fail_closed"})
        if guard_model is None and config.guard_model.classifier_mode == "parallel":
            config = config.model_copy(update={"guard_model": config.guard_model.model_copy(update={"classifier_mode": "gray_only"})})
        return cls(
            storage,
            engine,
            embedder=emb,
            config=config,
            guard_model=guard_model,
            llm_judge=llm_judge,
            feedback_review=feedback_review,
        )

    def _record_feedback(self, *, prompt: str, result: CheckResult, origin: str) -> None:
        if self._feedback_review is None:
            return
        category = result.matched_category or "direct_instruction_override"
        if result.decision == "block":
            self._feedback_review.enqueue_block(
                prompt=prompt,
                check_result=result,
                origin="llm_judge" if origin == "llm_judge" else "guard_model",
                category_slug=category,
            )
        elif result.decision == "allow" and origin in ("guard_model", "llm_judge"):
            self._feedback_review.record_near_miss_allow(
                prompt=prompt,
                check_result=result,
                origin="llm_judge" if origin == "llm_judge" else "guard_model",
            )

    @property
    def guard_model_call_count(self) -> int:
        if self._guard_model is None:
            return 0
        return getattr(self._guard_model, "call_count", 0)

    @property
    def llm_judge_call_count(self) -> int:
        if self._llm_judge is None:
            return 0
        return getattr(self._llm_judge, "call_count", 0)

    def _effective_config(self) -> TriageConfig:
        if not self._judge_circuit_open:
            return self._config
        cfg = self._config.model_copy(deep=True)
        cfg.triage.block_threshold = max(
            0.5,
            cfg.triage.block_threshold - cfg.judge.tighten_block_threshold_delta,
        )
        cfg.fusion.weak_signal_floor = min(
            0.9,
            cfg.fusion.weak_signal_floor + cfg.judge.tighten_weak_signal_floor_delta,
        )
        return cfg

    def _nearest_seed_examples(self, normalized: str, category_slug: str | None, *, limit: int = 3) -> list[dict]:
        slugs = [category_slug] if category_slug else list(self._engine.attack_categories)
        if not slugs:
            return []
        hits = self._storage.vector.ann_search_semantic(
            self._embedder.embed_semantic(normalized),
            category_slugs=list(slugs),
            top_k=limit,
        )
        return [
            {
                "text": hit.chunk_text[:240],
                "category_slug": hit.category_slug,
                "score": round(hit.score, 4),
            }
            for hit in hits
        ]

    def _graph_connectivity_score(self, text: str, category_slug: str | None) -> float:
        if self._graph_engine.ready:
            return self._graph_engine.graph_connectivity_score(text, category_slug)
        if not category_slug:
            return 0.0
        tokens = set(re.findall(r"[a-z0-9]{4,}", text.lower()))
        rule_tokens: set[str] = set()
        for rule in self._engine.regex_rules:
            if rule.category_slug != category_slug:
                continue
            rule_tokens.update(re.findall(r"[a-z]{4,}", rule.pattern.lower()))
        for word, cat in self._engine._substring_rules:
            if cat == category_slug:
                rule_tokens.add(word)
        if not rule_tokens:
            return 0.0
        overlap = len(tokens & rule_tokens)
        return min(1.0, overlap / max(1.0, len(rule_tokens) * 0.35))

    def _community_confidence(
        self,
        semantic_vector: list[float],
        category_slug: str | None,
        *,
        rule_matched: bool,
    ) -> float:
        if self._graph_engine.ready:
            return self._graph_engine.community_confidence(
                semantic_vector,
                category_slug,
                rule_matched=rule_matched,
            )
        if rule_matched and category_slug:
            return 1.0
        return 0.5 if category_slug else 0.0

    def _uses_parallel_classifier(self) -> bool:
        return (
            self._config.guard_model.enabled
            and self._config.guard_model.classifier_mode == "parallel"
            and self._guard_model is not None
        )

    def _start_parallel_classifier(self, prompt: str) -> Future[GuardModelVerdict] | None:
        if not self._uses_parallel_classifier():
            return None
        return self._classifier_executor.submit(self._guard_model.check, prompt)  # type: ignore[union-attr]

    def _collect_classifier_verdict(
        self,
        future: Future[GuardModelVerdict] | None,
    ) -> GuardModelVerdict | None:
        if future is None:
            return None
        return future.result()

    @staticmethod
    def _classifier_details(verdict: GuardModelVerdict) -> dict:
        return {
            "classifier_fused": True,
            "classifier_mode": "parallel",
            "guard_model_id": verdict.model_id,
            "guard_model_confidence": verdict.confidence,
            "guard_model_latency_ms": verdict.latency_ms,
            "guard_model_verdict": verdict.decision,
            "guard_model_details": verdict.details,
            "classifier_prob": verdict.confidence,
        }

    def _resolve_gray(
        self,
        *,
        prompt: str,
        normalized: str,
        fusion_details: dict,
        matched_category: str | None,
    ) -> CheckResult:
        policy = self._config.gray_zone_policy
        base_details = {
            **fusion_details,
            "gray_zone_policy": policy,
            "gray_origin": "fusion_gray",
        }

        if policy == "fail_open":
            return CheckResult(
                decision="allow",
                resolution_gate="fusion_gray_fail_open",
                matched_category=matched_category,
                normalized_prompt=normalized,
                details={**base_details, "decision_source": "fusion_gray→fail_open"},
            )

        if policy == "fail_closed":
            return CheckResult(
                decision="block",
                resolution_gate="fusion_gray_fail_closed",
                matched_category=matched_category,
                normalized_prompt=normalized,
                details={**base_details, "decision_source": "fusion_gray→fail_closed"},
            )

        if fusion_details.get("classifier_fused") and "guard_model_verdict" in fusion_details:
            verdict_decision = str(fusion_details["guard_model_verdict"])
            guard_details = {**base_details, **{k: fusion_details[k] for k in fusion_details if k.startswith("guard_model") or k.startswith("classifier")}}
            guard_details["decision_source"] = "fusion_gray→parallel_classifier"
        else:
            verdict = self._guard_model.check(prompt, context=fusion_details)  # type: ignore[union-attr]
            guard_details = {
                **base_details,
                **self._classifier_details(verdict),
            }
            verdict_decision = verdict.decision

        if verdict_decision == "uncertain" and self._llm_judge is not None:
            if self._judge_circuit_open and self._config.judge.accept_guard_at_lower_confidence_when_capped:
                risk = guard_details.get("guard_model_confidence")
                if isinstance(risk, (int, float)):
                    forced: Decision = "block" if float(risk) >= 0.5 else "allow"
                    result = CheckResult(
                        decision=forced,
                        resolution_gate="guard_model",
                        matched_category=matched_category,
                        normalized_prompt=normalized,
                        details={
                            **guard_details,
                            "decision_source": "fusion_gray→guard_model_capped_fallback",
                        },
                    )
                    self._record_feedback(prompt=prompt, result=result, origin="guard_model")
                    return result
            judge_context = {
                **guard_details,
                "matched_category": matched_category,
                "nearest_seed_examples": self._nearest_seed_examples(normalized, matched_category),
            }
            judge = self._llm_judge.judge(prompt, context=judge_context)
            if judge.details.get("circuit_breaker"):
                self._judge_circuit_open = True
            final_decision: Decision = judge.decision
            result = CheckResult(
                decision=final_decision,
                resolution_gate="llm_judge",
                matched_category=matched_category,
                normalized_prompt=normalized,
                details={
                    **guard_details,
                    "llm_judge_confidence": judge.confidence,
                    "llm_judge_latency_ms": judge.latency_ms,
                    "llm_judge_reasoning": judge.reasoning,
                    "decision_source": "fusion_gray→guard_model_uncertain→llm_judge",
                },
            )
            self._record_feedback(prompt=prompt, result=result, origin="llm_judge")
            return result

        if verdict_decision == "block":
            result = CheckResult(
                decision="block",
                resolution_gate="guard_model",
                matched_category=matched_category,
                normalized_prompt=normalized,
                details={**guard_details, "decision_source": "fusion_gray→guard_model"},
            )
            self._record_feedback(prompt=prompt, result=result, origin="guard_model")
            return result

        result = CheckResult(
            decision="allow",
            resolution_gate="guard_model",
            matched_category=matched_category,
            normalized_prompt=normalized,
            details={**guard_details, "decision_source": "fusion_gray→guard_model"},
        )
        self._record_feedback(prompt=prompt, result=result, origin="guard_model")
        return result

    def check(self, prompt: str, *, session_id: str | None = None) -> CheckResult:
        normalized = normalize_prompt(
            prompt,
            max_obfuscation_depth=self._config.normalization.max_obfuscation_depth,
        )

        tier1 = self._engine.match_tier1(normalized)
        if tier1 is not None:
            return CheckResult(
                decision="block",
                resolution_gate="tier1_rule",
                matched_category=tier1.category_slug,
                matched_rule_id=tier1.rule_id,
                normalized_prompt=normalized,
                details={"severity": tier1.severity},
            )

        classifier_future = self._start_parallel_classifier(prompt)

        semantic = self._embedder.embed_semantic(normalized)
        slug = self._engine.assign_category(normalized)
        category_vec = self._engine.remap_category_vector(
            normalized, semantic, category_slug=slug
        )

        attack_slugs = list(self._engine.attack_categories)
        benign_slug = self._engine.benign_category

        attack_hits = self._storage.vector.ann_search_semantic(
            semantic,
            category_slugs=attack_slugs,
            top_k=5,
        )
        benign_hits = self._storage.vector.ann_search_semantic(
            semantic,
            category_slugs=[benign_slug],
            top_k=3,
        )
        cat_hits = self._storage.vector.ann_search_category(
            category_vec,
            category_slugs=attack_slugs,
            top_k=3,
        )

        attack_sim = max((h.score for h in attack_hits), default=0.0)
        cat_sim = max((h.score for h in cat_hits), default=0.0)
        attack_sim = max(attack_sim, cat_sim)
        benign_sim = max((h.score for h in benign_hits), default=0.0)

        matched_category = slug or (attack_hits[0].category_slug if attack_hits else None)
        active_config = self._effective_config()
        thresholds = resolve_thresholds(active_config, matched_category)
        cfg = active_config

        margin = attack_sim - benign_sim
        if (
            benign_sim >= thresholds.benign_allow_floor
            and margin <= -thresholds.benign_margin_delta
        ):
            return CheckResult(
                decision="allow",
                resolution_gate="benign_fast_path",
                attack_sim=attack_sim,
                benign_sim=benign_sim,
                normalized_prompt=normalized,
                matched_category=matched_category,
            )

        top_hit = attack_hits[0] if attack_hits else None
        rule_matched = bool(slug and slug in self._engine.attack_categories)
        graph_score = self._graph_connectivity_score(normalized, matched_category)
        community_confidence = self._community_confidence(
            semantic,
            matched_category,
            rule_matched=rule_matched,
        )

        if top_hit and top_hit.score >= thresholds.corpus_match_threshold:
            return CheckResult(
                decision="block",
                resolution_gate="corpus_match",
                attack_sim=attack_sim,
                benign_sim=benign_sim,
                matched_category=matched_category,
                top_attack_entry_id=top_hit.entry_id,
                normalized_prompt=normalized,
                details={
                    "attack_sim": attack_sim,
                    "benign_sim": benign_sim,
                    "corpus_match_score": top_hit.score,
                },
            )

        classifier_verdict = self._collect_classifier_verdict(classifier_future)
        classifier_prob = (
            classifier_verdict.confidence if classifier_verdict is not None else None
        )

        fusion = fuse_signals(
            attack_sim=attack_sim,
            benign_sim=benign_sim,
            rule_matched=rule_matched,
            severity=top_hit.severity if top_hit else "medium",
            graph_score=graph_score,
            community_confidence=community_confidence,
            classifier_prob=classifier_prob,
            w_sim=cfg.fusion.w_sim,
            w_graph=cfg.fusion.w_graph,
            w_rule=cfg.fusion.w_rule,
            w_sev=cfg.fusion.w_sev,
            w_comm=cfg.fusion.w_comm,
            w_clf=cfg.fusion.w_clf if classifier_prob is not None else 0.0,
            w_benign=cfg.fusion.w_benign,
            weak_signal_floor=cfg.fusion.weak_signal_floor,
        )

        fusion_details = {
            "session_id": session_id,
            "contrastive_margin": fusion.contrastive_margin,
            "weak_signal_count": fusion.weak_signal_count,
            "block_threshold": thresholds.block_threshold,
            "allow_threshold": thresholds.allow_threshold,
            "fused_score": fusion.fused_score,
            "attack_sim": attack_sim,
            "benign_sim": benign_sim,
            "graph_score": graph_score,
            "community_confidence": community_confidence,
            "classifier_prob": fusion.classifier_prob,
        }
        if classifier_verdict is not None:
            fusion_details.update(self._classifier_details(classifier_verdict))

        decision, gate = route_fusion_decision(
            fused_score=fusion.fused_score,
            weak_signal_count=fusion.weak_signal_count,
            block_threshold=thresholds.block_threshold,
            allow_threshold=thresholds.allow_threshold,
            min_weak_signals_for_gray=cfg.fusion.min_weak_signals_for_gray,
        )

        if decision == "gray" and gate == "fusion_gray":
            if self._config.gray_terminal:
                return CheckResult(
                    decision="gray",
                    resolution_gate="fusion_gray",
                    fused_score=fusion.fused_score,
                    attack_sim=attack_sim,
                    benign_sim=benign_sim,
                    matched_category=matched_category,
                    top_attack_entry_id=top_hit.entry_id if top_hit else None,
                    normalized_prompt=normalized,
                    details=fusion_details,
                )
            return self._resolve_gray(
                prompt=prompt,
                normalized=normalized,
                fusion_details=fusion_details,
                matched_category=matched_category,
            )

        return CheckResult(
            decision=decision,
            resolution_gate=gate,
            fused_score=fusion.fused_score,
            attack_sim=attack_sim,
            benign_sim=benign_sim,
            matched_category=matched_category,
            top_attack_entry_id=top_hit.entry_id if top_hit else None,
            normalized_prompt=normalized,
            details=fusion_details,
        )
