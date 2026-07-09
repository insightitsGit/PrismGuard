"""Import-time salience filters for seed ingest (skip low-value / duplicate benign rows)."""

from __future__ import annotations

import re

from prismguard.seed.normalize import normalize_seed_text
from prismguard.storage.protocols import StorageBackend
from prismguard.storage.types import SeedEntryRecord

_MIN_TOKENS = 3


def _token_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def existing_benign_normalized_texts(
    storage: StorageBackend,
    *,
    exclude_entry_id: str | None = None,
) -> set[str]:
    texts: set[str] = set()
    for category in storage.relational.list_categories():
        if category.is_attack_category:
            continue
        for entry in storage.vector.list_seed_entries_by_category(category.slug):
            if exclude_entry_id and entry.id == exclude_entry_id:
                continue
            chunk = entry.chunk_text or entry.raw_text
            if chunk:
                texts.add(normalize_seed_text(chunk))
    return texts


def should_skip_benign_ingest(
    entry: SeedEntryRecord,
    *,
    existing_benign: set[str],
    near_duplicate_threshold: float = 0.98,
) -> bool:
    """Skip near-duplicate benign rows before expensive embed (text-normalized gate)."""
    if entry.category_slug != "benign_adjacent":
        return False
    text = normalize_seed_text(entry.chunk_text or entry.raw_text)
    if not text:
        return True
    if _token_count(text) < _MIN_TOKENS:
        return True
    if text in existing_benign:
        return True
    # Lightweight near-dup: one text is a substring of another normalized benign row.
    for existing in existing_benign:
        if len(text) >= 20 and len(existing) >= 20:
            shorter, longer = (text, existing) if len(text) < len(existing) else (existing, text)
            if shorter in longer and len(shorter) / len(longer) >= near_duplicate_threshold:
                return True
    return False
