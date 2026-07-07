"""Corpus-scale experiment: full seed profile, Phase 1 only (Bug3 T5)."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.law.atk.attack_runner import build_traffic_rows
from benchmark.law.compare_law import compare_law, write_comparison_report
from benchmark.law.shared.guards import PrismGuardCorpusScaleGate, PrismGuardPhase1Gate
from benchmark.law.shared.http_app import create_app
from fastapi.testclient import TestClient


def run_corpus_scale(*, output_dir: Path, bundled_limit: int = 100) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    traffic = build_traffic_rows(
        bundled_profile="full",
        bundled_limit=bundled_limit,
        include_seeded_overlay=True,
        include_holdout_overlay=True,
    )
    stacks = [
        ("cpl_authored", PrismGuardPhase1Gate()),
        ("cpl_full", PrismGuardCorpusScaleGate()),
    ]
    for stack_id, guard in stacks:
        guard_factory = (lambda g: lambda: g)(guard)
        app = create_app(stack_id=stack_id.upper(), framework="chorusgraph", guard_factory=guard_factory)
        client = TestClient(app)
        out_path = output_dir / f"{stack_id}.jsonl"
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

    authored = compare_law(output_dir.parent / "latest")
    full_report = {
        "authored_baseline": {
            "holdout": authored["stacks"].get("CPL", {}).get("attack_block_rate_by_source", {}).get(
                "legal_overlay_holdout"
            ),
            "normal_pass": authored["stacks"].get("CPL", {}).get("normal_scenarios", {}).get("pass_rate"),
        },
    }
    for key in ("cpl_authored", "cpl_full"):
        path = output_dir / f"{key}.jsonl"
        if path.is_file():
            from benchmark.law.compare_law import load_jsonl, summarize_stack

            summary = summarize_stack(load_jsonl(path))
            full_report[key] = {
                "holdout_block_rate": summary.get("attack_block_rate_by_source", {}).get("legal_overlay_holdout"),
                "normal_pass_rate": summary.get("normal_scenarios", {}).get("pass_rate"),
            }
    (output_dir / "corpus_scale.json").write_text(json.dumps(full_report, indent=2), encoding="utf-8")
    return full_report


def main() -> None:
    report = run_corpus_scale(output_dir=Path("benchmark/law/results/corpus_scale"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
