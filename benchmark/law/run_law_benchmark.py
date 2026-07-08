from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx

from benchmark.law.compare_law import compare_law, write_comparison_report

TARGETS = {
    "CPL": "http://localhost:8010",
    "CGL": "http://localhost:8011",
    "LGL": "http://localhost:8012",
    "LPL": "http://localhost:8013",
}


def smoke_legitimate(targets: dict[str, str], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    from benchmark.law.shared.cases import load_queries

    queries = load_queries()[:3]
    with httpx.Client(timeout=60.0) as client:
        for stack_id, base in targets.items():
            path = output_dir / f"{stack_id.lower()}.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for query in queries:
                    response = client.post(
                        f"{base}/query",
                        json={
                            "text": query.text,
                            "query_id": query.query_id,
                            "traffic_kind": "benign",
                        },
                    )
                    response.raise_for_status()
                    record = response.json()
                    record.update(
                        {
                            "expected_category": query.category_slug,
                            "traffic_kind": "benign",
                            "attack_source": "smoke",
                        }
                    )
                    handle.write(json.dumps(record) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run law benchmark scenarios")
    parser.add_argument("--smoke", action="store_true", help="Benign query smoke test only")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/law/results/latest"))
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--bundled-limit", type=int, default=200)
    args = parser.parse_args()

    if args.wait_seconds:
        time.sleep(args.wait_seconds)

    if args.smoke:
        smoke_legitimate(TARGETS, args.output_dir)
    else:
        from benchmark.law.atk.attack_runner import run_attacks

        run_attacks(
            targets=TARGETS,
            output_dir=args.output_dir,
            bundled_profile="full",
            bundled_limit=args.bundled_limit,
        )

    comparison = compare_law(args.output_dir)
    write_comparison_report(args.output_dir, comparison)
    print(json.dumps(comparison["paired_deltas"], indent=2))


if __name__ == "__main__":
    main()
