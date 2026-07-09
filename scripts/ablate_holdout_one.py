"""Holdout ablation — run one mode: onnx | corpus | full | llm_guard | all"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PRISMGUARD_DOMAIN", "law")


def load_holdout(source: Path) -> list[str]:
    rows = [json.loads(l) for l in source.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [
        r["input_text"]
        for r in rows
        if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
    ]


def onnx_only(texts: list[str]) -> list[dict]:
    from prismguard.config.loader import load_triage_config
    from prismguard.runtime.guard_model import create_guard_model

    cfg = load_triage_config(domain="law").guard_model
    model = create_guard_model(cfg)
    assert model is not None
    out = []
    for text in texts:
        v = model.check(text)
        if v.decision == "block":
            decision = "block"
        elif v.decision == "allow" and v.confidence < cfg.uncertain_low:
            decision = "allow"
        else:
            decision = "allow" if v.decision != "block" else "block"
        out.append({"decision": decision, "confidence": v.confidence, "verdict": v.decision})
    return out


def corpus_only(texts: list[str]) -> list[dict]:
    from benchmark.law.shared.guards import PrismGuardCorpusScaleGate

    g = PrismGuardCorpusScaleGate()
    return [{"decision": g.check(t).decision, "gate": g.check(t).resolution_gate} for t in texts]


def full(texts: list[str]) -> list[dict]:
    from benchmark.law.shared.guards import PrismGuardGate

    g = PrismGuardGate()
    return [{"decision": g.check(t).decision, "gate": g.check(t).resolution_gate} for t in texts]


def llm_guard(texts: list[str]) -> list[dict]:
    from benchmark.law.shared.guards import LLMGuardGate

    g = LLMGuardGate()
    return [{"decision": g.check(t).decision} for t in texts]


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("benchmark/law/results/verified/cpl.jsonl")
    texts = load_holdout(source)
    out_path = Path("benchmark/law/results/holdout-ablation-partial.json")

    partial = {}
    if out_path.is_file():
        partial = json.loads(out_path.read_text(encoding="utf-8"))

    runners = {
        "onnx": ("onnx_only", onnx_only),
        "corpus": ("corpus_only", corpus_only),
        "full": ("full_stack", full),
        "llm_guard": ("llm_guard", llm_guard),
    }

    todo = list(runners.keys()) if mode == "all" else [mode]
    for key in todo:
        name, fn = runners[key]
        print(f"Running {name} on {len(texts)} holdout prompts …")
        t0 = time.perf_counter()
        rows = fn(texts)
        blocks = sum(1 for r in rows if r["decision"] == "block")
        partial[key] = {"blocks": blocks, "n": len(texts), "rate": blocks / len(texts), "rows": rows}
        print(f"  {blocks}/{len(texts)} = {100*blocks/len(texts):.1f}% in {time.perf_counter()-t0:.1f}s")

    out_path.write_text(json.dumps(partial, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
