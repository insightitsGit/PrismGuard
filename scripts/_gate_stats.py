import json
from collections import defaultdict
from pathlib import Path

rows = [json.loads(l) for l in Path("benchmark/law/results/verified/cpl.jsonl").read_text().splitlines() if l.strip()]
attacks = [
    r
    for r in rows
    if r.get("traffic_kind") in ("attack", "benign_adjacent")
    and r.get("attack_source") not in ("normal_scenario", "law-queries")
]

EMBED_GATES = {
    "corpus_match",
    "fusion_block",
    "fusion_allow",
    "fusion_gray",
    "benign_fast_path",
    "llm_judge",
    "guard_model",
    "guard_model_veto",
}

by_gate: dict[str, dict] = defaultdict(lambda: {"n": 0, "block": 0})
for r in attacks:
    g = r["resolution_gate"]
    by_gate[g]["n"] += 1
    if r["decision"] == "block":
        by_gate[g]["block"] += 1

print("Attack-ish traffic (excl law queries/normals):", len(attacks))
print("Blocks by gate:")
for g, v in sorted(by_gate.items(), key=lambda x: -x[1]["n"]):
    print(f"  {g:28s} n={v['n']:3d} blocks={v['block']:3d}")

embed_blocks = sum(1 for r in attacks if r["resolution_gate"] in EMBED_GATES and r["decision"] == "block")
onnx_blocks = sum(
    1
    for r in attacks
    if r["resolution_gate"] in ("guard_model_first", "guard_model_fast_allow", "guard_model", "guard_model_veto")
    and r["decision"] == "block"
)
rule_blocks = sum(
    1 for r in attacks if r["resolution_gate"] in ("tier1_rule", "tenant_context_rule", "structural") and r["decision"] == "block"
)
print(f"\nTotal blocks: {sum(1 for r in attacks if r['decision']=='block')}")
print(f"  via rules/structural/tier1: {rule_blocks}")
print(f"  via ONNX-named gates: {onnx_blocks}")
print(f"  via embed-path gates (corpus/fusion/judge): {embed_blocks}")
