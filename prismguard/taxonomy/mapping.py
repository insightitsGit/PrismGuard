from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from prismguard.seed.models import ParsedSeed
from prismguard.storage.protocols import StorageBackend
from prismguard.storage.types import RuleRecord

try:
    from prismrag_patch.core import PrismRAGPatch
    from prismrag_patch.mapping.rules import RulesStrategy
    from prismrag_patch.models import MappingConfig

    _HAS_PRISMRAG = True
except ImportError:  # pragma: no cover
    PrismRAGPatch = None  # type: ignore[misc, assignment]
    RulesStrategy = None  # type: ignore[misc, assignment]
    MappingConfig = None  # type: ignore[misc, assignment]
    _HAS_PRISMRAG = False


@dataclass
class TaxonomyEngine:
    """prismRAG RulesStrategy + Tier-1 regex rules for deterministic pre-LLM detection."""

    patch: object
    strategy: object
    mapping_dict: dict[str, Any]
    regex_rules: list[RuleRecord] = field(default_factory=list)
    bridges: dict[str, list[str]] = field(default_factory=dict)
    attack_categories: set[str] = field(default_factory=set)
    benign_category: str = "benign_adjacent"
    _substring_rules: list[tuple[str, str]] = field(default_factory=list)

    def assign_category(self, text: str) -> str | None:
        slug = self.strategy.infer_category_from_text(text)  # type: ignore[union-attr]
        if slug:
            return slug
        lower = text.lower()
        scores: dict[str, int] = {}
        for word, cat in self._substring_rules:
            if word in lower:
                scores[cat] = scores.get(cat, 0) + 1
        if not scores:
            return None
        return max(scores, key=lambda s: scores[s])

    def remap_category_vector(self, text: str, semantic_vector: list[float]) -> list[float]:
        return self.patch.remap_vector(semantic_vector, text)  # type: ignore[union-attr]

    def match_tier1(self, text: str) -> RuleRecord | None:
        for rule in self.regex_rules:
            if rule.pattern_type != "regex":
                if rule.pattern.lower() in text.lower():
                    return rule
                continue
            try:
                if re.search(rule.pattern, text, re.IGNORECASE):
                    return rule
            except re.error:
                continue
        return None

    def bridge_neighbors(self, slug: str) -> list[str]:
        return list(self.bridges.get(slug, []))


