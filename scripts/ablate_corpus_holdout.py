import json
import os
from pathlib import Path

os.environ["PRISMGUARD_DOMAIN"] = "law"

from benchmark.law.shared.guards import PrismGuardPhase1Gate, PrismGuardCorpusScaleGate

source = Path("benchmark/law/results/verified/cpl.jsonl")
rows = [json.loads(l) for l in source.read_text().splitlines() if l.strip()]
texts = [
    r["input_text"]
    for r in rows
    if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
]
full = {
    r["input_text"]: r
    for r in rows
    if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
}

for label, factory in [
    ("phase1_corpus (authored seed, no ONNX)", PrismGuardPhase1Gate),
    ("corpus_scale (full seed, no ONNX)", PrismGuardCorpusScaleGate),
]:
    print(f"\n=== {label} ===")
    g = factory()
    blocks = 0
    for text in texts:
        r = g.check(text)
        if r.decision == "block":
            blocks += 1
        ref = full[text]
        mark = " *" if r.decision != ref["decision"] else ""
        print(f"  {r.decision:5} [{r.resolution_gate:20}] full={ref['decision']:5}{mark} | {text[:70]}")
    print(f"Total: {blocks}/{len(texts)} = {100*blocks/len(texts):.1f}%")
