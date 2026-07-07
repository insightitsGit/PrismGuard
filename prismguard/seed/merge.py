from __future__ import annotations

from prismguard.seed.models import CategorySeed, EntrySeed, ParsedSeed, RuleSeed


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

            key = seed_content_hash(entry.category_slug, entry.text)
            entries[key] = entry

    return ParsedSeed(
        categories=list(categories.values()),
        rules=list(rules.values()),
        entries=list(entries.values()),
        source_files=list(dict.fromkeys(source_files)),
    )
