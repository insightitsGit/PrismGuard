from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FusionResult:
    fused_score: float
    attack_sim: float
    benign_sim: float
    rule_boost: float
    severity_boost: float
    graph_score: float
    community_confidence: float
    classifier_prob: float
    contrastive_margin: float
    weak_signal_count: int


def count_weak_signals(
    *,
    attack_sim: float,
    rule_boost: float,
    severity_boost: float,
    graph_score: float,
    community_confidence: float,
    classifier_prob: float,
    weak_signal_floor: float,
) -> int:
    signals = (
        attack_sim,
        rule_boost,
        severity_boost,
        graph_score,
        community_confidence,
        classifier_prob,
    )
    return sum(1 for value in signals if value >= weak_signal_floor)


def fuse_signals(
    *,
    attack_sim: float,
    benign_sim: float,
    rule_matched: bool,
    severity: str,
    graph_score: float = 0.0,
    community_confidence: float = 0.0,
    classifier_prob: float | None = None,
    w_sim: float = 0.35,
    w_graph: float = 0.25,
    w_rule: float = 0.15,
    w_sev: float = 0.10,
    w_comm: float = 0.10,
    w_clf: float = 0.0,
    w_benign: float = 0.30,
    weak_signal_floor: float = 0.25,
) -> FusionResult:
    severity_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
    sev = severity_map.get(severity, 0.5)
    rule_boost = 1.0 if rule_matched else 0.0
    clf = float(classifier_prob) if classifier_prob is not None else 0.0
    margin = attack_sim - benign_sim
    fused = (
        w_sim * attack_sim
        + w_graph * graph_score
        + w_rule * rule_boost
        + w_sev * sev
        + w_comm * community_confidence
        + w_clf * clf
        - w_benign * benign_sim
    )
    fused = max(0.0, min(1.0, fused))
    weak_count = count_weak_signals(
        attack_sim=attack_sim,
        rule_boost=rule_boost,
        severity_boost=sev,
        graph_score=graph_score,
        community_confidence=community_confidence,
        classifier_prob=clf,
        weak_signal_floor=weak_signal_floor,
    )
    return FusionResult(
        fused_score=fused,
        attack_sim=attack_sim,
        benign_sim=benign_sim,
        rule_boost=rule_boost,
        severity_boost=sev,
        graph_score=graph_score,
        community_confidence=community_confidence,
        classifier_prob=clf,
        contrastive_margin=margin,
        weak_signal_count=weak_count,
    )
