"""Cold vs warm latency and concurrent probe for PrismGuard law gate."""

from __future__ import annotations

import argparse
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault("PRISMGUARD_DOMAIN", "law")


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[idx]


def _timed_check(gate, text: str) -> tuple[float, str]:
    start = time.perf_counter()
    outcome = gate.check(text)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, outcome.resolution_gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=5, help="Warm repeats per prompt")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent probe workers")
    parser.add_argument(
        "--prompt",
        default="What is the standard notice period in our mutual NDA template?",
        help="Benign normal-traffic prompt",
    )
    args = parser.parse_args()

    from benchmark.law.shared.guards import PrismGuardGate

    print("=== Cold start (new PrismGuardGate) ===")
    cold_start = time.perf_counter()
    gate = PrismGuardGate(seed_profile="authored", gray_zone_policy="escalate")
    cold_init_ms = (time.perf_counter() - cold_start) * 1000
    cold_lat, cold_gate = _timed_check(gate, args.prompt)
    print(f"init_ms={cold_init_ms:.1f} first_check_ms={cold_lat:.1f} gate={cold_gate}")

    print("\n=== Warm single-thread ===")
    warm_latencies: list[float] = []
    gates: list[str] = []
    for _ in range(args.samples):
        lat, gate_name = _timed_check(gate, args.prompt)
        warm_latencies.append(lat)
        gates.append(gate_name)
    print(
        f"n={len(warm_latencies)} "
        f"p50={statistics.median(warm_latencies):.1f}ms "
        f"p95={_percentile(warm_latencies, 95):.1f}ms "
        f"gates={sorted(set(gates))}"
    )

    print(f"\n=== Concurrent probe (workers={args.concurrency}, n={args.samples}) ===")
    concurrent_latencies: list[float] = []

    def _worker(_: int) -> float:
        lat, _ = _timed_check(gate, args.prompt)
        return lat

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(_worker, i) for i in range(args.samples)]
        for fut in as_completed(futures):
            concurrent_latencies.append(fut.result())
    wall_ms = (time.perf_counter() - start) * 1000
    print(
        f"wall_ms={wall_ms:.1f} "
        f"per_req_p50={statistics.median(concurrent_latencies):.1f}ms "
        f"per_req_p95={_percentile(concurrent_latencies, 95):.1f}ms"
    )


if __name__ == "__main__":
    main()
