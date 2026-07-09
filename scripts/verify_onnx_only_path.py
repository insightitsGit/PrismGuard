"""Quick verify ONNX-only path (corpus_path_enabled=false) vs attack/normal holdout."""
import json
import os
import time
from pathlib import Path

os.environ["PRISMGUARD_DOMAIN"] = "law"

from benchmark.law.shared.guards import PrismGuardGate
from benchmark.law.shared.normal_holdout import load_normal_holdout_scenarios
from benchmark.law.shared.normal_scenarios import load_normal_scenarios

source = Path("benchmark/law/results/verified/cpl.jsonl")
rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]

holdout = [
    r
    for r in rows
    if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
]
seeded = [r for r in rows if r.get("attack_source") in ("normal_scenario", "normal_scenario_seeded")]

print("Loading PrismGuard (corpus_path_enabled=false in triage.yaml) …")
t0 = time.perf_counter()
gate = PrismGuardGate()
print(f"  loaded in {time.perf_counter() - t0:.1f}s")
print(f"  corpus_path_enabled={gate._checker._config.embedding.corpus_path_enabled}")


def run_batch(batch, label, *, expect_blocks: bool) -> tuple[int, int]:
    ok = 0
    latencies = []
    gates: dict[str, int] = {}
    for row in batch:
        start = time.perf_counter()
        out = gate.check(row["text"] if "text" in row else row["input_text"])
        latencies.append((time.perf_counter() - start) * 1000)
        gates[out.resolution_gate] = gates.get(out.resolution_gate, 0) + 1
        if expect_blocks:
            if out.decision == "block":
                ok += 1
        elif out.decision == "allow":
            ok += 1
    n = len(batch)
    rate = ok / n if n else 0
    mean_lat = sum(latencies) / len(latencies) if latencies else 0
    print(f"\n{label}: {ok}/{n} ({100 * rate:.1f}%)  mean_latency={mean_lat:.0f}ms")
    print(f"  gates: {dict(sorted(gates.items(), key=lambda x: -x[1]))}")
    return ok, n


print("\n--- Verified reference ---")
print(f"  holdout blocks: {sum(1 for r in holdout if r['decision'] == 'block')}/{len(holdout)}")
print(f"  seeded normal pass: {sum(1 for r in seeded if r['decision'] == 'allow')}/{len(seeded)}")

run_batch(
    [{"text": e.text} for e in load_normal_scenarios()],
    "normal_scenario_seeded (ONNX-only path)",
    expect_blocks=False,
)
run_batch(
    [{"text": e.text} for e in load_normal_holdout_scenarios()],
    "normal_scenario_holdout (ONNX-only path)",
    expect_blocks=False,
)
