from __future__ import annotations

import os
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal

from prismguard.config.loader import TriageConfig, load_triage_config
from prismguard.context.matcher import (
    compile_override_tokens,
    contains_override_language,
    find_matching_entities,
    tenant_severity_boost,
    tenant_tier1_block,
)
from prismguard.context.models import TenantLexicon
from prismguard.context.loader import load_lexicon_file, load_tenant_lexicon
from prismguard.runtime.fusion import fuse_signals
from prismguard.runtime.guard_model import GuardModel, GuardModelVerdict
from prismguard.runtime.llm_judge import LLMJudge
from prismguard.runtime.normalize import normalize_prompt
from prismguard.runtime.session import SessionStore, create_session_store
from prismguard.runtime.stage_profiler import StageProfiler
from prismguard.runtime.structural import analyze_structural
from prismguard.runtime.verdict_cache import content_address, get_verdict_cache, rule_version_snapshot
from prismguard.runtime.thresholds import resolve_thresholds
from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.embedder import Embedder, HashEmbedder, create_embedder_from_config

if TYPE_CHECKING:
    from prismguard.feedback.review import FeedbackReviewService
from prismguard.taxonomy.graph import TaxonomyGraphEngine
from prismguard.taxonomy.ingest import ingest_seed_vectors, iter_all_seed_entries
from prismguard.taxonomy.mapping import TaxonomyEngine, build_mapping_from_parsed_seed

