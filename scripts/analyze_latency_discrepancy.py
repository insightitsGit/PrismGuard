from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path("benchmark/law/results/latest")


def summarize(rows: list[dict], label: str) -> None:
    if not rows:
        return
    lat = [float(r.get("latency_ms") or 0) for r in rows]
    req = [float(r["request_latency_ms"]) for r in rows if r.get("request_latency_ms") is not None]
    print(f"=== {label} n={len(rows)} ===")
    print(f"  latency_ms mean={statistics.mean(lat):.1f} p50={statistics.median(lat):.1f}")
    if req:
        print(f"  request_latency_ms mean={statistics.mean(req):.1f} p50={statistics.median(req):.1f}")
        # rows where internal >> external
        mism = [
            r
            for r in rows
            if r.get("request_latency_ms") is not None
            and float(r["latency_ms"]) > float(r["request_latency_ms"]) * 2
        ]
        print(f"  internal > 2x request: {len(mism)}/{len(req)}")
    clf0 = sum(1 for r in rows if int(r.get("guard_classifier_calls") or 0) == 0)
    print(f"  guard_classifier_calls=0: {clf0}/{len(rows)}")
    print(f"  top gates: {Counter(r.get('resolution_gate') for r in rows).most_common(4)}")
    print()


def main() -> None:
    for fname in ("cpl.jsonl", "cgl.jsonl"):
        path = ROOT / fname
        if path.is_file():
            rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            summarize(rows, f"local {fname}")

    combined = ROOT / "atk_combined.jsonl"
    if combined.is_file():
        rows = [json.loads(line) for line in combined.read_text().splitlines() if line.strip()]
        for stack in ("CPL", "CGL"):
            summarize([r for r in rows if r.get("stack_id") == stack], f"docker atk {stack}")


if __name__ == "__main__":
    main()
