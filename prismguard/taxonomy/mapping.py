from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from prismguard.storage.protocols import StorageBackend
from prismguard.storage.types import RuleRecord
from prismguard.taxonomy.constants import CATEGORY_VECTOR_DIM

if TYPE_CHECKING:
    from prismguard.seed.models import ParsedSeed

try:
    from prismrag_patch.config import EMBED_DIM_SEMANTIC
    from prismrag_patch.core import PrismRAGPatch
    from prismrag_patch.mapping.projection import project_sem_to_personal
    from prismrag_patch.mapping.rules import RulesStrategy
    from prismrag_patch.models import MappingConfig

    _HAS_PRISMRAG = True
except ImportError:  # pragma: no cover
    PrismRAGPatch = None  # type: ignore[misc, assignment]
    RulesStrategy = None  # type: ignore[misc, assignment]
    MappingConfig = None  # type: ignore[misc, assignment]
    project_sem_to_personal = None  # type: ignore[misc, assignment]
    EMBED_DIM_SEMANTIC = 768
    _HAS_PRISMRAG = False

log = logging.getLogger(__name__)

_PRISM_EXTRA_HINT = "prismrag-patch is required for full taxonomy — pip install prismguard[prism]"


def has_prismrag() -> bool:
    """True when the optional ``[prism]`` stack (prismrag-patch) is importable."""
    return _HAS_PRISMRAG


class _KeywordRulesStrategy:
    """Base-install category inference from keyword rules (no prismrag-patch)."""

    def __init__(self, mapping_dict: dict[str, Any]) -> None:
        self._word_to_slug: list[tuple[str, str]] = []
        for rule in mapping_dict.get("rules", []):
            word = str(rule.get("word", "")).lower().strip()
            slug = str(rule.get("category_slug", "")).strip()
            if word and slug:
                self._word_to_slug.append((word, slug))

    def infer_category_from_text(self, text: str) -> str | None:
        lower = text.lower()
        scores: dict[str, int] = {}
        for word, slug in self._word_to_slug:
            if len(word) < 4:
                continue
            if re.search(rf"\b{re.escape(word)}\b", lower):
                scores[slug] = scores.get(slug, 0) + 1
        if not scores:
            return None
        return max(scores, key=lambda s: scores[s])


class _RulesOnlyPatch:
    """Pools semantic vectors to category dim without prismrag remap."""

    def remap_vector(self, semantic_vector: list[float], text: str = "") -> list[float]:
        _ = text
        from prismguard.taxonomy.embedder import _pool_dims

        return _pool_dims(list(semantic_vector), CATEGORY_VECTOR_DIM)


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
    rules_only: bool = False

    def _substring_match_scores(self, text: str) -> dict[str, int]:
        lower = text.lower()
        scores: dict[str, int] = {}
        for word, cat in self._substring_rules:
            if re.search(rf"\b{re.escape(word)}\b", lower):
                scores[cat] = scores.get(cat, 0) + 1
        return scores

    def assign_category(self, text: str) -> str | None:
        slug = self.strategy.infer_category_from_text(text)  # type: ignore[union-attr]
        if slug:
            return slug
        scores = self._substring_match_scores(text)
        if not scores:
            return None
        return max(scores, key=lambda s: scores[s])

    def remap_category_vector(
        self,
        text: str,
        semantic_vector: list[float],
        *,
        category_slug: str | None = None,
    ) -> list[float]:
        result = self.patch.remap_vector(semantic_vector, text)  # type: ignore[union-attr]
        if len(result) == CATEGORY_VECTOR_DIM:
            return result

        slug = category_slug or self.assign_category(text)
        if slug:
            augmented = f"{text} {' '.join(slug.split('_'))}"
            result = self.patch.remap_vector(semantic_vector, augmented)  # type: ignore[union-attr]
            if len(result) == CATEGORY_VECTOR_DIM:
                return result

            if project_sem_to_personal is not None and len(semantic_vector) == EMBED_DIM_SEMANTIC:
                slugs = [c["slug"] for c in self.mapping_dict.get("categories", [])]
                if slug in slugs:
                    import numpy as np

                    projected = project_sem_to_personal(
                        np.asarray(semantic_vector, dtype=float),
                        slug,
                        slugs,
                    )
                    return [float(x) for x in projected]

        from prismguard.taxonomy.embedder import _pool_dims

        pooled = _pool_dims(semantic_vector, CATEGORY_VECTOR_DIM)
        log.debug(
            "category vector projection fallback for text=%r slug=%r dim=%d",
            text[:80],
            slug,
            len(pooled),
        )
        return pooled

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


def _engine_from_parts(
    *,
    mapping_dict: dict[str, Any],
    regex_rules: list[RuleRecord],
    bridges: dict[str, list[str]],
    attack_categories: set[str],
    substring_rules: list[tuple[str, str]],
) -> TaxonomyEngine:
    """Build a TaxonomyEngine; degrade to rules-only when prismrag-patch is absent."""
    if _HAS_PRISMRAG:
        patch = PrismRAGPatch(mapping=mapping_dict, blend_alpha=0.35)
        strategy = RulesStrategy(MappingConfig.from_dict(mapping_dict))
        rules_only = False
    else:
        log.info("prismrag-patch not installed — using rules-only taxonomy (%s)", _PRISM_EXTRA_HINT)
        patch = _RulesOnlyPatch()
        strategy = _KeywordRulesStrategy(mapping_dict)
        rules_only = True
    return TaxonomyEngine(
        patch=patch,
        strategy=strategy,
        mapping_dict=mapping_dict,
        regex_rules=regex_rules,
        bridges=bridges,
        attack_categories=attack_categories,
        _substring_rules=substring_rules,
        rules_only=rules_only,
    )


def build_mapping_after_import(storage: StorageBackend, parsed: ParsedSeed) -> TaxonomyEngine:
    """Build taxonomy from persisted storage (authoritative) with bridges from parsed seed."""
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
    bridges = {c.slug: parsed_bridges.get(c.slug, []) for c in categories}
    attack = {c.slug for c in categories if c.is_attack_category}
    substring_rules = [(word, slug) for word, slug in keyword_pairs if len(word) >= 5]
    return _engine_from_parts(
        mapping_dict=mapping_dict,
        regex_rules=rules,
        bridges=bridges,
        attack_categories=attack,
        substring_rules=substring_rules,
    )


def build_mapping_from_parsed_seed(parsed: ParsedSeed) -> TaxonomyEngine:
    mapping_dict = _mapping_dict_from_seed(parsed)
    bridges: dict[str, list[str]] = {}
    attack: set[str] = set()
    for category in parsed.categories:
        bridges[category.slug] = list(category.bridges_to)
        if category.is_attack_category:
            attack.add(category.slug)

    substring_rules = [(word, slug) for word, slug in _keyword_rules_from_seed(parsed) if len(word) >= 5]
    regex_rules = [
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
    ]
    return _engine_from_parts(
        mapping_dict=mapping_dict,
        regex_rules=regex_rules,
        bridges=bridges,
        attack_categories=attack,
        substring_rules=substring_rules,
    )


def build_mapping_from_storage(storage: StorageBackend) -> TaxonomyEngine:
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
    attack = {c.slug for c in categories if c.is_attack_category}
    return _engine_from_parts(
        mapping_dict=mapping_dict,
        regex_rules=rules,
        bridges={},
        attack_categories=attack,
        substring_rules=[(r.pattern, r.category_slug) for r in rules if r.pattern_type == "keyword"],
    )
