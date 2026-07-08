"""Synthetic tenant-context benchmark eval (Phase 3)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from benchmark.law.compare_law import compare_law, write_comparison_report
from benchmark.law.run_local_benchmark import STACKS
from fastapi.testclient import TestClient

from benchmark.law.shared.http_app import create_app
from benchmark.law.shared.seed_overlap import verify_holdout_overlap


def _load_tenant_sim_rows() -> list[dict]:
    path = Path(__file__).resolve().parent / "data" / "tenant_sim_attacks.yaml"
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    rows: list[dict] = []
    for entry in raw.get("entries") or []:
        slug = entry.get("category_slug", "")
        rows.append(
            {
                "text": entry["text"],
                "category_slug": slug,
                "attack_source": "tenant_sim_holdout",
                "traffic_kind": "attack" if slug != "benign_adjacent" else "benign_adjacent",
            }
        )
    return rows


def run_tenant_sim(*, output_dir: Path, lexicon_path: Path | None) -> dict:
    import os

    output_dir.mkdir(parents=True, exist_ok=True)
    if lexicon_path is not None:
        os.environ["PRISMGUARD_TENANT_LEXICON_PATH"] = str(lexicon_path)
    traffic = _load_tenant_sim_rows()
    overlap = verify_holdout_overlap()

    for stack_id, framework, guard_cls in STACKS:
        if stack_id not in {"CPL", "LPL"}:
            continue
        app = create_app(stack_id=stack_id, framework=framework, guard_factory=guard_cls)
        client = TestClient(app)
        out_path = output_dir / f"{stack_id.lower()}_tenant_sim.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for row in traffic:
                response = client.post(
                    "/query",
                    json={"text": row["text"], "traffic_kind": row["traffic_kind"]},
                )
                record = response.json()
                record.update(row)
                handle.write(json.dumps(record) + "\n")

    report = compare_law(output_dir)
    report["tenant_sim_overlap"] = {
        "holdout_clean": overlap.holdout_clean,
        "holdout_vs_tenant_sim": overlap.holdout_vs_tenant_sim,
    }
    write_comparison_report(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic tenant-context eval")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/tenant/results/latest"))
    parser.add_argument("--lexicon-file", type=Path, default=None)
    args = parser.parse_args()
    report = run_tenant_sim(output_dir=args.output_dir, lexicon_path=args.lexicon_file)
    print(json.dumps(report.get("stacks", {}), indent=2))


if __name__ == "__main__":
    main()
