from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from benchmark.advertisement.suites import ADVERTISEMENT_SUITES, suite_by_id
from benchmark.law.compare_law import compare_law, write_comparison_report
from benchmark.law.run_local_benchmark import STACKS
from benchmark.law.shared.http_app import create_app
from benchmark.law.shared.seed_overlap import verify_holdout_overlap, verify_normal_holdout_overlap


def _run_suite(
    *,
    suite_id: str,
    output_dir: Path,
    bundled_limit: int,
    warmup_requests: int,
    domain: str,
) -> dict[str, Any]:
    suite = suite_by_id(suite_id)
    os.environ["PRISMGUARD_DOMAIN"] = domain
    output_dir.mkdir(parents=True, exist_ok=True)
    traffic = suite.build_traffic(bundled_limit=bundled_limit)
    started = time.perf_counter()

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
                        "style": row.get("style"),
                    }
                )
                handle.write(json.dumps(record) + "\n")

    report = compare_law(output_dir, domain=domain, skip_overlap_check=True)
    report["suite"] = {
        "suite_id": suite.suite_id,
        "title": suite.title,
        "description": suite.description,
        "advertisement_use": suite.advertisement_use,
        "domain": domain,
        "traffic_count": len(traffic),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    report["harness"] = {
        "mode": "in_process",
        "latency_primary_field": "request_latency_ms",
        "warmup_requests": warmup_requests,
        "bundled_limit": bundled_limit,
    }
    write_comparison_report(output_dir, report, skip_validation=True)
    return report


def _headline_metrics(report: dict[str, Any]) -> dict[str, Any]:
    cpl = report.get("stacks", {}).get("CPL", {})
    holdout_source = report.get("holdout_source", "legal_overlay_holdout")
    return {
        "suite_id": report.get("suite", {}).get("suite_id"),
        "advertisement_use": report.get("suite", {}).get("advertisement_use"),
        "traffic_count": report.get("suite", {}).get("traffic_count"),
        "cpl_request_latency_ms_mean": cpl.get("request_latency_ms_mean"),
        "cpl_attack_holdout_block_rate": (cpl.get("attack_block_rate_by_source") or {}).get(holdout_source),
        "cpl_attack_block_rate": cpl.get("attack_block_rate"),
        "cpl_normal_scenario_seeded_pass_rate": (cpl.get("normal_pass_rate_by_source") or {}).get(
            "normal_scenario_seeded"
        ),
        "cpl_normal_scenario_holdout_pass_rate": (cpl.get("normal_pass_rate_by_source") or {}).get(
            "normal_scenario_holdout"
        ),
        "cpl_kb_benign_fp_rate": cpl.get("false_positive_rate"),
    }


def _write_advertisement_summary(results_root: Path, suite_reports: list[dict[str, Any]]) -> None:
    overlap = verify_holdout_overlap()
    normal_overlap = verify_normal_holdout_overlap()
    headlines = [_headline_metrics(r) for r in suite_reports]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results_root": str(results_root),
        "overlap_check": {
            "attack_holdout_clean": overlap.holdout_clean,
            "normal_holdout_clean": normal_overlap.holdout_clean,
            "normal_holdout_vs_dev_collisions": normal_overlap.holdout_vs_normal_dev,
            "normal_holdout_vs_hard_negatives": normal_overlap.holdout_vs_hard_negatives,
        },
        "headlines": headlines,
        "suites": [r.get("suite") for r in suite_reports],
    }
    (results_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# PrismGuard Advertisement Benchmark Summary",
        "",
        f"_Generated: {summary['generated_at']}_",
        "",
        "## How to cite these numbers",
        "",
        "| Metric | Suite | Safe for external claims? |",
        "|--------|-------|---------------------------|",
        "| Attack holdout block rate | `attack-holdout` | Yes (cold attack eval) |",
        "| Normal holdout pass rate | `normal-holdout` | Yes (cold benign eval) |",
        "| Normal dev pass rate | `normal-dev` | No — used in tuning/training |",
        "| Seeded overlay block rate | `attack-seeded` | No — in-corpus attacks |",
        "| Full combined benchmark | `law-full` | Supporting context only |",
        "",
        "## CPL headline metrics by suite",
        "",
    ]
    for row in headlines:
        lines.extend(
            [
                f"### `{row.get('suite_id')}` ({row.get('advertisement_use')})",
                f"- traffic_count: {row.get('traffic_count')}",
                f"- request_latency_ms_mean: **{row.get('cpl_request_latency_ms_mean')}**",
                f"- attack_holdout_block_rate: **{row.get('cpl_attack_holdout_block_rate')}**",
                f"- attack_block_rate (suite): **{row.get('cpl_attack_block_rate')}**",
                f"- normal_scenario_seeded_pass_rate: {row.get('cpl_normal_scenario_seeded_pass_rate')}",
                f"- normal_scenario_holdout_pass_rate: **{row.get('cpl_normal_scenario_holdout_pass_rate')}**",
                f"- kb_benign_fp_rate: {row.get('cpl_kb_benign_fp_rate')}",
                "",
            ]
        )

    lines.extend(
        [
            "## Overlap checks",
            f"- attack_holdout_clean: **{overlap.holdout_clean}**",
            f"- normal_holdout_clean: **{normal_overlap.holdout_clean}**",
            f"- normal_holdout_vs_dev_collisions: {normal_overlap.holdout_vs_normal_dev}",
            f"- normal_holdout_vs_hard_negatives: {normal_overlap.holdout_vs_hard_negatives}",
            "",
            "## Suite directories",
            "",
        ]
    )
    for report in suite_reports:
        suite = report.get("suite", {})
        lines.append(f"- `{suite.get('suite_id')}/` — {suite.get('title')}")
    lines.append("")

    (results_root / "ADVERTISEMENT_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")

    readme = [
        "# Advertisement benchmark results",
        "",
        "Separate suites for honest external messaging:",
        "",
        "- **attack-holdout** — cold attack detection (cite this for holdout block rate)",
        "- **normal-holdout** — cold false-positive eval (cite this for benign pass rate)",
        "- **normal-dev** — development/tuned benign set (do not cite as generalization)",
        "- **law-full** — combined harness matching production benchmark shape",
        "- **healthcare-domain** / **finance-domain** — domain pack overlays",
        "",
        "See `ADVERTISEMENT_SUMMARY.md` for CPL headline table and `summary.json` for machine-readable output.",
        "Each subdirectory has `comparison.json`, `COMPARISON_REPORT.md`, and per-stack `*.jsonl` traces.",
        "",
    ]
    (results_root / "README.md").write_text("\n".join(readme), encoding="utf-8")