def _rules_to_keyword_pairs(rules: list[RuleRecord]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(word: str, slug: str) -> None:
        key = (word.lower().strip(), slug)
        if word and key not in seen:
            seen.add(key)
            pairs.append(key)

    for rule in rules:
        if rule.pattern_type == "keyword":
            for token in rule.pattern.lower().split():
                add(token, rule.category_slug)
        else:
            for token in re.findall(r"[a-zA-Z]{4,}", rule.pattern):
                add(token, rule.category_slug)
    return pairs


def _keyword_rules_from_seed(parsed: ParsedSeed) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(word: str, slug: str) -> None:
        key = (word.lower().strip(), slug)
        if word and key not in seen:
            seen.add(key)
            pairs.append(key)

    for rule in parsed.rules:
        if rule.pattern_type == "keyword":
            for token in rule.pattern.lower().split():
                add(token, rule.category_slug)
        else:
            for token in re.findall(r"[a-zA-Z]{4,}", rule.pattern):
                add(token, rule.category_slug)
    return pairs


def _mapping_dict_from_seed(parsed: ParsedSeed) -> dict[str, Any]:
    keyword_pairs = _keyword_rules_from_seed(parsed)
    return {
        "categories": [
            {"slug": c.slug, "label": c.label}
            for c in parsed.categories
        ],
        "rules": [
            {"word": word, "category_slug": slug, "weight": 1.0}
            for word, slug in keyword_pairs
        ],
    }


def build_mapping_after_import(storage: StorageBackend, parsed: ParsedSeed) -> TaxonomyEngine:
    """Build taxonomy from persisted storage (authoritative) with bridges from parsed seed."""
    if not _HAS_PRISMRAG:
        raise ImportError("prismrag-patch is required for taxonomy — pip install prismguard[prism]")

    categories = storage.relational.list_categories()
    rules = storage.relational.list_rules()
    parsed_bridges = {c.slug: list(c.bridges_to) for c in parsed.categories}
    keyword_pairs = _rules_to_keyword_pairs(rules)

    mapping_dict: dict[str, Any] = {
        "categories": [{"slug": c.slug, "label": c.label} for c in categories],
        "rules": [
            {"word": word, "category_slug": slug, "weight": 1.0}
            for word, slug in keyword_pairs
        ],
    }
    patch = PrismRAGPatch(mapping=mapping_dict, blend_alpha=0.35)
    strategy = RulesStrategy(MappingConfig.from_dict(mapping_dict))

    bridges = {c.slug: parsed_bridges.get(c.slug, []) for c in categories}
    attack = {c.slug for c in categories if c.is_attack_category}
    substring_rules = [(word, slug) for word, slug in keyword_pairs if len(word) >= 5]

    return TaxonomyEngine(
        patch=patch,
        strategy=strategy,
        mapping_dict=mapping_dict,
        regex_rules=rules,
        bridges=bridges,
        attack_categories=attack,
        _substring_rules=substring_rules,
    )


def build_mapping_from_parsed_seed(parsed: ParsedSeed) -> TaxonomyEngine:
    if not _HAS_PRISMRAG:
        raise ImportError("prismrag-patch is required for taxonomy — pip install prismguard[prism]")

    mapping_dict = _mapping_dict_from_seed(parsed)
    patch = PrismRAGPatch(mapping=mapping_dict, blend_alpha=0.35)
    strategy = RulesStrategy(MappingConfig.from_dict(mapping_dict))

    bridges: dict[str, list[str]] = {}
    attack: set[str] = set()
    for category in parsed.categories:
        bridges[category.slug] = list(category.bridges_to)
        if category.is_attack_category:
            attack.add(category.slug)

    substring_rules = [(word, slug) for word, slug in _keyword_rules_from_seed(parsed) if len(word) >= 5]

    return TaxonomyEngine(
        patch=patch,
        strategy=strategy,
        mapping_dict=mapping_dict,
        regex_rules=[
            RuleRecord(
                rule_id=r.rule_id,
                pattern=r.pattern,
                pattern_type=r.pattern_type,
                category_slug=r.category_slug,
                severity=r.severity,
                rationale=r.rationale,
                created_by=r.created_by,
            )
            for r in parsed.rules
        ],
        bridges=bridges,
        attack_categories=attack,
        _substring_rules=substring_rules,
    )


def build_mapping_from_storage(storage: StorageBackend) -> TaxonomyEngine:
    if not _HAS_PRISMRAG:
        raise ImportError("prismrag-patch is required for taxonomy — pip install prismguard[prism]")

    categories = storage.relational.list_categories()
    rules = storage.relational.list_rules()
    mapping_dict: dict[str, Any] = {
        "categories": [{"slug": c.slug, "label": c.label} for c in categories],
        "rules": [
            {"word": r.pattern, "category_slug": r.category_slug, "weight": 1.0}
            for r in rules
            if r.pattern_type == "keyword"
        ],
    }
    patch = PrismRAGPatch(mapping=mapping_dict, blend_alpha=0.35)
    strategy = RulesStrategy(MappingConfig.from_dict(mapping_dict))
    attack = {c.slug for c in categories if c.is_attack_category}
    return TaxonomyEngine(
        patch=patch,
        strategy=strategy,
        mapping_dict=mapping_dict,
        regex_rules=rules,
        bridges={},
        attack_categories=attack,
        _substring_rules=[(r.pattern, r.category_slug) for r in rules if r.pattern_type == "keyword"],
    )
