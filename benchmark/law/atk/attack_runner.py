from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
import yaml

from benchmark.law.shared.cases import load_queries
from benchmark.law.shared.normal_scenarios import load_normal_scenarios

DEFAULT_TARGETS = {
    "CPL": "http://cpl:8080",
    "CGL": "http://cgl:8080",
    "LGL": "http://lgl:8080",
    "LPL": "http://lpl:8080",
}

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_attack_overlay(path: Path, *, attack_source: str) -> list[dict]:
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


def _load_bundled_attacks(profile: str, limit: int | None) -> list[dict]:
    from prismguard.seed import load_bundled_seed

    parsed = load_bundled_seed(profile=profile)  # type: ignore[arg-type]
    rows = [
        {
            "text": entry.canonical_text(),
            "category_slug": entry.category_slug,
            "source": entry.source,
            "attack_source": "bundled_full",
            "traffic_kind": "attack" if entry.category_slug != "benign_adjacent" else "benign_adjacent",
        }
        for entry in parsed.entries
    ]
    if limit is not None:
        return rows[:limit]
    return rows


def _post_target(client: httpx.Client, base_url: str, payload: dict) -> dict:
    start = time.perf_counter()
    response = client.post(f"{base_url}/query", json=payload, timeout=180.0)
    response.raise_for_status()
    body = response.json()
    body["request_latency_ms"] = (time.perf_counter() - start) * 1000
    body["latency_ms"] = body["request_latency_ms"]
    return body


def build_traffic_rows(
    *,
    bundled_profile: str,
    bundled_limit: int | None,
    include_seeded_overlay: bool,
    include_holdout_overlay: bool,
) -> list[dict]:
    rows: list[dict] = []

    queries = load_queries()
    rows.extend(
        {
            "text": q.text,
            "query_id": q.query_id,
            "category_slug": q.category_slug,
            "traffic_kind": "benign",
            "attack_source": "law-queries",
        }
        for q in queries
    )

    rows.extend(
        {
            "text": s.text,
            "scenario_id": s.scenario_id,
            "category_slug": s.category_hint,
            "traffic_kind": "normal",
            "attack_source": "normal_scenario",
        }
        for s in load_normal_scenarios()
    )

    if include_seeded_overlay:
        rows.extend(_load_attack_overlay(_DATA_DIR / "legal_attacks.yaml", attack_source="legal_overlay_seeded"))
    if include_holdout_overlay:
        rows.extend(
            _load_attack_overlay(_DATA_DIR / "legal_attacks_holdout.yaml", attack_source="legal_overlay_holdout")
        )
    rows.extend(_load_bundled_attacks(bundled_profile, bundled_limit))
    return rows


def run_attacks(
    *,
    targets: dict[str, str],
    output_dir: Path,
    bundled_profile: str = "full",
    bundled_limit: int | None = 200,
    include_seeded_overlay: bool = True,
    include_holdout_overlay: bool = True,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    traffic = build_traffic_rows(
        bundled_profile=bundled_profile,
        bundled_limit=bundled_limit,
        include_seeded_overlay=include_seeded_overlay,
        include_holdout_overlay=include_holdout_overlay,
    )

    combined_log = output_dir / "atk_combined.jsonl"
    with httpx.Client() as client, combined_log.open("w", encoding="utf-8") as combined:
        for stack_id, base_url in targets.items():
            out_path = output_dir / f"{stack_id.lower()}.jsonl"
            with out_path.open("w", encoding="utf-8") as handle:
                for row in traffic:
                    payload = {
                        "text": row["text"],
                        "query_id": row.get("query_id"),
                        "traffic_kind": row.get("traffic_kind", "attack"),
                    }
                    try:
                        body = _post_target(client, base_url, payload)
                    except Exception as exc:
                        body = {
                            "stack_id": stack_id,
                            "decision": "gray",
                            "resolution_gate": "atk_error",
                            "error": str(exc),
                        }
                    record = {
                        "stack_id": stack_id,
                        "target": base_url,
                        "input_text": row["text"],
                        "expected_category": row.get("category_slug"),
                        "traffic_kind": row.get("traffic_kind", "attack"),
                        "attack_source": row.get("attack_source", ""),
                        "scenario_id": row.get("scenario_id"),
                        "source": row.get("source", ""),
                        **body,
                    }
                    handle.write(json.dumps(record) + "\n")
                    combined.write(json.dumps(record) + "\n")


def main() -> None:
    import os

    parser = argparse.ArgumentParser(description="Law benchmark attacker (ATK)")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/law/results/latest"))
    parser.add_argument("--bundled-profile", default="full", choices=["authored", "full"])
    parser.add_argument("--bundled-limit", type=int, default=200)
    parser.add_argument("--no-seeded-overlay", action="store_true")
    parser.add_argument("--no-holdout-overlay", action="store_true")
    args = parser.parse_args()

    targets = {key: os.environ.get(f"TARGET_{key}", url) for key, url in DEFAULT_TARGETS.items()}
    run_attacks(
        targets=targets,
        output_dir=args.output_dir,
        bundled_profile=args.bundled_profile,
        bundled_limit=args.bundled_limit,
        include_seeded_overlay=not args.no_seeded_overlay,
        include_holdout_overlay=not args.no_holdout_overlay,
    )
    from benchmark.law.compare_law import compare_law, write_comparison_report

    comparison = compare_law(args.output_dir, domain="law")
    comparison["harness"] = {
        "mode": "docker_http",
        "latency_primary_field": "request_latency_ms",
    }
    write_comparison_report(args.output_dir, comparison)


if __name__ == "__main__":
    main()
