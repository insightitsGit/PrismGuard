from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from prismguard.storage.protocols import StorageBackend
from prismguard.storage.types import SeedEntryRecord
from prismguard.taxonomy.embedder import Embedder
from prismguard.taxonomy.constants import CATEGORY_VECTOR_DIM
from prismguard.taxonomy.mapping import TaxonomyEngine


@dataclass
class IngestReport:
    total_entries: int = 0
    embedded: int = 0
    skipped_already_embedded: int = 0
    empty_text_skipped: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        end = self.finished_at or datetime.now(UTC)
        return (end - self.started_at).total_seconds()


def iter_all_seed_entries(storage: StorageBackend):
    for category in storage.relational.list_categories():
        yield from storage.vector.list_seed_entries_by_category(category.slug)


def _vectors_complete(entry: SeedEntryRecord) -> bool:
    return bool(
        entry.embedding_semantic
        and entry.embedding_category
        and len(entry.embedding_category) == CATEGORY_VECTOR_DIM
    )


def ingest_seed_vectors(
    storage: StorageBackend,
    engine: TaxonomyEngine,
    embedder: Embedder,
    *,
    force: bool = False,
) -> IngestReport:
    """Dual-vector ingest: semantic 768-d + prismRAG category-grounded 256-d."""
    report = IngestReport()
    for entry in iter_all_seed_entries(storage):
        report.total_entries += 1
        text = entry.chunk_text or entry.raw_text
        if not text.strip():
            report.empty_text_skipped += 1
            continue
        if not force and _vectors_complete(entry):
            report.skipped_already_embedded += 1
            continue

        semantic = embedder.embed_semantic(text)
        slug = engine.assign_category(text) or entry.category_slug
        category_vec = engine.remap_category_vector(
            text, semantic, category_slug=slug
        )
        if len(category_vec) != CATEGORY_VECTOR_DIM:
            raise ValueError(
                f"category vector for entry {entry.id!r} has dim {len(category_vec)}, "
                f"expected {CATEGORY_VECTOR_DIM}"
            )

        updated = SeedEntryRecord(
            id=entry.id,
            raw_text=entry.raw_text,
            chunk_text=entry.chunk_text,
            embedding_semantic=semantic,
            embedding_category=category_vec,
            category_slug=entry.category_slug,
            severity=entry.severity,
            source=entry.source,
            reviewed_by=entry.reviewed_by,
            created_at=entry.created_at,
            updated_at=datetime.now(UTC),
        )
        storage.vector.upsert_seed_entry(updated)
        report.embedded += 1

    report.finished_at = datetime.now(UTC)
    return report
