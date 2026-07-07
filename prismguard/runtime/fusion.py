from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusionResult:
    fused_score: float
    attack_sim: float
    benign_sim: float
    rule_boost: float
    severity_boost: float
    contrastive_margin: float


def fuse_signals(
    *,
    attack_sim: float,
    benign_sim: float,
    rule_matched: bool,
    severity: str,
    w_sim: float = 0.35,
    w_benign: float = 0.30,
    w_rule: float = 0.15,
    w_sev: float = 0.10,
) -> FusionResult:
    severity_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
    sev = severity_map.get(severity, 0.5)
    rule_boost = 1.0 if rule_matched else 0.0
    margin = attack_sim - benign_sim
    fused = (
        w_sim * attack_sim
        + w_rule * rule_boost
        + w_sev * sev
        - w_benign * benign_sim
    )
    fused = max(0.0, min(1.0, fused))
    return FusionResult(
        fused_score=fused,
        attack_sim=attack_sim,
        benign_sim=benign_sim,
        rule_boost=rule_boost,
        severity_boost=sev,
        contrastive_margin=margin,
    )
