from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from benchmark.law.shared.kb import DATA_DIR

Variant = Literal["exact_repeat", "paraphrase", "novel"]


@dataclass(frozen=True)
class LawQuery:
    query_id: str
    text: str
    category_slug: str
    must_cite: list[str]
    variant: Variant = "exact_repeat"


def load_queries(path: Path | None = None) -> list[LawQuery]:
    raw_path = path or DATA_DIR / "queries.yaml"
    with raw_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        LawQuery(
            query_id=item["query_id"],
            text=item["text"],
            category_slug=item["category_slug"],
            must_cite=list(item.get("must_cite", [])),
            variant=item.get("variant", "exact_repeat"),
        )
        for item in raw.get("queries", [])
    ]
