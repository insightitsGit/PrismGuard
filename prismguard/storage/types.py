from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SeedEntryRecord:
    id: str
    raw_text: str
    chunk_text: str
    embedding_semantic: list[float]
    embedding_category: list[float]
    category_slug: str
    severity: str
    source: str
    reviewed_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class VectorSearchResult:
    entry_id: str
    score: float
    category_slug: str
    chunk_text: str
    severity: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CategoryRecord:
    slug: str
    label: str
    description: str = ""
    is_attack_category: bool = True


@dataclass(frozen=True)
class RuleRecord:
    rule_id: str
    pattern: str
    pattern_type: str
    category_slug: str
    severity: str
    rationale: str = ""
    created_by: str = ""


@dataclass(frozen=True)
class ImportLogRecord:
    id: str
    source_filename: str
    mode: str
    scope: str
    inserted: int
    updated: int
    skipped: int
    errored: int
    created_at: datetime
