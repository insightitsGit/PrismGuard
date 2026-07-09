import json
from pathlib import Path

source = Path("benchmark/law/results/verified/cpl.jsonl")
holdout = []
for line in source.read_text().splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack":
        holdout.append(r)

onnx = json.loads(Path("benchmark/law/results/holdout-ablation-partial.json").read_text())["onnx"]["rows"]
lgg = json.loads(Path("benchmark/law/results/holdout-ablation-partial.json").read_text())["llm_guard"]["rows"]

print(f"{'#':>2}  {'full':>5} {'onnx':>5} {'lgg':>5}  full_gate / onnx_conf  text")
print("-" * 100)
for i, r in enumerate(holdout):
    o, l = onnx[i], lgg[i]
    print(
        f"{i+1:2}  {r['decision']:>5} {o['decision']:>5} {l['decision']:>5}  "
        f"{r['resolution_gate']:18} / {o['confidence']:.2f}  {r['input_text'][:60]}"
    )

full_b = sum(1 for r in holdout if r["decision"] == "block")
onnx_b = sum(1 for r in onnx if r["decision"] == "block")
lgg_b = sum(1 for r in lgg if r["decision"] == "block")

print(f"\nSummary: full={full_b}/14  onnx_only={onnx_b}/14  llm_guard={lgg_b}/14")

print("\nONNX beats full (onnx block, full allow):")
for i, r in enumerate(holdout):
    if onnx[i]["decision"] == "block" and r["decision"] == "allow":
        print(f"  - {r['input_text'][:80]}")

print("\nFull beats ONNX (full block, onnx allow):")
for i, r in enumerate(holdout):
    if r["decision"] == "block" and onnx[i]["decision"] == "allow":
        print(f"  - [{r['resolution_gate']}] {r['input_text'][:80]}")

print("\nEmbedding/corpus-only wins (full block via corpus_match/fusion, onnx allow):")
for i, r in enumerate(holdout):
    if r["decision"] == "block" and onnx[i]["decision"] == "allow":
        if r["resolution_gate"] in ("corpus_match", "fusion_block", "fusion_allow", "benign_fast_path"):
            print(f"  - [{r['resolution_gate']}] {r['input_text'][:80]}")

print("\nStructural/rules-only wins (full block via structural/tier1, onnx allow):")
for i, r in enumerate(holdout):
    if r["decision"] == "block" and onnx[i]["decision"] == "allow":
        if r["resolution_gate"] in ("structural", "tier1_rule"):
            print(f"  - [{r['resolution_gate']}] {r['input_text'][:80]}")
