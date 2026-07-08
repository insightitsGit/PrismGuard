"""Quick pipeline check: law normals + holdout after threshold tuning."""

from __future__ import annotations

import os

os.environ.setdefault("PRISMGUARD_DOMAIN", "law")

from benchmark.law.shared.guards import PrismGuardGate
from benchmark.law.shared.normal_scenarios import load_normal_scenarios
from prismguard.models.eval import _holdout_rows


def main() -> None:
    gate = PrismGuardGate()
    normals = load_normal_scenarios()
    attacks = [r for r in _holdout_rows("law") if r["traffic_kind"] == "attack"]

    allowed = sum(1 for s in normals if gate.check(s.text).decision == "allow")
    blocked = sum(1 for r in attacks if gate.check(r["text"]).decision == "block")
    print(f"PIPELINE normal_allow={allowed}/{len(normals)} ({allowed/len(normals):.1%})")
    print(f"PIPELINE holdout_block={blocked}/{len(attacks)} ({blocked/len(attacks):.1%})")

    fails = [s for s in normals if gate.check(s.text).decision != "allow"]
    for s in fails[:5]:
        out = gate.check(s.text)
        print(f"  FAIL {out.decision} gate={out.resolution_gate} | {s.text[:70]}")


if __name__ == "__main__":
    main()
