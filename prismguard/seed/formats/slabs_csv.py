from __future__ import annotations

import csv
from pathlib import Path

from prismguard.seed.models import EntrySeed, ParsedSeed

_BENIGN = "benign_adjacent"
_STAGING = "unclassified_imported"


def parse_slabs_csv(path: Path) -> ParsedSeed:
    """S-Labs/prompt-injection-dataset: columns text,label (0=benign, 1=injection)."""
    entries: list[EntrySeed] = []
    source = f"s-labs-{path.stem}"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "text" not in reader.fieldnames or "label" not in reader.fieldnames:
            raise ValueError(f"S-Labs CSV must have text,label columns: {path}")
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            label = (row.get("label") or "").strip()
            if label == "0":
                category_slug = _BENIGN
                severity = "low"
            else:
                category_slug = _STAGING
                severity = "medium"
            entries.append(
                EntrySeed(
                    text=text,
                    category_slug=category_slug,
                    severity=severity,  # type: ignore[arg-type]
                    source=source,
                )
            )
    return ParsedSeed(entries=entries)
