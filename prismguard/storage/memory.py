from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

from prismguard.storage.protocols import RelationalStore, StorageBackend, VectorStore
from prismguard.storage.types import (
    CategoryRecord,
    ImportLogRecord,
    RuleRecord,
    SeedEntryRecord,
    VectorSearchResult,
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._entries: dict[str, SeedEntryRecord] = {}

    def upsert_seed_entry(self, entry: SeedEntryRecord) -> None:
        self._entries[entry.id] = entry

    def delete_seed_entries_by_category(self, category_slug: str) -> int:
        to_delete = [eid for eid, e in self._entries.items() if e.category_slug == category_slug]
        for eid in to_delete:
            del self._entries[eid]
        return len(to_delete)

    def truncate_seed_entries(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count

    def get_seed_entry(self, entry_id: str) -> SeedEntryRecord | None:
        return self._entries.get(entry_id)

    def list_seed_entries_by_category(self, category_slug: str) -> list[SeedEntryRecord]:
        return [e for e in self._entries.values() if e.category_slug == category_slug]

    def _ann_search(
        self,
        vector: list[float],
        *,
        field: str,
        category_slugs: list[str] | None,
        top_k: int,
    ) -> list[VectorSearchResult]:
        results: list[VectorSearchResult] = []
        for entry in self._entries.values():
            if category_slugs is not None and entry.category_slug not in category_slugs:
                continue
            emb = entry.embedding_semantic if field == "semantic" else entry.embedding_category
            score = _cosine_similarity(vector, emb)
            results.append(
                VectorSearchResult(
                    entry_id=entry.id,
                    score=score,
                    category_slug=entry.category_slug,
                    chunk_text=entry.chunk_text,
                    severity=entry.severity,
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def ann_search_semantic(
        self,
        vector: list[float],
        *,
        category_slugs: list[str] | None = None,
        top_k: int = 10,
    ) -> list[VectorSearchResult]:
        return self._ann_search(vector, field="semantic", category_slugs=category_slugs, top_k=top_k)

    def ann_search_category(
        self,
        vector: list[float],
        *,
        category_slugs: list[str] | None = None,
        top_k: int = 10,
    ) -> list[VectorSearchResult]:
        return self._ann_search(vector, field="category", category_slugs=category_slugs, top_k=top_k)


class InMemoryRelationalStore(RelationalStore):
    def __init__(self) -> None:
        self._categories: dict[str, CategoryRecord] = {}
        self._rules: dict[str, RuleRecord] = {}
        self._import_logs: list[ImportLogRecord] = []

    def upsert_category(self, category: CategoryRecord) -> None:
        self._categories[category.slug] = category

    def get_category(self, slug: str) -> CategoryRecord | None:
        return self._categories.get(slug)

    def list_categories(self) -> list[CategoryRecord]:
        return list(self._categories.values())

    def upsert_rule(self, rule: RuleRecord) -> None:
        self._rules[rule.rule_id] = rule

    def list_rules(self) -> list[RuleRecord]:
        return list(self._rules.values())

    def append_import_log(self, record: ImportLogRecord) -> None:
        self._import_logs.append(record)


class InMemoryStorageBackend(StorageBackend):
    """Reference in-process backend for unit tests and local dev without external DBs."""

    def __init__(self) -> None:
        self._vector = InMemoryVectorStore()
        self._relational = InMemoryRelationalStore()

    @property
    def backend_name(self) -> str:
        return "memory"

    @property
    def vector(self) -> VectorStore:
        return self._vector

    @property
    def relational(self) -> RelationalStore:
        return self._relational

    def healthcheck(self) -> bool:
        return True

    def close(self) -> None:
        return None


def new_seed_entry(
    *,
    raw_text: str,
    chunk_text: str,
    embedding_semantic: list[float],
    embedding_category: list[float],
    category_slug: str,
    severity: str = "medium",
    source: str = "test",
) -> SeedEntryRecord:
    now = datetime.now(UTC)
    return SeedEntryRecord(
        id=str(uuid4()),
        raw_text=raw_text,
        chunk_text=chunk_text,
        embedding_semantic=embedding_semantic,
        embedding_category=embedding_category,
        category_slug=category_slug,
        severity=severity,
        source=source,
        created_at=now,
        updated_at=now,
    )
