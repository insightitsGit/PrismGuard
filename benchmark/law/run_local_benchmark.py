"""In-process law benchmark runner (no Docker required for CPL/LPL; CGL/LGL need llm-guard)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from benchmark.law.atk.attack_runner import build_traffic_rows
from benchmark.law.compare_law import compare_law, write_comparison_report
from benchmark.law.shared.guards import LLMGuardGate, PrismGuardGate
from benchmark.law.shared.http_app import create_app
from benchmark.law.shared.seed_overlap import verify_holdout_overlap

STACKS = [
    ("CPL", "chorusgraph", PrismGuardGate),
    ("CGL", "chorusgraph", LLMGuardGate),
    ("LGL", "langgraph", LLMGuardGate),
    ("LPL", "langgraph", PrismGuardGate),
]


def run_local(*, output_dir: Path, bundled_limit: int, warmup_requests: int = 0) -> dict:
    import os

    os.environ.setdefault("PRISMGUARD_DOMAIN", "law")
    output_dir.mkdir(parents=True, exist_ok=True)
    traffic = build_traffic_rows(
        bundled_profile="full",
        bundled_limit=bundled_limit,
        include_seeded_overlay=True,
        include_holdout_overlay=True,
    )
    overlap = verify_holdout_overlap()

    for stack_id, framework, guard_cls in STACKS:
        app = create_app(stack_id=stack_id, framework=framework, guard_factory=guard_cls)
        client = TestClient(app)
        if warmup_requests > 0:
            for row in traffic[:warmup_requests]:
                client.post(
                    "/query",
                    json={
                        "text": row["text"],
                        "query_id": row.get("query_id"),
                        "traffic_kind": row.get("traffic_kind", "attack"),
                    },
                )
        out_path = output_dir / f"{stack_id.lower()}.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for row in traffic:
                payload = {
                    "text": row["text"],
                    "query_id": row.get("query_id"),
                    "traffic_kind": row.get("traffic_kind", "attack"),
                }
                start = time.perf_counter()
                response = client.post("/query", json=payload)
                request_ms = (time.perf_counter() - start) * 1000
                record = response.json()
                record["request_latency_ms"] = request_ms
                record["latency_ms"] = request_ms
                record.update(
                    {
                        "input_text": row["text"],
                        "expected_category": row.get("category_slug"),
                        "traffic_kind": row.get("traffic_kind", "attack"),
                        "attack_source": row.get("attack_source", ""),
                        "scenario_id": row.get("scenario_id"),
                    }
                )
                handle.write(json.dumps(record) + "\n")

    report = compare_law(output_dir, domain="law")
    report["overlap_check_runtime"] = {
        "holdout_clean": overlap.holdout_clean,
        "bundled_full_minus_authored_count": overlap.bundled_full_minus_authored_count,
    }
    report["harness"] = {
        "latency_primary_field": "request_latency_ms",
        "latency_guard_field": "guard_latency_ms",
        "latency_pipeline_field": "pipeline_latency_ms",
    }
    write_comparison_report(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run in-process law benchmark")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/law/results/latest"))
    parser.add_argument("--bundled-limit", type=int, default=100)
    parser.add_argument(
        "--warmup-requests",
        type=int,
        default=0,
        help="Untimed requests per stack before recording (not included in output)",
    )
    args = parser.parse_args()
    report = run_local(
        output_dir=args.output_dir,
        bundled_limit=args.bundled_limit,
        warmup_requests=args.warmup_requests,
    )
    print(json.dumps(report["paired_deltas"], indent=2))


if __name__ == "__main__":
    main()
