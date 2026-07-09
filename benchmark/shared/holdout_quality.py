"""Holdout set quality rules — phrasing diversity enforced by CI, not honor system."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PHRASING_STYLES = frozenset({"short_fragment", "full_question"})
PHRASING_REGISTERS = frozenset({"formal", "casual"})
QUADRANT_KEYS = (
    "short_fragment/formal",
    "short_fragment/casual",
    "full_question/formal",
    "full_question/casual",
)

_CASUAL_MARKERS = (
    "i'm ",
    "i am ",
    "can you ",
    "help me ",
    "hey ",
    "quick q",
    "need help",
    "gonna ",
    "what's ",
    "don't ",
    "so if ",
    " — ",
    "plain english",
    "for my ",
)


def infer_style(text: str, style: str = "") -> str:
    if style in PHRASING_STYLES:
        return style
    stripped = text.strip()
    if len(stripped) < 72 and "?" not in stripped:
        return "short_fragment"
    return "full_question"


def infer_register(text: str, register: str = "") -> str:
    if register in PHRASING_REGISTERS:
        return register
    lowered = text.lower()
    if any(marker in lowered for marker in _CASUAL_MARKERS):
        return "casual"
    return "formal"


def quadrant_key(*, style: str, register: str) -> str:
    return f"{style}/{register}"


@dataclass(frozen=True)
class PhrasingDiversityReport:
    total: int
    counts: dict[str, int] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)
    min_per_quadrant: int = 4

    @property
    def passes(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, Any]:
        return {
            "passes": self.passes,
            "total": self.total,
            "counts": self.counts,
            "min_per_quadrant": self.min_per_quadrant,
            "violations": self.violations,
        }


def verify_phrasing_diversity(
    rows: list[dict[str, Any]],
    *,
    min_per_quadrant: int = 4,
    min_total_for_rule: int = 20,
    id_key: str = "id",
    text_key: str = "text",
) -> PhrasingDiversityReport:
    """Require short/long × formal/casual coverage so holdout cannot be gamed by length."""
    counts = {key: 0 for key in QUADRANT_KEYS}
    for row in rows:
        text = str(row.get(text_key, "") or "")
        if not text:
            continue
        style = infer_style(text, str(row.get("style", "") or ""))
        register = infer_register(text, str(row.get("register", "") or ""))
        counts[quadrant_key(style=style, register=register)] += 1

    violations: list[str] = []
    total = sum(counts.values())
    if total < min_total_for_rule:
        violations.append(
            f"holdout has only {total} rows; need at least {min_total_for_rule} before phrasing rule applies"
        )
        return PhrasingDiversityReport(
            total=total,
            counts=counts,
            violations=violations,
            min_per_quadrant=min_per_quadrant,
        )

    for key in QUADRANT_KEYS:
        if counts[key] < min_per_quadrant:
            violations.append(f"{key}: {counts[key]} < required {min_per_quadrant}")

    return PhrasingDiversityReport(
        total=total,
        counts=counts,
        violations=violations,
        min_per_quadrant=min_per_quadrant,
    )


def load_yaml_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not raw:
        return []
    if "scenarios" in raw:
        return list(raw["scenarios"])
    if "entries" in raw:
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(raw["entries"], start=1):
            item = dict(row)
            item.setdefault("id", item.get("id") or f"entry-{index}")
            item.setdefault("text", "")
            item.setdefault("style", "")
            item.setdefault("register", "")
            rows.append(item)
        return rows
    return []


def verify_law_holdout_phrasing() -> dict[str, PhrasingDiversityReport]:
    data_dir = Path(__file__).resolve().parents[1] / "law" / "data"
    attack_rows = [
        row
        for row in load_yaml_rows(data_dir / "legal_attacks_holdout.yaml")
        if row.get("category_slug") != "benign_adjacent"
    ]
    return {
        "normal_holdout": verify_phrasing_diversity(
            load_yaml_rows(data_dir / "normal_scenarios_holdout.yaml"),
            min_per_quadrant=4,
            min_total_for_rule=20,
        ),
        "attack_holdout": verify_phrasing_diversity(
            attack_rows,
            min_per_quadrant=2,
            min_total_for_rule=10,
        ),
    }
