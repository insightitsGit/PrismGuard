from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "normal_scenarios_holdout.yaml"


@dataclass(frozen=True)
class NormalHoldoutScenario:
    scenario_id: str
    text: str
    category_hint: str
    style: str = ""


def load_normal_holdout_scenarios() -> list[NormalHoldoutScenario]:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        NormalHoldoutScenario(
            scenario_id=row["id"],
            text=row["text"],
            category_hint=row.get("category_hint", ""),
            style=row.get("style", ""),
        )
        for row in raw.get("scenarios", [])
    ]
