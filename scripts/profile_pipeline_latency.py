#!/usr/bin/env python3
"""Quick pipeline latency profile — which stage dominates (ONNX, embed, ANN, …)?

Usage:
  # Quick sample (~40 requests, stratified by resolution gate)
  python scripts/profile_pipeline_latency.py --quick

  # Full verified CPL traffic (189 requests, ~15–25 min cold)
  python scripts/profile_pipeline_latency.py

  # Per-request JSON logs to stderr
  python scripts/profile_pipeline_latency.py --quick --log

Environment (also set automatically by this script):
  PRISMGUARD_PROFILE_STAGES=1   — collect stage_latency_ms on each check
  PRISMGUARD_PROFILE_LOG=1      — log one JSON line per request (with --log)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path


def _load_sample_texts(source: Path, *, limit: int | None, quick: bool) -> list[dict]:
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not quick and limit is None:
        return [{"text": r["input_text"], "gate": r.get("resolution_gate", ""), "meta": r} for r in rows]

    by_gate: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_gate[r.get("resolution_gate", "unknown")].append(r)

    picked: list[dict] = []
    if quick:
        # Holdout first, then up to 3 per gate type.
        holdout = [
            r
            for r in rows
            if r.get("attack_source") == "legal_overlay_holdout" and r.get("traffic_kind") == "attack"
        ]
        for r in holdout:
            picked.append({"text": r["input_text"], "gate": r.get("resolution_gate", ""), "meta": r})
        for gate, items in sorted(by_gate.items()):
            for r in items[:3]:
                entry = {"text": r["input_text"], "gate": gate, "meta": r}
                if entry not in picked:
                    picked.append(entry)
        if limit is not None:
            return picked[:limit]
        return picked

    if limit is not None:
        rows = rows[:limit]
    return [{"text": r["input_text"], "gate": r.get("resolution_gate", ""), "meta": r} for r in rows]


def _aggregate(records: list[dict]) -> dict:
    """Build summary stats from list of {gate, wall_ms, stages, buckets}."""
    stage_vals: dict[str, list[float]] = defaultdict(list)
    bucket_vals: dict[str, list[float]] = defaultdict(list)
    wall_vals: list[float] = []
    by_gate: dict[str, list[dict]] = defaultdict(list)

    for rec in records:
        wall_vals.append(rec["wall_ms"])
        by_gate[rec["gate"]].append(rec)
        for k, v in rec.get("stages", {}).items():
            stage_vals[k].append(v)
        for k, v in rec.get("buckets", {}).items():
            bucket_vals[k].append(v)

    def stats(vals: list[float]) -> dict:
        if not vals:
            return {"n": 0, "mean": 0.0, "p95": 0.0}
        ordered = sorted(vals)
        p95 = ordered[int(0.95 * (len(ordered) - 1))]
        return {"n": len(vals), "mean": round(statistics.mean(vals), 2), "p95": round(p95, 2)}

    bucket_means = {k: statistics.mean(v) for k, v in bucket_vals.items() if v}
    total_mean = sum(bucket_means.values()) or 1.0
    bucket_share = {k: round(100 * v / total_mean, 1) for k, v in sorted(bucket_means.items(), key=lambda x: -x[1])}

    gate_summary = {}
    for gate, items in sorted(by_gate.items()):
        g_buckets: dict[str, list[float]] = defaultdict(list)
        for item in items:
            for k, v in item.get("buckets", {}).items():
                g_buckets[k].append(v)
        gate_summary[gate] = {
            "n": len(items),
            "wall_ms_mean": round(statistics.mean(i["wall_ms"] for i in items), 2),
            "top_bucket": max(g_buckets.items(), key=lambda x: statistics.mean(x[1]))[0] if g_buckets else "",
        }

    return {
        "requests": len(records),
        "wall_ms": stats(wall_vals),
        "buckets": {k: stats(v) for k, v in sorted(bucket_vals.items())},
        "bucket_share_pct": bucket_share,
        "raw_stages": {k: stats(v) for k, v in sorted(stage_vals.items())},
        "by_resolution_gate": gate_summary,
    }


def _print_report(summary: dict, *, llm_guard_mean: float | None) -> None:
    print("\n=== PrismGuard pipeline latency profile ===")
    print(f"Requests: {summary['requests']}")
    w = summary["wall_ms"]
    print(f"Wall clock (check()): mean={w['mean']}ms  p95={w['p95']}ms\n")

    print("Stage buckets (% of summed stage time, mean ms):")
    share = summary["bucket_share_pct"]
    buckets = summary["buckets"]
    for name, pct in share.items():
        b = buckets.get(name, {"mean": 0, "p95": 0})
        print(f"  {name:18s}  {pct:5.1f}%   mean={b['mean']:7.1f}ms  p95={b['p95']:7.1f}ms")

    print("\nRaw stages (finer grain):")
    for name, s in summary["raw_stages"].items():
        print(f"  {name:18s}  mean={s['mean']:7.1f}ms  p95={s['p95']:7.1f}ms  n={s['n']}")

    if llm_guard_mean is not None:
        print(f"\nLLM Guard (single scan) mean wall: {llm_guard_mean:.1f}ms")

    print("\nBy resolution gate (wall ms mean, dominant bucket):")
    for gate, info in summary["by_resolution_gate"].items():
        print(f"  {gate:24s}  n={info['n']:3d}  wall={info['wall_ms_mean']:7.1f}ms  top={info['top_bucket']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("benchmark/law/results/verified/cpl.jsonl"),
        help="Traffic source (default: verified CPL jsonl)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap number of requests")
    parser.add_argument("--quick", action="store_true", help="Holdout + 3 samples per resolution gate")
    parser.add_argument("--output", type=Path, default=Path("benchmark/law/results/pipeline-profile.json"))
    parser.add_argument("--log", action="store_true", help="Emit per-request JSON logs")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup checks before measuring")
    parser.add_argument("--skip-llm-guard", action="store_true", help="Skip LLM Guard baseline timing")
    args = parser.parse_args()

    os.environ["PRISMGUARD_PROFILE_STAGES"] = "1"
    os.environ["PRISMGUARD_DOMAIN"] = "law"
    if args.log:
        os.environ["PRISMGUARD_PROFILE_LOG"] = "1"
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.source.is_file():
        print(f"Source not found: {args.source}", file=sys.stderr)
        return 1

    samples = _load_sample_texts(args.source, limit=args.limit, quick=args.quick)
    print(f"Profiling {len(samples)} requests from {args.source} …")

    from benchmark.law.shared.guards import LLMGuardGate, PrismGuardGate

    print("Loading PrismGuard (first request loads embedder + ONNX) …")
    guard = PrismGuardGate()
    checker = guard._checker  # noqa: SLF001

    warmup_text = samples[0]["text"] if samples else "warmup"
    for i in range(args.warmup):
        checker.check(warmup_text)

    records: list[dict] = []
    t0 = time.perf_counter()
    for i, sample in enumerate(samples):
        start = time.perf_counter()
        result = checker.check(sample["text"])
        wall = (time.perf_counter() - start) * 1000
        details = result.details or {}
        records.append(
            {
                "text": sample["text"][:80],
                "gate": result.resolution_gate,
                "expected_gate": sample.get("gate"),
                "decision": result.decision,
                "wall_ms": wall,
                "stages": details.get("stage_latency_ms", {}),
                "buckets": details.get("stage_bucket_ms", {}),
                "stage_total_ms": details.get("stage_total_ms"),
            }
        )
        if (i + 1) % 10 == 0:
            print(f"  … {i + 1}/{len(samples)}")
    elapsed = time.perf_counter() - t0
    print(f"Done in {elapsed:.1f}s")

    summary = _aggregate(records)
    summary["source"] = str(args.source)
    summary["quick"] = args.quick
    summary["records"] = records

    llm_mean: float | None = None
    if not args.skip_llm_guard:
        try:
            lg = LLMGuardGate()
            lg_times = []
            for sample in samples[: min(10, len(samples))]:
                s = time.perf_counter()
                lg.check(sample["text"])
                lg_times.append((time.perf_counter() - s) * 1000)
            llm_mean = statistics.mean(lg_times) if lg_times else None
            summary["llm_guard_wall_ms_mean"] = llm_mean
        except Exception as exc:
            summary["llm_guard_error"] = str(exc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Write slim summary without full records for quick diff
    slim = {k: v for k, v in summary.items() if k != "records"}
    args.output.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")

    _print_report(summary, llm_guard_mean=llm_mean)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
