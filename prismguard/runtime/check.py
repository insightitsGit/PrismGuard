from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from prismguard.config.loader import TriageConfig, load_triage_config
from prismguard.runtime.fusion import fuse_signals
from prismguard.runtime.normalize import normalize_prompt
from prismguard.runtime.thresholds import resolve_thresholds
from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.embedder import Embedder, create_embedder
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


class RuntimeChecker:
    """
    Deterministic pre-LLM check: normalize → Tier-1 → dual ANN → fusion.
    No Guard Model or LLM Judge — gray zone is explicit for downstream escalation.
    """

    def __init__(
        self,
        storage: StorageBackend,
        engine: TaxonomyEngine,
        *,
        embedder: Embedder | None = None,
        config: TriageConfig | None = None,
    ) -> None:
        self._storage = storage
        self._engine = engine
        self._embedder = embedder or create_embedder(prefer_transformer=False)
        self._config = config or load_triage_config()

    @classmethod
    def from_storage(
        cls,
        storage: StorageBackend,
        parsed_seed,
        *,
        embedder: Embedder | None = None,
        config: TriageConfig | None = None,
        force_embed: bool = False,
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
        return cls(storage, engine, embedder=emb, config=config)

    def _graph_connectivity_score(self, text: str, category_slug: str | None) -> float:
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

    @staticmethod
    def _community_confidence(category_slug: str | None, rule_matched: bool) -> float:
        if rule_matched and category_slug:
            return 1.0
        return 0.5 if category_slug else 0.0

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
        thresholds = resolve_thresholds(self._config, matched_category)
        cfg = self._config

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
        community_confidence = self._community_confidence(matched_category, rule_matched)

        fusion = fuse_signals(
            attack_sim=attack_sim,
            benign_sim=benign_sim,
            rule_matched=rule_matched,
            severity=top_hit.severity if top_hit else "medium",
            graph_score=graph_score,
            community_confidence=community_confidence,
            w_sim=cfg.fusion.w_sim,
            w_graph=cfg.fusion.w_graph,
            w_rule=cfg.fusion.w_rule,
            w_sev=cfg.fusion.w_sev,
            w_comm=cfg.fusion.w_comm,
            w_benign=cfg.fusion.w_benign,
            weak_signal_floor=cfg.fusion.weak_signal_floor,
        )

        if top_hit and top_hit.score >= thresholds.corpus_match_threshold:
            return CheckResult(
                decision="block",
                resolution_gate="corpus_match",
                fused_score=fusion.fused_score,
                attack_sim=attack_sim,
                benign_sim=benign_sim,
                matched_category=matched_category,
                top_attack_entry_id=top_hit.entry_id,
                normalized_prompt=normalized,
                details={
                    "session_id": session_id,
                    "contrastive_margin": fusion.contrastive_margin,
                    "corpus_match_threshold": thresholds.corpus_match_threshold,
                },
            )

        decision, gate = route_fusion_decision(
            fused_score=fusion.fused_score,
            weak_signal_count=fusion.weak_signal_count,
            block_threshold=thresholds.block_threshold,
            allow_threshold=thresholds.allow_threshold,
            min_weak_signals_for_gray=cfg.fusion.min_weak_signals_for_gray,
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
            details={
                "session_id": session_id,
                "contrastive_margin": fusion.contrastive_margin,
                "weak_signal_count": fusion.weak_signal_count,
                "block_threshold": thresholds.block_threshold,
                "allow_threshold": thresholds.allow_threshold,
            },
        )
