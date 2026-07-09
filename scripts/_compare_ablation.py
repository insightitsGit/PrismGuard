import json
from pathlib import Path

source = Path("benchmark/law/results/verified/cpl.jsonl")
holdout = [
    json.loads(l)
    for l in source.read_text().splitlines()
    if l.strip()
    and json.loads(l).get("attack_source") == "legal_overlay_holdout"
    and json.loads(l).get("traffic_kind") == "attack"
]
# fix double parse
holdout = []
for line in source.read_text().splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack":
        holdout.append(r)

partial = json.loads(Path("benchmark/law/results/holdout-ablation-partial.json").read_text())
onnx = partial["onnx"]["rows"]
llm = partial["llm_guard"]["rows"]

print("Per-prompt holdout comparison (ONNX-only vs verified full vs LLM Guard):\n")
for i, r in enumerate(holdout):
    text = r["input_text"][:85]
    full = r["decision"]
    full_gate = r["resolution_gate"]
    o = onnx[i]
    l = llm[i]
    print(f"{i+1:2}. full={full:5} [{full_gate:20}] | onnx={o['decision']:5} conf={o['confidence']:.2f} | lgg={l['decision']:5}")
    print(f"    {text}")

if "corpus" in partial:
    corpus = partial["corpus"]["rows"]
    print(f"\nCorpus-only: {partial['corpus']['blocks']}/{partial['corpus']['n']}")
    for i, r in enumerate(holdout):
        if corpus[i]["decision"] != r["decision"]:
            print(f"  diff: full={r['decision']} corpus={corpus[i]['decision']} gate={corpus[i].get('gate')} | {r['input_text'][:70]}")
