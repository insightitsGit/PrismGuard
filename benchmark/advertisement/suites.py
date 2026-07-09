from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from benchmark.domain.run_domain_benchmark import build_domain_traffic_rows
from benchmark.law.atk.attack_runner import build_traffic_rows, _load_attack_overlay
from benchmark.law.shared.cases import load_queries
from benchmark.law.shared.normal_holdout import load_normal_holdout_scenarios
from benchmark.law.shared.normal_scenarios import load_normal_scenarios

_DATA_DIR = Path(__file__).resolve().parents[1] / "law" / "data"


@dataclass(frozen=True)
class BenchmarkSuite:
    suite_id: str
    title: str
    description: str
    domain: str
    advertisement_use: str  # headline | supporting | diagnostic
    build_traffic: Callable[..., list[dict]]


def _attack_holdout_only(**_: object) -> list[dict]:
    return _load_attack_overlay(_DATA_DIR / "legal_attacks_holdout.yaml", attack_source="legal_overlay_holdout")


def _attack_seeded_only(**_: object) -> list[dict]:
    return _load_attack_overlay(_DATA_DIR / "legal_attacks.yaml", attack_source="legal_overlay_seeded")


def _normal_dev_only(**_: object) -> list[dict]:
    return [
        {
            "text": s.text,
            "scenario_id": s.scenario_id,
            "category_slug": s.category_hint,
            "traffic_kind": "normal",
            "attack_source": "normal_scenario_dev",
        }
        for s in load_normal_scenarios()
    ]


def _normal_holdout_only(**_: object) -> list[dict]:
    return [
        {
            "text": s.text,
            "scenario_id": s.scenario_id,
            "category_slug": s.category_hint,
            "traffic_kind": "normal_holdout",
            "attack_source": "normal_holdout",
            "style": s.style,
        }
        for s in load_normal_holdout_scenarios()
    ]


def _law_kb_benign_only(**_: object) -> list[dict]:
    return [
        {
            "text": q.text,
            "query_id": q.query_id,
            "category_slug": q.category_slug,
            "traffic_kind": "benign",
            "attack_source": "law-queries",
        }
        for q in load_queries()
    ]


def _law_full_benchmark(*, bundled_limit: int = 100, **_: object) -> list[dict]:
    rows = build_traffic_rows(
        bundled_profile="full",
        bundled_limit=bundled_limit,
        include_seeded_overlay=True,
        include_holdout_overlay=True,
    )
    rows.extend(
        {
            "text": s.text,
            "scenario_id": s.scenario_id,
            "category_slug": s.category_hint,
            "traffic_kind": "normal_holdout",
            "attack_source": "normal_holdout",
            "style": s.style,
        }
        for s in load_normal_holdout_scenarios()
    )
    for row in rows:
        if row.get("traffic_kind") == "normal" and row.get("attack_source") == "normal_scenario":
            row["attack_source"] = "normal_scenario_dev"
    return rows


def _domain_full(domain: str) -> Callable[..., list[dict]]:
    def _builder(*, bundled_limit: int = 100, **_: object) -> list[dict]:
        return build_domain_traffic_rows(domain=domain, bundled_limit=bundled_limit)

    return _builder


ADVERTISEMENT_SUITES: tuple[BenchmarkSuite, ...] = (
    BenchmarkSuite(
        suite_id="attack-holdout",
        title="Attack holdout (cold)",
        description="14 held-out attack prompts never imported into seed stores.",
        domain="law",
        advertisement_use="headline",
        build_traffic=_attack_holdout_only,
    ),
    BenchmarkSuite(
        suite_id="attack-seeded",
        title="Attack seeded overlay",
        description="Seeded overlay attacks (in-corpus); diagnostic only, not for cold detection claims.",
        domain="law",
        advertisement_use="diagnostic",
        build_traffic=_attack_seeded_only,
    ),
    BenchmarkSuite(
        suite_id="normal-dev",
        title="Normal scenarios (development set)",
        description="35 benign prompts used in threshold tuning and training — not a cold FP metric.",
        domain="law",
        advertisement_use="diagnostic",
        build_traffic=_normal_dev_only,
    ),
    BenchmarkSuite(
        suite_id="normal-holdout",
        title="Normal holdout (cold)",
        description="20 cold benign prompts never used in tune/train/calibrate — cite for FP generalization.",
        domain="law",
        advertisement_use="headline",
        build_traffic=_normal_holdout_only,
    ),
    BenchmarkSuite(
        suite_id="law-kb-benign",
        title="Law KB benign queries",
        description="18 in-domain RAG benign queries from the law assistant benchmark.",
        domain="law",
        advertisement_use="supporting",
        build_traffic=_law_kb_benign_only,
    ),
    BenchmarkSuite(
        suite_id="law-full",
        title="Law full benchmark",
        description="Combined law traffic: KB benign, normal dev, normal holdout, overlays, bundled attacks.",
        domain="law",
        advertisement_use="supporting",
        build_traffic=_law_full_benchmark,
    ),
    BenchmarkSuite(
        suite_id="healthcare-domain",
        title="Healthcare domain pack",
        description="Healthcare overlay + holdout with law-derived bundled traffic.",
        domain="healthcare",
        advertisement_use="supporting",
        build_traffic=_domain_full("healthcare"),
    ),
    BenchmarkSuite(
        suite_id="finance-domain",
        title="Finance domain pack",
        description="Finance overlay + holdout with law-derived bundled traffic.",
        domain="finance",
        advertisement_use="supporting",
        build_traffic=_domain_full("finance"),
    ),
)


def suite_by_id(suite_id: str) -> BenchmarkSuite:
    for suite in ADVERTISEMENT_SUITES:
        if suite.suite_id == suite_id:
            return suite
    known = ", ".join(s.suite_id for s in ADVERTISEMENT_SUITES)
    raise KeyError(f"Unknown suite {suite_id!r}; known: {known}")


def list_suite_ids() -> list[str]:
    return [s.suite_id for s in ADVERTISEMENT_SUITES]
