from __future__ import annotations

import csv
from pathlib import Path

from prismguard.seed.models import EntrySeed, ParsedSeed


def parse_csv_entries(path: Path) -> ParsedSeed:
    entries: list[EntrySeed] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "text" not in reader.fieldnames or "category_slug" not in reader.fieldnames:
            raise ValueError(f"CSV must include text and category_slug columns: {path}")
        for row in reader:
            if not row.get("text") or not row.get("category_slug"):
                continue
            entries.append(
                EntrySeed(
                    text=row["text"].strip(),
                    category_slug=row["category_slug"].strip(),
                    severity=(row.get("severity") or "medium").strip(),  # type: ignore[arg-type]
                    source=(row.get("source") or "csv-import").strip(),
                    rule_id=row.get("rule_id") or None,
                    notes=row.get("notes") or None,
                )
            )
    return ParsedSeed(entries=entries)
