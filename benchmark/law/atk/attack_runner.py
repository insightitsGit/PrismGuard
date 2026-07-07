from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
import yaml

from benchmark.law.shared.cases import load_queries

DEFAULT_TARGETS = {
    "CPL": "http://cpl:8080",
    "CRL": "http://crl:8080",
    "LNL": "http://lnl:8080",
    "LPL": "http://lpl:8080",
}


def _load_attack_overlay(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return list(raw.get("entries", []))


def _load_bundled_attacks(profile: str, limit: int | None) -> list[dict]:
    from prismguard.seed import load_bundled_seed

    parsed = load_bundled_seed(profile=profile)  # type: ignore[arg-type]
    rows = [
        {
            "text": entry.canonical_text(),
            "category_slug": entry.category_slug,
            "source": entry.source,
            "traffic_kind": "attack" if entry.category_slug != "benign_adjacent" else "benign_adjacent",
        }
        for entry in parsed.entries
    ]
    if limit is not None:
        return rows[:limit]
    return rows


def _post_target(client: httpx.Client, base_url: str, payload: dict) -> dict:
    start = time.perf_counter()
    response = client.post(f"{base_url}/query", json=payload, timeout=120.0)
    response.raise_for_status()
    body = response.json()
    body["request_latency_ms"] = (time.perf_counter() - start) * 1000
    return body


def run_attacks(
    *,
    targets: dict[str, str],
    output_dir: Path,
    bundled_profile: str = "authored",
    bundled_limit: int | None = 200,
    include_overlay: bool = True,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = Path(__file__).resolve().parents[1] / "data" / "legal_attacks.yaml"
    attacks: list[dict] = []
    if include_overlay:
        for row in _load_attack_overlay(overlay_path):
            attacks.append(
                {
                    **row,
                    "traffic_kind": "attack"
                    if row.get("category_slug") != "benign_adjacent"
                    else "benign_adjacent",
                }
            )
    attacks.extend(_load_bundled_attacks(bundled_profile, bundled_limit))

    queries = load_queries()
    benign_tasks = [
        {
            "text": q.text,
            "query_id": q.query_id,
            "category_slug": q.category_slug,
            "traffic_kind": "benign",
            "source": "law-queries",
        }
        for q in queries
    ]

    combined_log = output_dir / "atk_combined.jsonl"
    with httpx.Client() as client, combined_log.open("w", encoding="utf-8") as combined:
        for stack_id, base_url in targets.items():
            out_path = output_dir / f"{stack_id.lower()}.jsonl"
            with out_path.open("w", encoding="utf-8") as handle:
                for row in benign_tasks + attacks:
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
                        "source": row.get("source", ""),
                        **body,
                    }
                    handle.write(json.dumps(record) + "\n")
                    combined.write(json.dumps(record) + "\n")


def main() -> None:
    import os

    parser = argparse.ArgumentParser(description="Law benchmark attacker (ATK)")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/law/results/latest"))
    parser.add_argument("--bundled-profile", default="authored", choices=["authored", "full"])
    parser.add_argument("--bundled-limit", type=int, default=200)
    parser.add_argument("--no-overlay", action="store_true")
    args = parser.parse_args()

    targets = {key: os.environ.get(f"TARGET_{key}", url) for key, url in DEFAULT_TARGETS.items()}
    run_attacks(
        targets=targets,
        output_dir=args.output_dir,
        bundled_profile=args.bundled_profile,
        bundled_limit=args.bundled_limit,
        include_overlay=not args.no_overlay,
    )


if __name__ == "__main__":
    main()
