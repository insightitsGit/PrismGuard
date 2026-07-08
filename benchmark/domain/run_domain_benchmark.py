"""Domain-specific benchmark runner (healthcare / finance / law)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from benchmark.law.atk.attack_runner import build_traffic_rows
from benchmark.law.compare_law import compare_law, write_comparison_report
from benchmark.law.run_local_benchmark import STACKS
from benchmark.law.shared.http_app import create_app
from prismguard.domains.registry import get_domain_pack


def _load_domain_overlay_rows(path: Path, *, attack_source: str) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    rows: list[dict] = []
    for row in raw.get("entries", []):
        rows.append(
            {
                **row,
                "attack_source": attack_source,
                "traffic_kind": "attack"
                if row.get("category_slug") != "benign_adjacent"
                else "benign_adjacent",
            }
        )
    return rows


def build_domain_traffic_rows(*, domain: str, bundled_limit: int) -> list[dict]:
    """Same traffic mix as law benchmark, with domain pack overlay + holdout."""
    pack = get_domain_pack(domain)
    seeded_source = "legal_overlay_seeded" if domain == "law" else f"{domain}_overlay_seeded"
    holdout_source = "legal_overlay_holdout" if domain == "law" else f"{domain}_holdout"

    if domain == "law":
        return build_traffic_rows(
            bundled_profile="full",
            bundled_limit=bundled_limit,
            include_seeded_overlay=True,
            include_holdout_overlay=True,
        )

    rows = build_traffic_rows(
        bundled_profile="full",
        bundled_limit=bundled_limit,
        include_seeded_overlay=False,
        include_holdout_overlay=False,
    )
    rows.extend(_load_domain_overlay_rows(pack.overlay_path, attack_source=seeded_source))
    if pack.holdout_path is not None:
        rows.extend(_load_domain_overlay_rows(pack.holdout_path, attack_source=holdout_source))
    return rows


def run_domain_benchmark(*, domain: str, output_dir: Path, bundled_limit: int) -> dict:
    os.environ["PRISMGUARD_DOMAIN"] = domain
    output_dir.mkdir(parents=True, exist_ok=True)
    traffic = build_domain_traffic_rows(domain=domain, bundled_limit=bundled_limit)

    for stack_id, framework, guard_cls in STACKS:
        app = create_app(stack_id=stack_id, framework=framework, guard_factory=guard_cls)
        client = TestClient(app)
        out_path = output_dir / f"{stack_id.lower()}.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for row in traffic:
                response = client.post(
                    "/query",
                    json={
                        "text": row["text"],
                        "query_id": row.get("query_id"),
                        "traffic_kind": row.get("traffic_kind", "attack"),
                    },
                )
                record = response.json()
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

    report = compare_law(output_dir, domain=domain)
    write_comparison_report(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run domain-pack benchmark")
    parser.add_argument("--domain", required=True, choices=["law", "healthcare", "finance"])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--bundled-limit", type=int, default=100)
    args = parser.parse_args()
    output_dir = args.output_dir or Path(f"benchmark/{args.domain}/results/latest")
    report = run_domain_benchmark(domain=args.domain, output_dir=output_dir, bundled_limit=args.bundled_limit)
    print(json.dumps(report.get("paired_deltas", {}), indent=2))


if __name__ == "__main__":
    main()
