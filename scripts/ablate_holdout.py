"""Holdout ablation: ONNX-only vs corpus/embed-only vs full stack vs LLM Guard."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PRISMGUARD_DOMAIN", "law")


def load_holdout_attacks(source: Path) -> list[dict]:
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [
        r
        for r in rows
        if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
    ]


def block_rate(decisions: list[str]) -> tuple[int, int, float]:
    blocks = sum(1 for d in decisions if d == "block")
    return blocks, len(decisions), blocks / len(decisions) if decisions else 0.0


def run_onnx_only(texts: list[str]) -> list[dict]:
    from prismguard.config.loader import load_triage_config
    from prismguard.runtime.guard_model import create_guard_model

    cfg = load_triage_config(domain="law").guard_model
    model = create_guard_model(cfg)
    if model is None:
        raise RuntimeError("ONNX guard model not loaded")

    rows = []
    for text in texts:
        v = model.check(text)
        if v.decision == "block" and v.confidence >= cfg.classifier_first_block_threshold:
            decision = "block"
            gate = "onnx_high_conf_block"
        elif v.decision == "allow" and v.confidence < cfg.uncertain_low:
            decision = "allow"
            gate = "onnx_high_conf_allow"
        elif v.decision == "block":
            decision = "block"
            gate = "onnx_block"
        elif v.decision == "allow":
            decision = "allow"
            gate = "onnx_allow"
        else:
            decision = "allow"  # uncertain → fail-open for pure-ONNX slice
            gate = "onnx_uncertain_allow"
        rows.append({"decision": decision, "gate": gate, "confidence": v.confidence})
    return rows


def run_corpus_only(texts: list[str]) -> list[dict]:
    from benchmark.law.shared.guards import PrismGuardCorpusScaleGate

    gate = PrismGuardCorpusScaleGate()
    rows = []
    for text in texts:
        out = gate.check(text)
        rows.append({"decision": out.decision, "gate": out.resolution_gate})
    return rows


def run_full(texts: list[str]) -> list[dict]:
    from benchmark.law.shared.guards import PrismGuardGate

    gate = PrismGuardGate()
    rows = []
    for text in texts:
        out = gate.check(text)
        rows.append({"decision": out.decision, "gate": out.resolution_gate})
    return rows


def run_llm_guard(texts: list[str]) -> list[dict]:
    from benchmark.law.shared.guards import LLMGuardGate

    gate = LLMGuardGate()
    rows = []
    for text in texts:
        out = gate.check(text)
        rows.append({"decision": out.decision, "gate": out.resolution_gate})
    return rows


def compare_modes(
    holdout: list[dict],
    mode_rows: list[dict],
    *,
    mode_name: str,
) -> dict:
    texts = [r["input_text"] for r in holdout]
    blocks, n, rate = block_rate([r["decision"] for r in mode_rows])
    full_blocks = sum(1 for r in holdout if r["decision"] == "block")

    unique_vs_full = []
    lost_vs_full = []
    for i, text in enumerate(texts):
        full_dec = holdout[i]["decision"]
        mode_dec = mode_rows[i]["decision"]
        if mode_dec == "block" and full_dec != "block":
            unique_vs_full.append(text[:90])
        if full_dec == "block" and mode_dec != "block":
            lost_vs_full.append((text[:90], holdout[i]["resolution_gate"], mode_rows[i]["gate"]))

    return {
        "mode": mode_name,
        "blocks": blocks,
        "n": n,
        "block_rate": round(rate, 4),
        "unique_blocks_vs_full": unique_vs_full,
        "lost_blocks_vs_full": lost_vs_full,
    }


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("benchmark/law/results/verified/cpl.jsonl")
    holdout = load_holdout_attacks(source)
    texts = [r["input_text"] for r in holdout]
    n = len(texts)
    print(f"Holdout attacks: n={n}\n")

    print("Loading modes (first load is slow) …")
    t0 = time.perf_counter()
    full_rows = run_full(texts)
    print(f"  full stack loaded+run in {time.perf_counter()-t0:.1f}s")

    modes: list[tuple[str, list[dict]]] = [
        ("full_stack (CPL config)", full_rows),
    ]

    t0 = time.perf_counter()
    modes.append(("onnx_only (prism-pi-v1, no corpus path)", run_onnx_only(texts)))
    print(f"  onnx_only in {time.perf_counter()-t0:.1f}s")

    t0 = time.perf_counter()
    modes.append(("corpus_only (no ONNX, full seed + fusion)", run_corpus_only(texts)))
    print(f"  corpus_only in {time.perf_counter()-t0:.1f}s")

    t0 = time.perf_counter()
    modes.append(("llm_guard (DeBERTa classifier)", run_llm_guard(texts)))
    print(f"  llm_guard in {time.perf_counter()-t0:.1f}s")

    # verified full as reference
    full_ref_blocks = sum(1 for r in holdout if r["decision"] == "block")

    print("\n=== Holdout block rate by mode ===")
    print(f"{'Mode':<42} {'Blocks':>8}  {'Rate':>7}")
    print("-" * 62)
    results = []
    for name, rows in modes:
        b, _, rate = block_rate([r["decision"] for r in rows])
        print(f"{name:<42} {b:>3}/{n:<3}  {rate:>6.1%}")
        results.append(compare_modes(holdout, rows, mode_name=name))

    print(f"\n(reference verified CPL jsonl: {full_ref_blocks}/{n})")

    full = results[0]
    onnx = results[1]
    corpus = results[2]
    lgg = results[3]

    print("\n=== Marginal value vs full stack ===")
    for label, res in [("ONNX-only", onnx), ("Corpus-only", corpus), ("LLM Guard", lgg)]:
        print(f"\n{label}:")
        print(f"  lost vs full: {len(res['lost_blocks_vs_full'])} blocks")
        for item in res["lost_blocks_vs_full"][:8]:
            if isinstance(item, tuple):
                text, full_gate, mode_gate = item
                print(f"    - [{full_gate} -> {mode_gate}] {text}")
            else:
                print(f"    - {item}")
        print(f"  unique vs full: {len(res['unique_blocks_vs_full'])}")

    print("\n=== Direct answer ===")
    onnx_b = onnx["blocks"]
    corpus_b = corpus["blocks"]
    lgg_b = lgg["blocks"]
    full_b = full["blocks"]
    best = max((onnx_b, "ONNX-only (prism-pi-v1)"), (corpus_b, "Corpus/embed-only"), (lgg_b, "LLM Guard"))
    print(f"Best holdout block count alone: {best[1]} at {best[0]}/{n}")
    print(f"Full stack: {full_b}/{n} — adds {full_b - max(onnx_b, corpus_b, lgg_b)} vs best single mode")

    out = Path("benchmark/law/results/holdout-ablation.json")
    out.write_text(json.dumps({"holdout_n": n, "results": results}, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