Decision = Literal["block", "allow", "gray"]
ResolutionGate = Literal[
    "tier1_rule",
    "tenant_context_rule",
    "structural",
    "corpus_match",
    "benign_fast_path",
    "fusion_block",
    "fusion_allow",
    "fusion_gray",
    "fusion_gray_fail_open",
    "fusion_gray_fail_closed",
    "guard_model",
    "guard_model_first",
    "guard_model_fast_allow",
    "guard_model_veto",
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
    return (
        config.guard_model.classifier_mode in ("parallel", "first", "hybrid")
        or config.gray_zone_policy == "escalate"
    )


def guard_model_required_at_init(config: TriageConfig) -> bool:
    """Strict init check — escalate policy must have a model; parallel degrades if missing."""
    return config.guard_model.enabled and config.gray_zone_policy == "escalate"


def _resolve_tenant_lexicon(config: TriageConfig) -> TenantLexicon | None:
    if not config.tenant_context.enabled:
        return None
    path = config.tenant_context.lexicon_path.strip() or os.environ.get(
        "PRISMGUARD_TENANT_LEXICON_PATH", ""
    ).strip()
    if path:
        return load_lexicon_file(path)
    return load_tenant_lexicon()


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
        tenant_lexicon: TenantLexicon | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        self._storage = storage
        self._engine = engine
        self._config = config or load_triage_config()
        if embedder is not None:
            self._embedder = embedder
        elif self._config.embedding.corpus_path_enabled:
            self._embedder = create_embedder_from_config(self._config)
        else:
            self._embedder = HashEmbedder()
        self._guard_model = guard_model
        self._llm_judge = llm_judge
        self._feedback_review = feedback_review
        self._tenant_lexicon = tenant_lexicon or _resolve_tenant_lexicon(self._config)
        self._override_tokens = compile_override_tokens(self._tenant_lexicon)
        self._session_store = session_store or create_session_store()
        self._judge_circuit_open = False
        self._classifier_executor = ThreadPoolExecutor(
            max_workers=max(1, int(os.environ.get("PRISMGUARD_CLASSIFIER_WORKERS", "2"))),
            thread_name_prefix="prismguard-clf",
        )
        if guard_model_required_at_init(self._config) and self._guard_model is None:
            raise ValueError(
                "gray_zone_policy='escalate' requires a configured GuardModel at RuntimeChecker init"
            )
        if self._config.embedding.corpus_path_enabled:
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
        else:
            self._graph_engine = TaxonomyGraphEngine.from_mapping(
                mapping_dict=engine.mapping_dict,
                embedder=self._embedder,
                attack_categories=engine.attack_categories,
                seed_texts=[],
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
        tenant_lexicon: TenantLexicon | None = None,
    ) -> RuntimeChecker:
        engine = build_mapping_from_parsed_seed(parsed_seed)
        config = config or load_triage_config()
        if embedder is not None:
            emb = embedder
        elif config.embedding.corpus_path_enabled:
            emb = create_embedder_from_config(config)
        else:
            emb = HashEmbedder()
        from prismguard.taxonomy.constants import CATEGORY_VECTOR_DIM

        if config.embedding.corpus_path_enabled:
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
        if guard_model is None and guard_model_required(config):
            from prismguard.runtime.guard_model import create_guard_model

            guard_model = create_guard_model(config.guard_model)
        if guard_model is None and config.gray_zone_policy == "escalate":
            config = config.model_copy(update={"gray_zone_policy": "fail_closed"})
        if guard_model is None and config.guard_model.classifier_mode in ("parallel", "first", "hybrid"):
            config = config.model_copy(update={"guard_model": config.guard_model.model_copy(update={"classifier_mode": "gray_only"})})
        return cls(
            storage,
            engine,
            embedder=emb,
            config=config,
            guard_model=guard_model,
            llm_judge=llm_judge,
            feedback_review=feedback_review,
            tenant_lexicon=tenant_lexicon,
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

    def _uses_classifier_hybrid(self) -> bool:
        return (
            self._config.guard_model.enabled
            and self._config.guard_model.classifier_mode == "hybrid"
            and self._guard_model is not None
        )

    def _uses_classifier_first(self) -> bool:
        return (
            self._config.guard_model.enabled
            and self._config.guard_model.classifier_mode == "first"
            and self._guard_model is not None
        )

    def _uses_parallel_classifier(self) -> bool:
        return (
            self._config.guard_model.enabled
            and self._config.guard_model.classifier_mode == "parallel"
            and self._guard_model is not None
        )

    def _start_classifier_async(self, prompt: str) -> Future[GuardModelVerdict] | None:
        """Start ONNX classifier without blocking (classifier-first mode)."""
        if self._uses_classifier_hybrid():
            return None
        if not self._uses_classifier_first():
            return None
        return self._classifier_executor.submit(self._guard_model.check, prompt)  # type: ignore[union-attr]

    def _start_classifier_late(self, prompt: str) -> Future[GuardModelVerdict] | None:
        """Hybrid/parallel: start classifier after rules/structural short-circuits."""
        if self._guard_model is None:
            return None
        if not (self._uses_classifier_hybrid() or self._uses_parallel_classifier()):
            return None
        return self._classifier_executor.submit(self._guard_model.check, prompt)

    @staticmethod
    def _mark_classifier_invoked(details: dict) -> dict:
        return {**details, "classifier_invoked": True}

    def _attach_optional_classifier_details(
        self,
        details: dict,
        future: Future[GuardModelVerdict] | None,
        *,
        await_verdict: bool = False,
    ) -> dict:
        if future is None:
            return details
        details = self._mark_classifier_invoked(details)
        if await_verdict or future.done():
            verdict = future.result()
            return self._attach_classifier_details(details, verdict)
        return details

    def _await_classifier_verdict(
        self,
        future: Future[GuardModelVerdict] | None,
    ) -> GuardModelVerdict | None:
        if future is None:
            return None
        profiler = StageProfiler.current()
        if profiler is None:
            return future.result()
        with profiler.section("classifier"):
            return future.result()

    def _classifier_disagrees_with_structural_allow(
        self,
        verdict: GuardModelVerdict | None,
    ) -> bool:
        if verdict is None:
            return False
        if verdict.decision == "uncertain":
            return True
        if verdict.decision == "block":
            return verdict.confidence >= self._config.guard_model.veto_threshold
        return False

    def _structural_allow_wins_on_disagreement(
        self,
        *,
        normalized: str,
        structural: object,
        classifier_verdict: GuardModelVerdict,
        decision_source: str,
    ) -> CheckResult:
        return CheckResult(
            decision="allow",
            resolution_gate="structural",
            matched_category="benign_adjacent",
            normalized_prompt=normalized,
            details=self._attach_classifier_details(
                {
                    "structural": getattr(structural, "details", {}),
                    "matched_pattern": getattr(structural, "matched_pattern", None),
                    "decision_source": decision_source,
                },
                classifier_verdict,
            ),
        )

    def _invoke_llm_judge(
        self,
        *,
        prompt: str,
        normalized: str,
        guard_details: dict,
        matched_category: str | None,
        decision_source: str,
    ) -> CheckResult:
        if self._llm_judge is None:
            policy = self._config.gray_zone_policy
            if policy == "fail_closed":
                # Structural allow wins over classifier disagreement when Judge is unavailable.
                decision: Decision = "allow"
                gate: ResolutionGate = "structural"
                source = f"{decision_source}→no_judge→structural_wins"
            else:
                decision = "allow"
                gate = "structural"
                source = f"{decision_source}→no_judge→structural_wins"
            return CheckResult(
                decision=decision,
                resolution_gate=gate,
                matched_category=matched_category,
                normalized_prompt=normalized,
                details={**guard_details, "decision_source": source},
            )

        profiler = StageProfiler.current()
        judge_context = {
            **guard_details,
            "matched_category": matched_category,
            "nearest_seed_examples": self._nearest_seed_examples(normalized, matched_category),
        }
        if profiler is not None:
            with profiler.section("judge"):
                judge = self._llm_judge.judge(prompt, context=judge_context)
        else:
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
                "decision_source": decision_source,
            },
        )
        self._record_feedback(prompt=prompt, result=result, origin="llm_judge")
        return result

    def _escalate_structural_classifier_disagreement(
        self,
        *,
        prompt: str,
        normalized: str,
        structural: object,
        classifier_verdict: GuardModelVerdict,
    ) -> CheckResult:
        details = self._attach_classifier_details(
            {
                "structural": getattr(structural, "details", {}),
                "matched_pattern": getattr(structural, "matched_pattern", None),
                "disagreement_escalation": True,
            },
            classifier_verdict,
        )
        if self._config.gray_zone_policy != "escalate":
            return self._structural_allow_wins_on_disagreement(
                normalized=normalized,
                structural=structural,
                classifier_verdict=classifier_verdict,
                decision_source="structural_allow→classifier_disagree→structural_wins",
            )
        return self._invoke_llm_judge(
            prompt=prompt,
            normalized=normalized,
            guard_details=details,
            matched_category="benign_adjacent",
            decision_source="structural_allow→classifier_disagree→llm_judge",
        )

    def _classifier_first_early_block(
        self,
        verdict: GuardModelVerdict,
        *,
        structural: object | None = None,
        normalized: str = "",
    ) -> CheckResult | None:
        if verdict.decision != "block":
            return None
        if (
            structural is not None
            and getattr(structural, "decision", None) == "allow"
            and self._config.guard_model.disagreement_escalation
        ):
            return None
        threshold = self._config.guard_model.classifier_first_block_threshold
        if verdict.confidence < threshold:
            return None
        if structural is not None and getattr(structural, "decision", None) == "continue":
            from prismguard.runtime.structural import is_legal_topic_fragment

            attack_score = float(getattr(structural, "attack_score", 0.0) or 0.0)
            if attack_score < 0.35 and is_legal_topic_fragment(normalized):
                return None
        details = {
            **self._classifier_details(verdict),
            "classifier_mode": "first",
            "decision_source": "classifier_first→block",
        }
        return CheckResult(
            decision="block",
            resolution_gate="guard_model_first",
            normalized_prompt="",
            details=details,
        )

    def _classifier_fast_allow(self, verdict: GuardModelVerdict) -> CheckResult | None:
        if verdict.decision != "allow":
            return None
        if verdict.confidence >= self._config.guard_model.uncertain_low:
            return None
        details = {
            **self._classifier_details(verdict),
            "classifier_mode": "first",
            "decision_source": "classifier_first→fast_allow",
        }
        return CheckResult(
            decision="allow",
            resolution_gate="guard_model_fast_allow",
            matched_category="benign_adjacent",
            normalized_prompt="",
            details=details,
        )

    def _attach_classifier_details(self, details: dict, verdict: GuardModelVerdict | None) -> dict:
        if verdict is None:
            return details
        mode = "first" if self._uses_classifier_first() else "parallel"
        return {**details, **self._classifier_details(verdict), "classifier_mode": mode}

    def _escalate_uncertain_classifier(
        self,
        *,
        prompt: str,
        normalized: str,
        fusion_details: dict,
        matched_category: str | None,
        classifier_verdict: GuardModelVerdict,
    ) -> CheckResult:
        details = self._attach_classifier_details(fusion_details, classifier_verdict)
        details["decision_source"] = "classifier_first→uncertain→gray"
        return self._resolve_gray(
            prompt=prompt,
            normalized=normalized,
            fusion_details=details,
            matched_category=matched_category,
        )

    def _resolve_classifier_only(
        self,
        *,
        prompt: str,
        normalized: str,
        verdict: GuardModelVerdict | None,
        matched_category: str | None = None,
        extra_details: dict | None = None,
    ) -> CheckResult:
        """ONNX-only tail: no embed/ANN/fusion — classifier verdict + gray policy."""
        if verdict is None and self._guard_model is not None:
            verdict = self._guard_model.check(prompt)
        base = dict(extra_details or {})
        if verdict is None:
            policy = self._config.gray_zone_policy
            decision: Decision = "allow" if policy == "fail_open" else "block"
            gate: ResolutionGate = "guard_model" if policy != "fail_open" else "fusion_allow"
            return CheckResult(
                decision=decision,
                resolution_gate=gate,
                normalized_prompt=normalized,
                matched_category=matched_category,
                details={**base, "decision_source": "classifier_only→no_model"},
            )

        details = self._attach_classifier_details(
            {**base, "decision_source": "classifier_only_path"},
            verdict,
        )
        if verdict.decision == "block":
            from prismguard.runtime.structural import is_legal_topic_fragment

            if (
                self._uses_classifier_first()
                and is_legal_topic_fragment(normalized)
                and verdict.confidence < self._config.guard_model.classifier_first_block_threshold
            ):
                return CheckResult(
                    decision="allow",
                    resolution_gate="guard_model",
                    normalized_prompt=normalized,
                    matched_category=matched_category or "benign_adjacent",
                    details={
                        **details,
                        "decision_source": "classifier_only→legal_topic_fragment→allow",
                    },
                )
            if (
                self._uses_classifier_first()
                and is_legal_topic_fragment(normalized)
                and verdict.confidence >= self._config.guard_model.classifier_first_block_threshold
            ):
                return CheckResult(
                    decision="allow",
                    resolution_gate="structural",
                    normalized_prompt=normalized,
                    matched_category=matched_category or "benign_adjacent",
                    details={
                        **details,
                        "decision_source": "classifier_only→legal_topic_fragment→structural_allow",
                    },
                )
            if (
                self._uses_classifier_first()
                and verdict.confidence < self._config.guard_model.veto_threshold
            ):
                return CheckResult(
                    decision="allow",
                    resolution_gate="guard_model",
                    normalized_prompt=normalized,
                    matched_category=matched_category or "benign_adjacent",
                    details={
                        **details,
                        "decision_source": "classifier_only→below_veto→allow",
                    },
                )
            return CheckResult(
                decision="block",
                resolution_gate="guard_model",
                normalized_prompt=normalized,
                matched_category=matched_category,
                details=details,
            )
        if verdict.decision == "allow":
            return CheckResult(
                decision="allow",
                resolution_gate="guard_model_fast_allow",
                normalized_prompt=normalized,
                matched_category=matched_category or "benign_adjacent",
                details=details,
            )
        return self._resolve_gray(
            prompt=prompt,
            normalized=normalized,
            fusion_details=details,
            matched_category=matched_category,
        )

    def _start_parallel_classifier(self, prompt: str) -> Future[GuardModelVerdict] | None:
        if not self._uses_parallel_classifier():
            return None
        return self._classifier_executor.submit(self._guard_model.check, prompt)  # type: ignore[union-attr]

    def _collect_classifier_verdict(
        self,
        future: Future[GuardModelVerdict] | None,
    ) -> GuardModelVerdict | None:
        return self._await_classifier_verdict(future)

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

    def _apply_classifier_veto(
        self,
        decision: Decision,
        gate: ResolutionGate,
        verdict: GuardModelVerdict | None,
        details: dict,
    ) -> tuple[Decision, ResolutionGate, dict]:
        if verdict is None or not self._config.guard_model.veto_enabled:
            return decision, gate, details
        if (
            self._config.guard_model.disagreement_escalation
            and gate == "structural"
            and decision == "allow"
        ):
            return decision, gate, details
        threshold = self._config.guard_model.veto_threshold
        if decision == "allow" and verdict.confidence >= threshold:
            return (
                "block",
                "guard_model_veto",
                {
                    **details,
                    "classifier_veto": True,
                    "veto_confidence": verdict.confidence,
                    "decision_source": "classifier_veto",
                },
            )
        return decision, gate, details

    def _tenant_override_escalation(
        self,
        normalized: str,
        classifier_verdict: GuardModelVerdict | None,
    ) -> bool:
        if self._tenant_lexicon is None or not self._config.tenant_context.force_classifier_on_override:
            return False
        if not contains_override_language(normalized, override_tokens=self._override_tokens):
            return False
        if not find_matching_entities(normalized, self._tenant_lexicon):
            return False
        if classifier_verdict is None:
            return True
        return classifier_verdict.decision == "uncertain"

    def _skip_benign_fast_path(self, normalized: str) -> bool:
        if self._tenant_lexicon is None:
            return False
        if not contains_override_language(normalized, override_tokens=self._override_tokens):
            return False
        return bool(find_matching_entities(normalized, self._tenant_lexicon))

    def _fusion_classifier_prob(self, verdict: GuardModelVerdict | None) -> float | None:
        """Only let high-confidence classifier scores pull fusion toward block."""
        if verdict is None:
            return None
        if verdict.confidence < self._config.guard_model.veto_threshold:
            if verdict.decision == "block":
                return None
            return verdict.confidence
        return verdict.confidence

    def _resolve_gray(
        self,
        *,
        prompt: str,
        normalized: str,
        fusion_details: dict,
        matched_category: str | None,
    ) -> CheckResult:
        profiler = StageProfiler.current()
        if profiler is not None:
            with profiler.section("gray_resolve"):
                return self._resolve_gray_body(
                    prompt=prompt,
                    normalized=normalized,
                    fusion_details=fusion_details,
                    matched_category=matched_category,
                )
        return self._resolve_gray_body(
            prompt=prompt,
            normalized=normalized,
            fusion_details=fusion_details,
            matched_category=matched_category,
        )

    def _resolve_gray_body(
        self,
        *,
        prompt: str,
        normalized: str,
        fusion_details: dict,
        matched_category: str | None,
    ) -> CheckResult:
        profiler = StageProfiler.current()
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
            if profiler is not None:
                with profiler.section("classifier_gray"):
                    verdict = self._guard_model.check(prompt, context=fusion_details)  # type: ignore[union-attr]
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
            return self._invoke_llm_judge(
                prompt=prompt,
                normalized=normalized,
                guard_details=guard_details,
                matched_category=matched_category,
                decision_source="fusion_gray→guard_model_uncertain→llm_judge",
            )

        if verdict_decision == "block":
            confidence = guard_details.get("guard_model_confidence")
            if (
                self._uses_classifier_first()
                and isinstance(confidence, (int, float))
                and float(confidence) < self._config.guard_model.veto_threshold
            ):
                verdict_decision = "allow"
                guard_details = {
                    **guard_details,
                    "decision_source": "fusion_gray→guard_model_below_veto→allow",
                }
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
        profiler = StageProfiler.begin()
        wall_start = time.perf_counter()
        cache = get_verdict_cache()
        cache_key: str | None = None
        normalized_for_cache = normalize_prompt(
            prompt,
            max_obfuscation_depth=self._config.normalization.max_obfuscation_depth,
        )
        if cache is not None and self._guard_model is not None:
            cache_key = content_address(
                normalized_prompt=normalized_for_cache,
                artifact_id=self._guard_model.model_id,
                classifier_mode=self._config.guard_model.classifier_mode,
                rule_version=rule_version_snapshot(
                    tier1_rules=self._storage.relational.list_rules(),
                ),
                structural_threshold=self._config.structural.structural_block_threshold,
                veto_threshold=self._config.guard_model.veto_threshold,
            )
            cached = cache.get(cache_key)
            if cached is not None:
                cached.normalized_prompt = normalized_for_cache
                return cached
        try:
            result = self._check_body(prompt, session_id=session_id)
            if profiler is not None:
                result.details = profiler.merge_details(result.details)
                profiler.log_request(
                    resolution_gate=result.resolution_gate,
                    decision=result.decision,
                    prompt=prompt,
                    wall_ms=(time.perf_counter() - wall_start) * 1000,
                )
            if session_id:
                self._session_store.record_turn(
                    session_id,
                    prompt=prompt,
                    normalized=result.normalized_prompt,
                    category_slug=result.matched_category,
                    attack_sim=result.attack_sim,
                    decision=result.decision,
                )
            if cache is not None and cache_key is not None:
                cache.put(cache_key, result)
            return result
        finally:
            StageProfiler.end()

    def _check_body(self, prompt: str, *, session_id: str | None = None) -> CheckResult:
        profiler = StageProfiler.current()

        if profiler is not None:
            with profiler.section("normalize"):
                normalized = normalize_prompt(
                    prompt,
                    max_obfuscation_depth=self._config.normalization.max_obfuscation_depth,
                )
        else:
            normalized = normalize_prompt(
                prompt,
                max_obfuscation_depth=self._config.normalization.max_obfuscation_depth,
            )

        session_score = self._session_store.escalation_score(session_id) if session_id else 0.0

        if profiler is not None:
            with profiler.section("classifier_start"):
                classifier_future = self._start_classifier_async(prompt)
        else:
            classifier_future = self._start_classifier_async(prompt)

        if profiler is not None:
            with profiler.section("tier1"):
                tier1 = self._engine.match_tier1(normalized)
        else:
            tier1 = self._engine.match_tier1(normalized)
        if tier1 is not None:
            return CheckResult(
                decision="block",
                resolution_gate="tier1_rule",
                matched_category=tier1.category_slug,
                matched_rule_id=tier1.rule_id,
                normalized_prompt=normalized,
                details=self._attach_optional_classifier_details(
                    {"severity": tier1.severity},
                    classifier_future,
                ),
            )

        if profiler is not None:
            with profiler.section("tenant"):
                tenant_block = tenant_tier1_block(
                    normalized,
                    self._tenant_lexicon,
                    override_tokens=self._override_tokens,
                )
        else:
            tenant_block = tenant_tier1_block(
                normalized,
                self._tenant_lexicon,
                override_tokens=self._override_tokens,
            )
        if tenant_block is not None:
            return CheckResult(
                decision="block",
                resolution_gate="tenant_context_rule",
                matched_category="direct_instruction_override",
                normalized_prompt=normalized,
                details=self._attach_optional_classifier_details(
                    tenant_block,
                    classifier_future,
                ),
            )

        if profiler is not None:
            with profiler.section("structural"):
                structural = analyze_structural(
                    normalized,
                    block_threshold=self._config.structural.structural_block_threshold,
                    allow_threshold=self._config.structural.structural_allow_threshold,
                )
        else:
            structural = analyze_structural(
                normalized,
                block_threshold=self._config.structural.structural_block_threshold,
                allow_threshold=self._config.structural.structural_allow_threshold,
            )
        if structural.decision == "block":
            return CheckResult(
                decision="block",
                resolution_gate="structural",
                matched_category="direct_instruction_override",
                normalized_prompt=normalized,
                details=self._attach_optional_classifier_details(
                    {"structural": structural.details, "matched_pattern": structural.matched_pattern},
                    classifier_future,
                ),
            )

        if structural.decision == "allow":
            if self._uses_classifier_hybrid():
                return CheckResult(
                    decision="allow",
                    resolution_gate="structural",
                    matched_category="benign_adjacent",
                    normalized_prompt=normalized,
                    details={
                        "structural": structural.details,
                        "matched_pattern": structural.matched_pattern,
                        "decision_source": "hybrid→structural_allow_skip_classifier",
                    },
                )
            first_verdict = self._await_classifier_verdict(classifier_future)
            if (
                self._config.guard_model.disagreement_escalation
                and self._classifier_disagrees_with_structural_allow(first_verdict)
            ):
                return self._escalate_structural_classifier_disagreement(
                    prompt=prompt,
                    normalized=normalized,
                    structural=structural,
                    classifier_verdict=first_verdict,  # type: ignore[arg-type]
                )
            first_block_threshold = self._config.guard_model.classifier_first_block_threshold
            if (
                first_verdict is None
                or first_verdict.confidence < first_block_threshold
                or structural.benign_score >= 0.45
            ):
                return CheckResult(
                    decision="allow",
                    resolution_gate="structural",
                    matched_category="benign_adjacent",
                    normalized_prompt=normalized,
                    details=self._attach_classifier_details(
                        {
                            "structural": structural.details,
                            "matched_pattern": structural.matched_pattern,
                            "decision_source": "structural_benign_framing",
                        },
                        first_verdict,
                    ),
                )
            early = self._classifier_first_early_block(
                first_verdict, structural=structural, normalized=normalized
            )
            if early is not None:
                early.normalized_prompt = normalized
                return early
            if (
                first_verdict is not None
                and first_verdict.decision == "uncertain"
                and self._config.gray_zone_policy == "escalate"
            ):
                return self._escalate_uncertain_classifier(
                    prompt=prompt,
                    normalized=normalized,
                    fusion_details={"structural": structural.details, "matched_pattern": structural.matched_pattern},
                    matched_category="benign_adjacent",
                    classifier_verdict=first_verdict,
                )
            if first_verdict is not None and self._config.guard_model.veto_enabled:
                vetoed = self._apply_classifier_veto(
                    "allow",
                    "structural",
                    first_verdict,
                    {"structural": structural.details, "matched_pattern": structural.matched_pattern},
                )
                if vetoed[0] == "block":
                    return CheckResult(
                        decision="block",
                        resolution_gate=vetoed[1],
                        matched_category="benign_adjacent",
                        normalized_prompt=normalized,
                        details=vetoed[2],
                    )
            return CheckResult(
                decision="allow",
                resolution_gate="structural",
                matched_category="benign_adjacent",
                normalized_prompt=normalized,
                details=self._attach_classifier_details(
                    {"structural": structural.details, "matched_pattern": structural.matched_pattern},
                    first_verdict,
                ),
            )

        if classifier_future is None:
            classifier_future = self._start_classifier_late(prompt)
        if classifier_future is None:
            classifier_future = self._start_parallel_classifier(prompt)

        first_verdict = self._await_classifier_verdict(classifier_future)
        if first_verdict is not None:
            early = self._classifier_first_early_block(
                first_verdict, structural=structural, normalized=normalized
            )
            if early is not None:
                early.normalized_prompt = normalized
                return early
            fast_allow = self._classifier_fast_allow(first_verdict)
            if fast_allow is not None:
                fast_allow.normalized_prompt = normalized
                return fast_allow

        if not self._config.embedding.corpus_path_enabled:
            return self._resolve_classifier_only(
                prompt=prompt,
                normalized=normalized,
                verdict=first_verdict,
            )

        if profiler is not None:
            with profiler.section("embed"):
                semantic = self._embedder.embed_semantic(normalized)
            with profiler.section("category"):
                slug = self._engine.assign_category(normalized)
                category_vec = self._engine.remap_category_vector(
                    normalized, semantic, category_slug=slug
                )
        else:
            semantic = self._embedder.embed_semantic(normalized)
            slug = self._engine.assign_category(normalized)
            category_vec = self._engine.remap_category_vector(
                normalized, semantic, category_slug=slug
            )

        attack_slugs = list(self._engine.attack_categories)
        benign_slug = self._engine.benign_category

        if profiler is not None:
            with profiler.section("ann_search"):
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
        else:
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
            not self._skip_benign_fast_path(normalized)
            and benign_sim >= thresholds.benign_allow_floor
            and margin <= -thresholds.benign_margin_delta
        ):
            if (
                first_verdict is not None
                and first_verdict.decision == "uncertain"
                and self._config.gray_zone_policy == "escalate"
            ):
                return self._escalate_uncertain_classifier(
                    prompt=prompt,
                    normalized=normalized,
                    fusion_details={
                        "attack_sim": attack_sim,
                        "benign_sim": benign_sim,
                        "benign_fast_path": True,
                    },
                    matched_category=matched_category,
                    classifier_verdict=first_verdict,
                )
            allow_details = self._attach_classifier_details(
                {"attack_sim": attack_sim, "benign_sim": benign_sim},
                first_verdict,
            )
            if first_verdict is not None and self._config.guard_model.veto_enabled:
                vetoed = self._apply_classifier_veto("allow", "benign_fast_path", first_verdict, allow_details)
                if vetoed[0] == "block":
                    return CheckResult(
                        decision="block",
                        resolution_gate=vetoed[1],
                        attack_sim=attack_sim,
                        benign_sim=benign_sim,
                        normalized_prompt=normalized,
                        matched_category=matched_category,
                        details=vetoed[2],
                    )
            return CheckResult(
                decision="allow",
                resolution_gate="benign_fast_path",
                attack_sim=attack_sim,
                benign_sim=benign_sim,
                normalized_prompt=normalized,
                matched_category=matched_category,
                details=allow_details,
            )

        top_hit = attack_hits[0] if attack_hits else None
        rule_matched = bool(slug and slug in self._engine.attack_categories)
        if profiler is not None:
            with profiler.section("graph"):
                graph_score = self._graph_connectivity_score(normalized, matched_category)
                community_confidence = self._community_confidence(
                    semantic,
                    matched_category,
                    rule_matched=rule_matched,
                )
        else:
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
                details=self._attach_classifier_details(
                    {
                        "attack_sim": attack_sim,
                        "benign_sim": benign_sim,
                        "corpus_match_score": top_hit.score,
                    },
                    first_verdict,
                ),
            )

        classifier_verdict = first_verdict
        classifier_prob = self._fusion_classifier_prob(classifier_verdict)

        if profiler is not None:
            with profiler.section("fusion"):
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
                    w_session=cfg.fusion.w_session,
                    session_escalation_score=session_score,
                    weak_signal_floor=cfg.fusion.weak_signal_floor,
                )
        else:
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
                w_session=cfg.fusion.w_session,
                session_escalation_score=session_score,
                weak_signal_floor=cfg.fusion.weak_signal_floor,
            )

        fusion_details = {
            "session_id": session_id,
            "session_escalation_score": session_score,
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

        tenant_boost = tenant_severity_boost(
            normalized,
            self._tenant_lexicon,
            boost_restricted=cfg.tenant_context.severity_boost_restricted,
            boost_internal=cfg.tenant_context.severity_boost_internal,
        )
        fused_score = min(1.0, fusion.fused_score + tenant_boost)
        if session_score > 0:
            fusion_details["session_escalation_score"] = session_score
        if tenant_boost > 0:
            fusion_details["tenant_severity_boost"] = tenant_boost
        fusion_details["fused_score"] = fused_score

        decision, gate = route_fusion_decision(
            fused_score=fused_score,
            weak_signal_count=fusion.weak_signal_count,
            block_threshold=thresholds.block_threshold,
            allow_threshold=thresholds.allow_threshold,
            min_weak_signals_for_gray=cfg.fusion.min_weak_signals_for_gray,
        )

        decision, gate, fusion_details = self._apply_classifier_veto(
            decision,
            gate,
            classifier_verdict,
            fusion_details,
        )

        if (
            self._uses_classifier_first()
            and classifier_verdict is not None
            and classifier_verdict.decision == "uncertain"
            and decision == "allow"
            and gate == "fusion_allow"
            and self._config.gray_zone_policy == "escalate"
        ):
            return self._escalate_uncertain_classifier(
                prompt=prompt,
                normalized=normalized,
                fusion_details=fusion_details,
                matched_category=matched_category,
                classifier_verdict=classifier_verdict,
            )

        if (
            decision == "allow"
            and gate == "fusion_allow"
            and self._tenant_override_escalation(normalized, classifier_verdict)
            and not self._config.gray_terminal
        ):
            return self._resolve_gray(
                prompt=prompt,
                normalized=normalized,
                fusion_details=fusion_details,
                matched_category=matched_category,
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
            fused_score=fused_score,
            attack_sim=attack_sim,
            benign_sim=benign_sim,
            matched_category=matched_category,
            top_attack_entry_id=top_hit.entry_id if top_hit else None,
            normalized_prompt=normalized,
            details=fusion_details,
        )
