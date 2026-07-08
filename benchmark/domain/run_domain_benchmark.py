"""Domain-specific benchmark runner (healthcare / finance / law)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from benchmark.law.atk.attack_runner import build_traffic_rows
from benchmark.law.compare_law import compare_law, write_comparison_report
from benchmark.law.run_local_benchmark import STACKS
from fastapi.testclient import TestClient

from benchmark.law.shared.http_app import create_app
from prismguard.domains.registry import get_domain_pack
from prismguard.seed import import_bundled_seed, import_seeds
from prismguard.seed.parse import parse_seed_file
from prismguard.storage import create_storage


def run_domain_benchmark(*, domain: str, output_dir: Path, bundled_limit: int) -> dict:
    os.environ["PRISMGUARD_DOMAIN"] = domain
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = get_domain_pack(domain)

    storage = create_storage("memory")
    import_bundled_seed(storage, profile="authored")
    import_seeds(storage, parse_seed_file(pack.overlay_path), mode="update")

    traffic = build_traffic_rows(
        bundled_profile="full",
        bundled_limit=bundled_limit,
        include_seeded_overlay=False,
        include_holdout_overlay=pack.holdout_path is not None,
    )
    if pack.holdout_path is not None:
        import yaml

        with pack.holdout_path.open(encoding="utf-8") as handle:
            holdout = yaml.safe_load(handle)
        for entry in holdout.get("entries") or []:
            if entry.get("category_slug") == "benign_adjacent":
                continue
            traffic.append(
                {
                    "text": entry["text"],
                    "category_slug": entry.get("category_slug"),
                    "attack_source": f"{domain}_holdout",
                    "traffic_kind": "attack",
                }
            )

    for stack_id, framework, guard_cls in STACKS:
        app = create_app(stack_id=stack_id, framework=framework, guard_factory=guard_cls)
        client = TestClient(app)
        out_path = output_dir / f"{stack_id.lower()}.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for row in traffic:
                response = client.post(
                    "/query",
                    json={"text": row["text"], "traffic_kind": row.get("traffic_kind", "attack")},
                )
                record = response.json()
                record.update(
                    {
                        "input_text": row["text"],
                        "expected_category": row.get("category_slug"),
                        "traffic_kind": row.get("traffic_kind", "attack"),
                        "attack_source": row.get("attack_source", ""),
                    }
                )
                handle.write(json.dumps(record) + "\n")

    report = compare_law(output_dir)
    report["domain"] = domain
    write_comparison_report(output_dir, report)
    storage.close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run domain-pack benchmark")
    parser.add_argument("--domain", required=True, choices=["law", "healthcare", "finance"])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--bundled-limit", type=int, default=50)
    args = parser.parse_args()
    output_dir = args.output_dir or Path(f"benchmark/{args.domain}/results/latest")
    report = run_domain_benchmark(domain=args.domain, output_dir=output_dir, bundled_limit=args.bundled_limit)
    print(json.dumps(report.get("paired_deltas", {}), indent=2))


if __name__ == "__main__":
    main()
