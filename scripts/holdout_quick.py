from __future__ import annotations

import os

import yaml
from pathlib import Path

from benchmark.law.shared.guards import PrismGuardGate

os.environ.setdefault("PRISMGUARD_DOMAIN", "law")


def main() -> None:
    data = yaml.safe_load(
        (Path("benchmark/law/data/legal_attacks_holdout.yaml")).read_text(encoding="utf-8")
    )
    attacks = data["entries"]
    gate = PrismGuardGate(seed_profile="authored", gray_zone_policy="escalate")
    blocks = allows = 0
    clf_calls = 0
    for row in attacks:
        if row.get("category_slug") == "benign_adjacent":
            continue
        r = gate.check(row["text"])
        clf_calls += r.guard_classifier_calls
        if r.decision == "block":
            blocks += 1
        else:
            allows += 1
        text = row["text"][:60]
        print(f"{r.decision:5} @{r.resolution_gate:20} clf={r.guard_classifier_calls} | {text}...")
    total = blocks + allows
    print(f"HOLDOUT: {blocks}/{total} blocked = {blocks / total:.1%}")
    print(f"Classifier calls: {clf_calls}/{total} = {clf_calls / total:.1%}")


if __name__ == "__main__":
    main()