def run_all_advertisement_benchmarks(
    *,
    output_root: Path | None = None,
    bundled_limit: int = 100,
    warmup_requests: int = 3,
    suite_ids: list[str] | None = None,
    isolate_suites: bool = True,
) -> Path:
    import subprocess
    import sys

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results_root = output_root or Path(f"benchmark/advertisement/results/{stamp}")
    results_root.mkdir(parents=True, exist_ok=True)

    selected = [suite_by_id(sid) for sid in suite_ids] if suite_ids else list(ADVERTISEMENT_SUITES)
    suite_reports: list[dict[str, Any]] = []

    if isolate_suites and len(selected) > 1:
        for suite in selected:
            print(f"Running suite in subprocess: {suite.suite_id} ...", flush=True)
            cmd = [
                sys.executable,
                "-m",
                "benchmark.advertisement.run_all",
                "--output-dir",
                str(results_root),
                "--bundled-limit",
                str(bundled_limit),
                "--warmup-requests",
                str(warmup_requests),
                "--suite",
                suite.suite_id,
                "--no-isolate",
            ]
            subprocess.run(cmd, check=False)
        for suite in selected:
            comparison_path = results_root / suite.suite_id / "comparison.json"
            if comparison_path.is_file():
                suite_reports.append(json.loads(comparison_path.read_text(encoding="utf-8")))
        _write_advertisement_summary(results_root, suite_reports)
        return results_root

    for suite in selected:
        print(f"Running suite: {suite.suite_id} ({suite.domain}) ...", flush=True)
        report = _run_suite(
            suite_id=suite.suite_id,
            output_dir=results_root / suite.suite_id,
            bundled_limit=bundled_limit,
            warmup_requests=warmup_requests,
            domain=suite.domain,
        )
        suite_reports.append(report)
        print(json.dumps(_headline_metrics(report), indent=2), flush=True)

    _write_advertisement_summary(results_root, suite_reports)
    return results_root


def main() -> None:
    parser = argparse.ArgumentParser(description="Run advertisement benchmark suites")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Root output directory (default: benchmark/advertisement/results/<date>)",
    )
    parser.add_argument("--bundled-limit", type=int, default=100)
    parser.add_argument("--warmup-requests", type=int, default=3)
    parser.add_argument("--suite", action="append", dest="suites", help="Run only these suite ids (repeatable)")
    parser.add_argument(
        "--no-isolate",
        action="store_true",
        help="Run all suites in one process (default isolates each suite in a subprocess)",
    )
    args = parser.parse_args()
    root = run_all_advertisement_benchmarks(
        output_root=args.output_dir,
        bundled_limit=args.bundled_limit,
        warmup_requests=args.warmup_requests,
        suite_ids=args.suites,
        isolate_suites=not args.no_isolate and not args.suites,
    )
    print(f"Results written to {root}")


if __name__ == "__main__":
    main()
