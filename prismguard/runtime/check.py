from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from prismguard.config.loader import TriageConfig, load_triage_config
from prismguard.runtime.fusion import fuse_signals
from prismguard.runtime.normalize import normalize_prompt
from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.embedder import Embedder, create_embedder
from prismguard.taxonomy.mapping import TaxonomyEngine
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
        needs_embed = force_embed or any(
            not (e.embedding_semantic and e.embedding_category)
            for e in iter_all_seed_entries(storage)
        )
        if needs_embed:
            ingest_seed_vectors(storage, engine, emb, force=force_embed)
        return cls(storage, engine, embedder=emb, config=config)

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
        category_vec = self._engine.remap_category_vector(normalized, semantic)

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

        cfg = self._config
        margin = attack_sim - benign_sim
        if benign_sim >= cfg.benign_fast_path.benign_allow_floor and margin < cfg.benign_fast_path.benign_margin_delta:
            return CheckResult(
                decision="allow",
                resolution_gate="benign_fast_path",
                attack_sim=attack_sim,
                benign_sim=benign_sim,
                normalized_prompt=normalized,
                matched_category=slug,
            )

        top_hit = attack_hits[0] if attack_hits else None
        fusion = fuse_signals(
            attack_sim=attack_sim,
            benign_sim=benign_sim,
            rule_matched=slug in self._engine.attack_categories if slug else False,
            severity=top_hit.severity if top_hit else "medium",
            w_sim=cfg.fusion.w_sim,
            w_benign=cfg.fusion.w_benign,
            w_rule=cfg.fusion.w_rule,
            w_sev=cfg.fusion.w_sev,
        )

        if fusion.fused_score >= cfg.triage.block_threshold:
            gate: ResolutionGate = "fusion_block"
            decision: Decision = "block"
        elif fusion.fused_score <= cfg.triage.allow_threshold:
            gate = "fusion_allow"
            decision = "allow"
        else:
            gate = "fusion_gray"
            decision = "gray"

        if top_hit and top_hit.score >= 0.92:
            gate = "corpus_match"
            decision = "block"

        return CheckResult(
            decision=decision,
            resolution_gate=gate,
            fused_score=fusion.fused_score,
            attack_sim=attack_sim,
            benign_sim=benign_sim,
            matched_category=slug or (top_hit.category_slug if top_hit else None),
            top_attack_entry_id=top_hit.entry_id if top_hit else None,
            normalized_prompt=normalized,
            details={
                "session_id": session_id,
                "contrastive_margin": fusion.contrastive_margin,
            },
        )
