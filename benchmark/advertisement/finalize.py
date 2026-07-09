"""Rebuild comparison reports and advertisement summary from saved jsonl traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark.advertisement.run_all import _headline_metrics, _write_advertisement_summary
from benchmark.advertisement.suites import ADVERTISEMENT_SUITES, suite_by_id
from benchmark.law.compare_law import compare_law, write_comparison_report


def finalize_suite(results_root: Path, suite_id: str) -> dict | None:
    suite_dir = results_root / suite_id
    if not (suite_dir / "cpl.jsonl").is_file():
        return None
    suite = suite_by_id(suite_id)
    report = compare_law(suite_dir, domain=suite.domain, skip_overlap_check=True)
    report["suite"] = {
        "suite_id": suite.suite_id,
        "title": suite.title,
        "description": suite.description,
        "advertisement_use": suite.advertisement_use,
        "domain": suite.domain,
        "traffic_count": report.get("stacks", {}).get("CPL", {}).get("n"),
    }
    write_comparison_report(suite_dir, report, skip_validation=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize advertisement benchmark outputs")
    parser.add_argument("--results-dir", type=Path, required=True)
    args = parser.parse_args()
    reports: list[dict] = []
    for suite in ADVERTISEMENT_SUITES:
        report = finalize_suite(args.results_dir, suite.suite_id)
        if report is not None:
            reports.append(report)
            print(f"finalized {suite.suite_id}")
    _write_advertisement_summary(args.results_dir, reports)
    print(f"summary written to {args.results_dir}")


if __name__ == "__main__":
    main()
