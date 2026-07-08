"""Compare two law benchmark runs for decision and latency reproducibility."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _row_key(row: dict) -> tuple:
    return (
        row.get("input_text") or row.get("text") or "",
        row.get("traffic_kind") or "",
        row.get("attack_source") or "",
        row.get("query_id") or "",
        row.get("scenario_id") or "",
    )


def compare_runs(run_a: Path, run_b: Path) -> dict:
    stacks = ("cpl", "cgl", "lgl", "lpl")
    report: dict = {"run_a": str(run_a), "run_b": str(run_b), "stacks": {}}
    all_stable = True

    for stack in stacks:
        path_a = run_a / f"{stack}.jsonl"
        path_b = run_b / f"{stack}.jsonl"
        if not path_a.is_file() or not path_b.is_file():
            report["stacks"][stack.upper()] = {"error": "missing jsonl"}
            all_stable = False
            continue

        rows_a = _load_rows(path_a)
        rows_b = _load_rows(path_b)
        if len(rows_a) != len(rows_b):
            report["stacks"][stack.upper()] = {
                "error": "row_count_mismatch",
                "n_a": len(rows_a),
                "n_b": len(rows_b),
            }
            all_stable = False
            continue

        index_b = {_row_key(r): r for r in rows_b}
        decision_mismatches: list[dict] = []
        gate_mismatches: list[dict] = []
        latency_deltas: list[float] = []

        for row_a in rows_a:
            key = _row_key(row_a)
            row_b = index_b.get(key)
            if row_b is None:
                decision_mismatches.append({"key": key, "error": "missing_in_b"})
                continue
            if row_a.get("decision") != row_b.get("decision"):
                decision_mismatches.append(
                    {
                        "text": (row_a.get("input_text") or "")[:80],
                        "decision_a": row_a.get("decision"),
                        "decision_b": row_b.get("decision"),
                        "gate_a": row_a.get("resolution_gate"),
                        "gate_b": row_b.get("resolution_gate"),
                    }
                )
            elif row_a.get("resolution_gate") != row_b.get("resolution_gate"):
                gate_mismatches.append(
                    {
                        "text": (row_a.get("input_text") or "")[:80],
                        "gate_a": row_a.get("resolution_gate"),
                        "gate_b": row_b.get("resolution_gate"),
                    }
                )
            lat_a = float(row_a.get("request_latency_ms") or row_a.get("latency_ms") or 0)
            lat_b = float(row_b.get("request_latency_ms") or row_b.get("latency_ms") or 0)
            latency_deltas.append(abs(lat_b - lat_a))

        stack_report = {
            "n": len(rows_a),
            "decision_mismatches": len(decision_mismatches),
            "gate_mismatches": len(gate_mismatches),
            "latency_abs_delta_mean_ms": round(statistics.mean(latency_deltas), 2) if latency_deltas else 0,
            "latency_abs_delta_p95_ms": round(sorted(latency_deltas)[int(0.95 * (len(latency_deltas) - 1))], 2)
            if latency_deltas
            else 0,
            "stable": not decision_mismatches and not gate_mismatches,
        }
        if decision_mismatches:
            stack_report["decision_mismatch_samples"] = decision_mismatches[:10]
        if gate_mismatches:
            stack_report["gate_mismatch_samples"] = gate_mismatches[:10]
        report["stacks"][stack.upper()] = stack_report
        if not stack_report["stable"]:
            all_stable = False

    report["decisions_stable"] = all_stable
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_a", type=Path)
    parser.add_argument("run_b", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = compare_runs(args.run_a, args.run_b)
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
