from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path


def load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def block_rate(rows: list[dict], *, source: str | None = None) -> tuple[float | None, int, int]:
    attacks = [r for r in rows if r.get("traffic_kind") == "attack"]
    if source:
        attacks = [r for r in attacks if r.get("attack_source") == source]
    if not attacks:
        return None, 0, 0
    blocked = sum(1 for r in attacks if r.get("decision") == "block")
    return blocked / len(attacks), blocked, len(attacks)


def normal_pass(rows: list[dict]) -> tuple[float | None, int, int]:
    normals = [r for r in rows if r.get("traffic_kind") == "normal"]
    if not normals:
        return None, 0, 0
    passed = sum(1 for r in normals if r.get("decision") == "allow")
    return passed / len(normals), passed, len(normals)


def guard_only_estimate(rows: list[dict]) -> dict:
    """Approximate guard time: blocks have no retrieval; use latency_ms as guard-dominated."""
    blocks = [float(r["latency_ms"]) for r in rows if r.get("decision") == "block"]
    attacks = [r for r in rows if r.get("traffic_kind") == "attack"]
    atk_blocks = [float(r["latency_ms"]) for r in attacks if r.get("decision") == "block"]
    return {
        "all_blocks_p50_ms": statistics.median(blocks) if blocks else None,
        "attack_blocks_p50_ms": statistics.median(atk_blocks) if atk_blocks else None,
        "all_blocks_mean_ms": statistics.mean(blocks) if blocks else None,
    }


def summarize(label: str, rows: list[dict]) -> None:
    if not rows:
        print(f"\n## {label}\n(no data)\n")
        return
    lat = [float(r.get("latency_ms") or 0) for r in rows]
    req = [float(r["request_latency_ms"]) for r in rows if r.get("request_latency_ms") is not None]
    holdout_rate, holdout_b, holdout_n = block_rate(rows, source="legal_overlay_holdout")
    pass_rate, pass_n, pass_total = normal_pass(rows)
    clf_mean = statistics.mean(int(r.get("guard_classifier_calls") or 0) for r in rows)
    gen_mean = statistics.mean(int(r.get("guard_generative_llm_calls") or 0) for r in rows)

    print(f"\n## {label} (n={len(rows)})")
    print(f"  Pipeline latency_ms: mean={statistics.mean(lat):.1f}  p50={statistics.median(lat):.1f}")
    if req:
        print(f"  HTTP request_latency_ms: mean={statistics.mean(req):.1f}  p50={statistics.median(req):.1f}")
    g = guard_only_estimate(rows)
    print(f"  Block-path p50 (proxy for fast guard): all={g['all_blocks_p50_ms']:.2f}ms  attack_blocks={g['attack_blocks_p50_ms']:.2f}ms")
    print(f"  Holdout block rate: {holdout_rate:.1%} ({holdout_b}/{holdout_n})" if holdout_rate is not None else "  Holdout: n/a")
    print(f"  Normal pass rate: {pass_rate:.1%} ({pass_n}/{pass_total})" if pass_rate is not None else "  Normal pass: n/a")
    print(f"  Overall attack block rate: {block_rate(rows)[0]:.1%} ({block_rate(rows)[1]}/{block_rate(rows)[2]})")
    print(f"  Classifier calls/request: {clf_mean:.2f}  Judge calls/request: {gen_mean:.3f}")
    print(f"  Top gates: {Counter(r.get('resolution_gate') for r in rows).most_common(5)}")


def main() -> None:
    root = Path("benchmark/law/results/latest")
    combined = load(root / "atk_combined.jsonl")
    print("# FINAL RESULTS RECONCILIATION")
    print("\nTraffic mix: 189 requests = 18 benign law queries + 35 normal scenarios + 105 attacks + 31 benign_adjacent")
    summarize("LOCAL in-process CPL (PrismGuard)", load(root / "cpl.jsonl"))
    summarize("LOCAL in-process CGL (LLM Guard)", load(root / "cgl.jsonl"))
    if combined:
        summarize("DOCKER live CPL (PrismGuard)", [r for r in combined if r.get("stack_id") == "CPL"])
        summarize("DOCKER live CGL (LLM Guard)", [r for r in combined if r.get("stack_id") == "CGL"])

    print("\n## AUTHORITATIVE DETECTION (local in-process, current code, classifier-first)")
    cpl, cgl = load(root / "cpl.jsonl"), load(root / "cgl.jsonl")
    if cpl and cgl:
        h_cpl = block_rate(cpl, source="legal_overlay_holdout")
        h_cgl = block_rate(cgl, source="legal_overlay_holdout")
        print(f"  CPL holdout: {h_cpl[0]:.1%} ({h_cpl[1]}/{h_cpl[2]})")
        print(f"  CGL holdout: {h_cgl[0]:.1%} ({h_cgl[1]}/{h_cgl[2]})")
        n_cpl = normal_pass(cpl)
        n_cgl = normal_pass(cgl)
        print(f"  CPL normal pass: {n_cpl[0]:.1%} ({n_cpl[1]}/{n_cpl[2]})")
        print(f"  CGL normal pass: {n_cgl[0]:.1%} ({n_cgl[1]}/{n_cgl[2]})")


if __name__ == "__main__":
    main()
