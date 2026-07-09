from __future__ import annotations

import re
from pathlib import Path

from prismguard.seed.models import CategorySeed, EntrySeed, ParsedSeed

_CATEGORY_HEADER = re.compile(r"^\*\*`([^`]+)`\*\*")
_SKIP_PREFIXES = ("detection signal:", "<!-- not-an-example -->")
_QUOTED_BULLET = re.compile(r'^-\s+"(.+)"\s*$')
_PLAIN_BULLET = re.compile(r"^-\s+(.+?)\s*$")


def _parse_categories_table(lines: list[str]) -> list[CategorySeed]:
    categories: list[CategorySeed] = []
    in_table = False
    for line in lines:
        if line.strip() == "### Categories":
            in_table = True
            continue
        if in_table and line.startswith("### "):
            break
        if not in_table or not line.strip().startswith("|"):
            continue
        if "`" not in line or "Slug" in line or line.strip().startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        slug = cells[0].strip("`")
        description = cells[1]
        bridges_raw = cells[2]
        bridges: list[str] = []
        if bridges_raw and "no bridges" not in bridges_raw.lower() and bridges_raw.strip() not in ("*(none)*", "—", "-"):
            bridges = [part.strip().strip("`") for part in bridges_raw.split(",") if part.strip()]
        categories.append(
            CategorySeed(
                slug=slug,
                label=slug.replace("_", " ").title(),
                description=description,
                is_attack_category=slug != "benign_adjacent",
                bridges_to=bridges,
            )
        )
    return categories


def _should_skip_example(line: str) -> bool:
    lowered = line.strip().lower()
    return any(lowered.startswith(prefix) for prefix in _SKIP_PREFIXES)


def _parse_seed_examples(lines: list[str]) -> list[EntrySeed]:
    entries: list[EntrySeed] = []
    current_slug: str | None = None
    in_examples = False
    for line in lines:
        if line.strip().startswith("### Seed examples"):
            in_examples = True
            continue
        if not in_examples:
            continue
        if line.startswith("---"):
            break
        if line.startswith("## Part ") and in_examples:
            break
        header = _CATEGORY_HEADER.match(line.strip())
        if header:
            current_slug = header.group(1)
            continue
        if current_slug is None or not line.strip().startswith("- "):
            continue
        if _should_skip_example(line):
            continue
        quoted = _QUOTED_BULLET.match(line.strip())
        if quoted:
            text = quoted.group(1)
        else:
            plain = _PLAIN_BULLET.match(line.strip())
            if not plain:
                continue
            text = plain.group(1)
        severity = "low" if current_slug == "benign_adjacent" else "high"
        entries.append(
            EntrySeed(
                text=text,
                category_slug=current_slug,
                severity=severity,
                source="markdown-seed",
            )
        )
    return entries


def parse_markdown_seed(path: Path) -> ParsedSeed:
    lines = path.read_text(encoding="utf-8").splitlines()
    categories = _parse_categories_table(lines)
    entries = _parse_seed_examples(lines)
    return ParsedSeed(categories=categories, entries=entries)
