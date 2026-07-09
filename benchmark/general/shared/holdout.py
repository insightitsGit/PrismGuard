from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class HoldoutScenario:
    scenario_id: str
    text: str
    category_hint: str
    style: str = ""


def _load_yaml(path: Path) -> list[HoldoutScenario]:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        HoldoutScenario(
            scenario_id=row["id"],
            text=row["text"],
            category_hint=row.get("category_hint", ""),
            style=row.get("style", ""),
        )
        for row in raw.get("scenarios", [])
    ]


def load_benign_holdout() -> list[HoldoutScenario]:
    return _load_yaml(_DATA_DIR / "benign_holdout.yaml")


def load_attack_holdout() -> list[HoldoutScenario]:
    return _load_yaml(_DATA_DIR / "attack_holdout.yaml")
