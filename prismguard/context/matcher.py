from __future__ import annotations

import re

from prismguard.context.models import EntityTerm, TenantLexicon

DEFAULT_OVERRIDE_TOKENS = frozenset(
    {
        "ignore",
        "bypass",
        "disregard",
        "override",
        "forget",
        "exception",
        "verbatim",
        "reveal",
        "disclose",
        "print",
        "quote",
        "leak",
        "without restriction",
        "no ethics",
        "developer mode",
        "do not refuse",
        "never mention policy",
    }
)


def normalize_term(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def compile_override_tokens(lexicon: TenantLexicon | None) -> frozenset[str]:
    tokens = set(DEFAULT_OVERRIDE_TOKENS)
    if lexicon is not None:
        tokens.update(normalize_term(t) for t in lexicon.override_tokens if t.strip())
    return frozenset(tokens)


def contains_override_language(text: str, *, override_tokens: frozenset[str]) -> bool:
    normalized = normalize_term(text)
    for token in override_tokens:
        if token in normalized:
            return True
    return False


def find_matching_entities(text: str, lexicon: TenantLexicon) -> list[tuple[str, EntityTerm]]:
    normalized = normalize_term(text)
    matches: list[tuple[str, EntityTerm]] = []
    seen: set[str] = set()
    for term, entity in lexicon.all_terms():
        key = normalize_term(term)
        if len(key) < 3 or key in seen:
            continue
        if key in normalized:
            matches.append((term, entity))
            seen.add(key)
    return matches


def tenant_tier1_block(
    text: str,
    lexicon: TenantLexicon | None,
    *,
    override_tokens: frozenset[str] | None = None,
) -> dict | None:
    """Block when restricted tenant entity co-occurs with override language."""
    if lexicon is None or not lexicon.entities:
        return None
    tokens = override_tokens or compile_override_tokens(lexicon)
    if not contains_override_language(text, override_tokens=tokens):
        return None
    matches = find_matching_entities(text, lexicon)
    restricted = [(term, ent) for term, ent in matches if ent.sensitivity == "restricted"]
    if not restricted:
        return None
    term, entity = restricted[0]
    return {
        "matched_term": term,
        "entity_type": entity.type,
        "sensitivity": entity.sensitivity,
        "override_detected": True,
    }


def tenant_severity_boost(
    text: str,
    lexicon: TenantLexicon | None,
    *,
    boost_restricted: float = 0.15,
    boost_internal: float = 0.08,
) -> float:
    if lexicon is None:
        return 0.0
    matches = find_matching_entities(text, lexicon)
    if not matches:
        return 0.0
    max_boost = 0.0
    for _, entity in matches:
        if entity.sensitivity == "restricted":
            max_boost = max(max_boost, boost_restricted)
        elif entity.sensitivity == "internal":
            max_boost = max(max_boost, boost_internal)
    return max_boost
