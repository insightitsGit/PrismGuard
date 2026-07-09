from __future__ import annotations

from typing import Protocol, runtime_checkable

from prismguard.storage.types import (
    CategoryRecord,
    ImportLogRecord,
    RuleRecord,
    SeedEntryRecord,
    VectorSearchResult,
)


@runtime_checkable
class VectorStore(Protocol):
    """ANN + seed corpus persistence. Backend-agnostic — no pgvector types leak here."""

    def upsert_seed_entry(self, entry: SeedEntryRecord) -> None: ...

    def delete_seed_entries_by_category(self, category_slug: str) -> int: ...

    def truncate_seed_entries(self) -> int: ...

    def get_seed_entry(self, entry_id: str) -> SeedEntryRecord | None: ...

    def list_seed_entries_by_category(self, category_slug: str) -> list[SeedEntryRecord]: ...

    def ann_search_semantic(
        self,
        vector: list[float],
        *,
        category_slugs: list[str] | None = None,
        top_k: int = 10,
    ) -> list[VectorSearchResult]: ...

    def ann_search_category(
        self,
        vector: list[float],
        *,
        category_slugs: list[str] | None = None,
        top_k: int = 10,
    ) -> list[VectorSearchResult]: ...


@runtime_checkable
class RelationalStore(Protocol):
    """Taxonomy, rules, and audit tables — may share a DB with VectorStore or use SQLite."""

    def upsert_category(self, category: CategoryRecord) -> None: ...

    def get_category(self, slug: str) -> CategoryRecord | None: ...

    def list_categories(self) -> list[CategoryRecord]: ...

    def upsert_rule(self, rule: RuleRecord) -> None: ...

    def list_rules(self) -> list[RuleRecord]: ...

    def append_import_log(self, record: ImportLogRecord) -> None: ...


@runtime_checkable
class StorageBackend(Protocol):
    """Unified storage facade selected at deploy time (pgvector, chroma, pinecone, weaviate, memory)."""

    @property
    def backend_name(self) -> str: ...

    @property
    def vector(self) -> VectorStore: ...

    @property
    def relational(self) -> RelationalStore: ...

    def healthcheck(self) -> bool: ...

    def close(self) -> None: ...
