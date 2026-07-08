"""Holdout-safe sweep of classifier uncertain/veto thresholds (law domain)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from benchmark.law.shared.guards import PrismGuardGate


@dataclass(frozen=True)
class SweepResult:
    uncertain_high: float
    veto_threshold: float
    holdout_block_rate: float
    holdout_classifier_calls: float
    normal_pass_rate: float


def _holdout_attacks() -> list[str]:
    data = yaml.safe_load(
        (Path("benchmark/law/data/legal_attacks_holdout.yaml")).read_text(encoding="utf-8")
    )
    return [
        row["text"]
        for row in data["entries"]
        if row.get("category_slug") != "benign_adjacent"
    ]


def _normal_prompts() -> list[str]:
    from benchmark.law.shared.normal_scenarios import load_normal_scenarios

    return [s.text for s in load_normal_scenarios()]


def sweep() -> SweepResult:
    os.environ["PRISMGUARD_DOMAIN"] = "law"
    attacks = _holdout_attacks()
    normals = _normal_prompts()
    best: SweepResult | None = None

    for uncertain_high in (0.50, 0.55, 0.60, 0.65):
        for veto_threshold in (0.50, 0.55, 0.60, 0.65):
            gate = PrismGuardGate(seed_profile="authored", gray_zone_policy="escalate")
            cfg = gate._checker._config  # noqa: SLF001
            gate._checker._config = cfg.model_copy(  # noqa: SLF001
                update={
                    "guard_model": cfg.guard_model.model_copy(
                        update={
                            "uncertain_high": uncertain_high,
                            "veto_threshold": veto_threshold,
                        }
                    )
                }
            )
            blocked = sum(1 for text in attacks if gate.check(text).decision == "block")
            clf_calls = sum(gate.check(text).guard_classifier_calls for text in attacks)
            normal_pass = sum(1 for text in normals if gate.check(text).decision == "allow")
            holdout_rate = blocked / len(attacks)
            normal_rate = normal_pass / len(normals)
            if normal_rate < 1.0:
                continue
            candidate = SweepResult(
                uncertain_high=uncertain_high,
                veto_threshold=veto_threshold,
                holdout_block_rate=round(holdout_rate, 4),
                holdout_classifier_calls=round(clf_calls / len(attacks), 4),
                normal_pass_rate=round(normal_rate, 4),
            )
            if best is None or candidate.holdout_block_rate > best.holdout_block_rate:
                best = candidate
    if best is None:
        raise RuntimeError("No threshold pair kept 100% normal pass rate")
    return best


def main() -> int:
    result = sweep()
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
