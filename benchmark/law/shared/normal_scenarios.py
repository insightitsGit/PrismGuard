from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "normal_scenarios.yaml"


@dataclass(frozen=True)
class NormalScenario:
    scenario_id: str
    text: str
    category_hint: str


def load_normal_scenarios() -> list[NormalScenario]:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        NormalScenario(
            scenario_id=row["id"],
            text=row["text"],
            category_hint=row.get("category_hint", ""),
        )
        for row in raw.get("scenarios", [])
    ]
