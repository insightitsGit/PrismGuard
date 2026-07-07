from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from prismguard.seed.models import CategorySeed, EntrySeed, ParsedSeed, RuleSeed


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"Expected list, got {type(value)!r}")


def parse_yaml_or_json_taxonomy(path: Path, raw: str | None = None) -> ParsedSeed:
    text = raw if raw is not None else path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Taxonomy file must be a mapping: {path}")

    categories: list[CategorySeed] = []
    for item in _as_list(data.get("categories")):
        if not isinstance(item, dict) or "slug" not in item:
            raise ValueError(f"Invalid category entry in {path}")
        categories.append(
            CategorySeed(
                slug=str(item["slug"]),
                label=str(item.get("label", item["slug"])),
                description=str(item.get("description", "")),
                is_attack_category=bool(item.get("is_attack_category", True)),
                bridges_to=[str(b) for b in _as_list(item.get("bridges_to"))],
            )
        )

    rules: list[RuleSeed] = []
    for item in _as_list(data.get("rules")):
        if not isinstance(item, dict) or "rule_id" not in item or "pattern" not in item:
            raise ValueError(f"Invalid rule entry in {path}")
        pattern_type = str(item.get("pattern_type", "regex"))
        if pattern_type not in ("regex", "keyword"):
            raise ValueError(f"Invalid pattern_type {pattern_type!r} in {path}")
        rules.append(
            RuleSeed(
                rule_id=str(item["rule_id"]),
                pattern=str(item["pattern"]),
                pattern_type=pattern_type,  # type: ignore[arg-type]
                category_slug=str(item["category_slug"]),
                severity=str(item.get("severity", "medium")),  # type: ignore[arg-type]
                rationale=str(item.get("rationale", "")),
                created_by=str(item.get("created_by", "")),
            )
        )

    entries: list[EntrySeed] = []
    for item in _as_list(data.get("entries")):
        if not isinstance(item, dict) or "category_slug" not in item:
            raise ValueError(f"Invalid entry in {path}")
        turns_raw = item.get("turns")
        turns = [str(t) for t in _as_list(turns_raw)] if turns_raw is not None else None
        if turns:
            text = str(item.get("text", ""))
        elif "text" in item:
            text = str(item["text"])
        else:
            raise ValueError(f"Entry requires text or turns in {path}")
        entries.append(
            EntrySeed(
                text=text,
                category_slug=str(item["category_slug"]),
                severity=str(item.get("severity", "medium")),  # type: ignore[arg-type]
                source=str(item.get("source", "yaml-import")),
                rule_id=str(item["rule_id"]) if item.get("rule_id") else None,
                notes=str(item["notes"]) if item.get("notes") else None,
                turns=turns,
                secondary_category_slugs=[
                    str(s) for s in _as_list(item.get("secondary_category_slugs"))
                ],
            )
        )

    return ParsedSeed(categories=categories, rules=rules, entries=entries)


def parse_json_taxonomy(path: Path) -> ParsedSeed:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return parse_yaml_or_json_taxonomy(path, raw=yaml.dump(data))
