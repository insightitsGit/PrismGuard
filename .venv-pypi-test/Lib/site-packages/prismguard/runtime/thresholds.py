from __future__ import annotations

from dataclasses import dataclass

from prismguard.config.loader import CategoryOverride, TriageConfig


@dataclass(frozen=True)
class ResolvedThresholds:
    block_threshold: float
    allow_threshold: float
    benign_allow_floor: float
    benign_margin_delta: float
    corpus_match_threshold: float


def resolve_thresholds(cfg: TriageConfig, category_slug: str | None) -> ResolvedThresholds:
    override: CategoryOverride | None = cfg.categories.get(category_slug or "")
    return ResolvedThresholds(
        block_threshold=(
            override.block_threshold
            if override and override.block_threshold is not None
            else cfg.triage.block_threshold
        ),
        allow_threshold=(
            override.allow_threshold
            if override and override.allow_threshold is not None
            else cfg.triage.allow_threshold
        ),
        benign_allow_floor=(
            override.benign_allow_floor
            if override and override.benign_allow_floor is not None
            else cfg.benign_fast_path.benign_allow_floor
        ),
        benign_margin_delta=(
            override.benign_margin_delta
            if override and override.benign_margin_delta is not None
            else cfg.benign_fast_path.benign_margin_delta
        ),
        corpus_match_threshold=(
            override.corpus_match_override_threshold
            if override and override.corpus_match_override_threshold is not None
            else cfg.triage.corpus_match_override_threshold
        ),
    )
