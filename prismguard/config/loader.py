from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class NormalizationConfig(BaseModel):
    max_obfuscation_depth: int = 3


class FusionConfig(BaseModel):
    w_sim: float = 0.35
    w_graph: float = 0.25
    w_rule: float = 0.15
    w_sev: float = 0.10
    w_comm: float = 0.10
    w_clf: float = 0.30
    w_benign: float = 0.30
    w_session: float = 0.15
    weak_signal_floor: float = 0.25
    min_weak_signals_for_gray: int = 2


class BenignFastPathConfig(BaseModel):
    benign_allow_floor: float = 0.72
    benign_margin_delta: float = 0.08


class TriageThresholds(BaseModel):
    block_threshold: float = 0.78
    allow_threshold: float = 0.42
    corpus_match_override_threshold: float = 0.92


class StructuralConfig(BaseModel):
    structural_block_threshold: float = 0.85
    structural_allow_threshold: float = 0.20


class EmbeddingConfig(BaseModel):
    chunk_overlap_ratio: float = 0.25
    suspicious_ngram_floor: float = 0.15


class RoutingConfig(BaseModel):
    community_confidence_floor: float = 0.55


class CacheConfig(BaseModel):
    semantic_cache_threshold: float = 0.97
    ttl_seconds: int = 3600


class CategoryOverride(BaseModel):
    block_threshold: float | None = None
    allow_threshold: float | None = None
    benign_allow_floor: float | None = None
    benign_margin_delta: float | None = None
    corpus_match_override_threshold: float | None = None


class JudgeConfig(BaseModel):
    rate_cap_per_minute: int = 60
    tighten_block_threshold_delta: float = 0.05
    tighten_weak_signal_floor_delta: float = 0.10
    accept_guard_at_lower_confidence_when_capped: bool = True
    confidence_floor: float = 0.70


class GuardModelConfig(BaseModel):
    enabled: bool = True
    classifier_mode: Literal["parallel", "gray_only"] = "parallel"
    artifact_id: str = "prism-pi-v1"
    artifact_path: str = ""
    uncertain_low: float = 0.35
    uncertain_high: float = 0.65


class TriageConfig(BaseModel):
    gray_zone_policy: Literal["escalate", "fail_open", "fail_closed"] = "fail_closed"
    gray_terminal: bool = False  # True = Phase 1 legacy (fusion_gray is final, no policy)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    benign_fast_path: BenignFastPathConfig = Field(default_factory=BenignFastPathConfig)
    triage: TriageThresholds = Field(default_factory=TriageThresholds)
    structural: StructuralConfig = Field(default_factory=StructuralConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    guard_model: GuardModelConfig = Field(default_factory=GuardModelConfig)
    categories: dict[str, CategoryOverride] = Field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> TriageConfig:
        return cls.model_validate(data)


def _default_config_path() -> Path:
    return Path(resources.files("prismguard.config") / "triage.yaml")


@lru_cache(maxsize=4)
def load_triage_config(path: str | Path | None = None) -> TriageConfig:
    config_path = Path(path) if path is not None else _default_config_path()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected mapping in triage config, got {type(raw)!r}")
    return TriageConfig.from_mapping(raw)
