from __future__ import annotations

import csv
from pathlib import Path

from prismguard.seed.models import EntrySeed, ParsedSeed

_STAGING = "unclassified_imported"


def parse_yanismiraoui_csv(path: Path) -> ParsedSeed:
    """yanismiraoui/prompt_injections: single-column multilingual attack prompts."""
    entries: list[EntrySeed] = []
    source = "yanismiraoui-prompt-injections"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return ParsedSeed(entries=[])
    start = 1 if rows[0] and rows[0][0].strip().lower() == "prompt_injections" else 0
    for row in rows[start:]:
        if not row:
            continue
        text = row[0].strip()
        if not text:
            continue
        entries.append(
            EntrySeed(
                text=text,
                category_slug=_STAGING,
                severity="medium",
                source=source,
            )
        )
    return ParsedSeed(entries=entries)
