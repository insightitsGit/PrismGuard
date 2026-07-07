from __future__ import annotations

import logging

from prismguard.seed.models import CategorySeed, EntrySeed, ParsedSeed, RuleSeed

log = logging.getLogger(__name__)

_AUTHORED_SOURCE_MARKERS = ("seed-v0", "authored", "design-doc", "mined-slabs")


def _source_priority(entry: EntrySeed) -> int:
    source = entry.source.lower()
    if any(marker in source for marker in _AUTHORED_SOURCE_MARKERS):
        return 2
    if "authored" in entry.source_file.lower():
        return 2
    return 1


def _entry_metadata_differs(left: EntrySeed, right: EntrySeed) -> bool:
    return (
        left.severity != right.severity
        or left.source != right.source
        or (left.notes or "") != (right.notes or "")
    )


def merge_parsed_seeds(parts: list[ParsedSeed]) -> ParsedSeed:
    if not parts:
        return ParsedSeed()
    if len(parts) == 1:
        return parts[0]

    categories: dict[str, CategorySeed] = {}
    rules: dict[str, RuleSeed] = {}
    entries: dict[str, EntrySeed] = {}
    source_files: list[str] = []

    for part in parts:
        source_files.extend(part.source_files)
        for category in part.categories:
            existing = categories.get(category.slug)
            if existing is None:
                categories[category.slug] = category
            else:
                bridges = list(dict.fromkeys([*existing.bridges_to, *category.bridges_to]))
                categories[category.slug] = CategorySeed(
                    slug=category.slug,
                    label=category.label or existing.label,
                    description=category.description or existing.description,
                    is_attack_category=category.is_attack_category,
                    bridges_to=bridges,
                    source_file=category.source_file or existing.source_file,
                )
        for rule in part.rules:
            existing = rules.get(rule.rule_id)
            if existing is not None and (
                existing.pattern != rule.pattern
                or existing.category_slug != rule.category_slug
                or existing.pattern_type != rule.pattern_type
            ):
                raise ValueError(
                    f"Conflicting rule_id {rule.rule_id!r} across sources "
                    f"{existing.source_file!r} and {rule.source_file!r}"
                )
            rules[rule.rule_id] = rule
        for entry in part.entries:
            from prismguard.seed.normalize import seed_content_hash

            key = seed_content_hash(entry.category_slug, entry.canonical_text())
            existing_entry = entries.get(key)
            if existing_entry is None:
                entries[key] = entry
                continue
            if not _entry_metadata_differs(existing_entry, entry):
                continue

            existing_priority = _source_priority(existing_entry)
            incoming_priority = _source_priority(entry)
            if incoming_priority > existing_priority:
                log.warning(
                    "authored seed supersedes external duplicate hash=%s kept source=%r over %r",
                    key,
                    entry.source,
                    existing_entry.source,
                )
                entries[key] = entry
            elif incoming_priority < existing_priority:
                log.warning(
                    "authored seed kept over external duplicate hash=%s kept source=%r over %r",
                    key,
                    existing_entry.source,
                    entry.source,
                )
            else:
                log.warning(
                    "duplicate seed entry hash=%s later source=%r supersedes %r",
                    key,
                    entry.source,
                    existing_entry.source,
                )
                entries[key] = entry

    return ParsedSeed(
        categories=list(categories.values()),
        rules=list(rules.values()),
        entries=list(entries.values()),
        source_files=list(dict.fromkeys(source_files)),
    )
