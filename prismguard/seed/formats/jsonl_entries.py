from __future__ import annotations

import json
from pathlib import Path

from prismguard.seed.models import EntrySeed, ParsedSeed


def parse_jsonl_entries(path: Path) -> ParsedSeed:
    entries: list[EntrySeed] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or "text" not in item or "category_slug" not in item:
                raise ValueError(f"Invalid JSONL row {line_no} in {path}")
            entries.append(
                EntrySeed(
                    text=str(item["text"]),
                    category_slug=str(item["category_slug"]),
                    severity=str(item.get("severity", "medium")),  # type: ignore[arg-type]
                    source=str(item.get("source", "jsonl-import")),
                    rule_id=str(item["rule_id"]) if item.get("rule_id") else None,
                    notes=str(item["notes"]) if item.get("notes") else None,
                )
            )
    return ParsedSeed(entries=entries)
