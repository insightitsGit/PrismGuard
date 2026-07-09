"""Verify general-domain cold holdout pass rates (ONNX-only path)."""
from __future__ import annotations

import os
import time

os.environ.setdefault("PRISMGUARD_DOMAIN", "general")

from benchmark.general.shared.holdout import load_attack_holdout, load_benign_holdout
from benchmark.law.shared.guards import PrismGuardGate


def main() -> int:
    benign = load_benign_holdout()
    attack = load_attack_holdout()
    print(f"Loading PrismGuard (domain=general, n_benign={len(benign)}, n_attack={len(attack)}) …")
    t0 = time.perf_counter()
    gate = PrismGuardGate(
        gray_zone_policy="fail_open",
        enable_llm_judge=False,
        import_legal_overlay=False,
    )
    print(f"  loaded in {time.perf_counter() - t0:.1f}s")
    print(f"  disagreement_escalation={gate._checker._config.guard_model.disagreement_escalation}")

    b_ok = 0
    a_ok = 0
    benign_gates: dict[str, int] = {}
    for row in benign:
        out = gate.check(row.text)
        benign_gates[out.resolution_gate] = benign_gates.get(out.resolution_gate, 0) + 1
        if out.decision == "allow":
            b_ok += 1
        else:
            print(f"  BENIGN FAIL [{row.scenario_id}]: {out.resolution_gate} — {row.text[:70]}")

    for row in attack:
        out = gate.check(row.text)
        if out.decision == "block":
            a_ok += 1
        else:
            print(f"  ATTACK MISS [{row.scenario_id}]: {out.resolution_gate} — {row.text[:70]}")

    print()
    print(f"benign_holdout: {b_ok}/{len(benign)} allow")
    print(f"attack_holdout: {a_ok}/{len(attack)} block")
    print(f"benign gates: {benign_gates}")
    return 0 if b_ok == len(benign) and a_ok == len(attack) else 1


if __name__ == "__main__":
    raise SystemExit(main())
