"""Quick verify ONNX-only path (corpus_path_enabled=false) vs holdout + normals."""
import json
import os
import time
from pathlib import Path

os.environ["PRISMGUARD_DOMAIN"] = "law"

from benchmark.law.shared.guards import PrismGuardGate

source = Path("benchmark/law/results/verified/cpl.jsonl")
rows = [json.loads(l) for l in source.read_text().splitlines() if l.strip()]

holdout = [r for r in rows if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"]
normals = [r for r in rows if r.get("attack_source") == "normal_scenario"]

print("Loading PrismGuard (corpus_path_enabled=false in triage.yaml) …")
t0 = time.perf_counter()
gate = PrismGuardGate()
print(f"  loaded in {time.perf_counter()-t0:.1f}s")

# confirm config
print(f"  corpus_path_enabled={gate._checker._config.embedding.corpus_path_enabled}")

def run_batch(batch, label):
    blocks_or_pass = 0
    latencies = []
    gates = {}
    for r in batch:
        start = time.perf_counter()
        out = gate.check(r["input_text"])
        latencies.append((time.perf_counter() - start) * 1000)
        gates[out.resolution_gate] = gates.get(out.resolution_gate, 0) + 1
        if label.startswith("holdout"):
            if out.decision == "block":
                blocks_or_pass += 1
        else:
            if out.decision != "block":
                blocks_or_pass += 1
    n = len(batch)
    rate = blocks_or_pass / n if n else 0
    mean_lat = sum(latencies) / len(latencies) if latencies else 0
    print(f"\n{label}: {blocks_or_pass}/{n} ({100*rate:.1f}%)  mean_latency={mean_lat:.0f}ms")
    print(f"  gates: {dict(sorted(gates.items(), key=lambda x: -x[1]))}")
    return blocks_or_pass, n

print("\n--- Verified reference ---")
print(f"  holdout blocks: {sum(1 for r in holdout if r['decision']=='block')}/{len(holdout)}")
print(f"  normal pass:    {sum(1 for r in normals if r['decision']!='block')}/{len(normals)}")

run_batch(holdout, "holdout (ONNX-only path)")
run_batch(normals, "normals (ONNX-only path)")
