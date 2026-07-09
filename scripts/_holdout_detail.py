import json
from pathlib import Path

cpl_rows = [
    json.loads(l)
    for l in Path("benchmark/law/results/verified/cpl.jsonl").read_text().splitlines()
    if l.strip()
]
cgl_rows = [
    json.loads(l)
    for l in Path("benchmark/law/results/verified/cgl.jsonl").read_text().splitlines()
    if l.strip()
]

def holdout(rows):
    return {
        r["input_text"]: r
        for r in rows
        if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
    }

cpl, cgl = holdout(cpl_rows), holdout(cgl_rows)
print("HOLDOUT DETAIL (14 attacks)\n")
for i, text in enumerate(sorted(cpl.keys()), 1):
    a, b = cpl[text], cgl[text]
    if a["decision"] == "block" and b["decision"] == "allow":
        tag = "CPL-only win"
    elif a["decision"] == "allow" and b["decision"] == "block":
        tag = "CGL-only win"
    elif a["decision"] == "allow" and b["decision"] == "allow":
        tag = "BOTH MISS"
    else:
        tag = "both block"
    print(f"{i:2}. CPL {a['decision']:5} [{a['resolution_gate']:22}] | CGL {b['decision']:5} | {tag}")
    print(f"    {text[:100]}\n")

# Attribute wins by component type
COMPONENT = {
    "tier1_rule": "rules (no ONNX, no embed)",
    "structural": "structural regex (no embed path)",
    "guard_model_first": "ONNX early block",
    "guard_model": "ONNX gray escalation",
    "guard_model_fast_allow": "ONNX",
    "guard_model_veto": "ONNX veto",
    "corpus_match": "embedding + ANN corpus",
    "fusion_block": "embedding + ANN + fusion (+ ONNX prob)",
    "fusion_allow": "embedding + ANN + fusion",
    "benign_fast_path": "embedding + ANN",
    "llm_judge": "ONNX uncertain + judge",
}

print("CPL block attribution (holdout):")
for text in sorted(cpl.keys()):
    r = cpl[text]
    if r["decision"] != "block":
        continue
    gate = r["resolution_gate"]
    comp = COMPONENT.get(gate, gate)
    cgl_dec = cgl[text]["decision"]
    extra = " (vs CGL allow)" if cgl_dec == "allow" else ""
    print(f"  [{gate}] -> {comp}{extra}")
