from __future__ import annotations

from datetime import datetime
from typing import Any

from prismguard.storage.backends.pgvector_schema import qualified
from prismguard.storage.blobs import BlobStore, raw_text_sha256
from prismguard.storage.types import (
    CategoryRecord,
    ImportLogRecord,
    RuleRecord,
    SeedEntryRecord,
    VectorSearchResult,
)


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


class PgvectorRelationalStore:
    def __init__(self, conn, *, schema_prefix: str) -> None:
        self._conn = conn
        self._prefix = schema_prefix
        self._categories = qualified(schema_prefix, "categories")
        self._rules = qualified(schema_prefix, "rules")
        self._imports = qualified(schema_prefix, "import_logs")

    def upsert_category(self, category: CategoryRecord) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._categories} (slug, label, description, is_attack_category)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    label = EXCLUDED.label,
                    description = EXCLUDED.description,
                    is_attack_category = EXCLUDED.is_attack_category
                """,
                (category.slug, category.label, category.description, category.is_attack_category),
            )
        self._conn.commit()

    def get_category(self, slug: str) -> CategoryRecord | None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT slug, label, description, is_attack_category FROM {self._categories} WHERE slug = %s",
                (slug,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return CategoryRecord(slug=row[0], label=row[1], description=row[2], is_attack_category=row[3])

    def list_categories(self) -> list[CategoryRecord]:
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT slug, label, description, is_attack_category FROM {self._categories} ORDER BY slug"
            )
            rows = cur.fetchall()
        return [
            CategoryRecord(slug=r[0], label=r[1], description=r[2], is_attack_category=r[3]) for r in rows
        ]

    def upsert_rule(self, rule: RuleRecord) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._rules}
                    (rule_id, pattern, pattern_type, category_slug, severity, rationale, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (rule_id) DO UPDATE SET
                    pattern = EXCLUDED.pattern,
                    pattern_type = EXCLUDED.pattern_type,
                    category_slug = EXCLUDED.category_slug,
                    severity = EXCLUDED.severity,
                    rationale = EXCLUDED.rationale,
                    created_by = EXCLUDED.created_by
                """,
                (
                    rule.rule_id,
                    rule.pattern,
                    rule.pattern_type,
                    rule.category_slug,
                    rule.severity,
                    rule.rationale,
                    rule.created_by,
                ),
            )
        self._conn.commit()

    def list_rules(self) -> list[RuleRecord]:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT rule_id, pattern, pattern_type, category_slug, severity, rationale, created_by
                FROM {self._rules} ORDER BY rule_id
                """
            )
            rows = cur.fetchall()
        return [
            RuleRecord(
                rule_id=r[0],
                pattern=r[1],
                pattern_type=r[2],
                category_slug=r[3],
                severity=r[4],
                rationale=r[5],
                created_by=r[6],
            )
            for r in rows
        ]

    def append_import_log(self, record: ImportLogRecord) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._imports}
                    (id, source_filename, mode, scope, inserted, updated, skipped, errored, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.id,
                    record.source_filename,
                    record.mode,
                    record.scope,
                    record.inserted,
                    record.updated,
                    record.skipped,
                    record.errored,
                    record.created_at,
                ),
            )
        self._conn.commit()


class PgvectorVectorStore:
    def __init__(self, conn, *, schema_prefix: str, blob_store: BlobStore | None = None) -> None:
        self._conn = conn
        self._prefix = schema_prefix
        self._seeds = qualified(schema_prefix, "seed_entries")
        self._blob_store = blob_store

    def upsert_seed_entry(self, entry: SeedEntryRecord) -> None:
        sem = vector_literal(entry.embedding_semantic)
        cat = vector_literal(entry.embedding_category)
        raw_sha = entry.raw_text_sha256 or (
            raw_text_sha256(entry.raw_text) if entry.raw_text else ""
        )
        if self._blob_store is not None and entry.raw_text:
            raw_sha = self._blob_store.put_raw_text(entry.raw_text)
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._seeds} (
                    id, raw_text, chunk_text, embedding_semantic, embedding_category,
                    category_slug, severity, source, reviewed_by,
                    content_hash, raw_text_sha256, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s::vector, %s::vector,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    raw_text = EXCLUDED.raw_text,
                    chunk_text = EXCLUDED.chunk_text,
                    embedding_semantic = EXCLUDED.embedding_semantic,
                    embedding_category = EXCLUDED.embedding_category,
                    category_slug = EXCLUDED.category_slug,
                    severity = EXCLUDED.severity,
                    source = EXCLUDED.source,
                    reviewed_by = EXCLUDED.reviewed_by,
                    content_hash = EXCLUDED.content_hash,
                    raw_text_sha256 = EXCLUDED.raw_text_sha256,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    entry.id,
                    entry.raw_text,
                    entry.chunk_text,
                    sem,
                    cat,
                    entry.category_slug,
                    entry.severity,
                    entry.source,
                    entry.reviewed_by,
                    entry.content_hash,
                    raw_sha,
                    entry.created_at,
                    entry.updated_at,
                ),
            )
        self._conn.commit()

    def delete_seed_entries_by_category(self, category_slug: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._seeds} WHERE category_slug = %s", (category_slug,))
            deleted = cur.rowcount
        self._conn.commit()
        return deleted

    def truncate_seed_entries(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self._seeds}")
            deleted = cur.rowcount
        self._conn.commit()
        return deleted

    def get_seed_entry(self, entry_id: str) -> SeedEntryRecord | None:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, raw_text, chunk_text, embedding_semantic, embedding_category,
                       category_slug, severity, source, reviewed_by, created_at, updated_at,
                       content_hash, raw_text_sha256
                FROM {self._seeds} WHERE id = %s
                """,
                (entry_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    def list_seed_entries_by_category(self, category_slug: str) -> list[SeedEntryRecord]:
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, raw_text, chunk_text, embedding_semantic, embedding_category,
                       category_slug, severity, source, reviewed_by, created_at, updated_at,
                       content_hash, raw_text_sha256
                FROM {self._seeds} WHERE category_slug = %s ORDER BY created_at
                """,
                (category_slug,),
            )
            rows = cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    def _row_to_entry(self, row: tuple) -> SeedEntryRecord:
        sem = list(row[3]) if row[3] is not None else []
        cat = list(row[4]) if row[4] is not None else []
        raw_text = row[1] or ""
        raw_sha = row[12] if len(row) > 12 else ""
        content_hash = row[11] if len(row) > 11 else ""
        if not raw_text and raw_sha and self._blob_store is not None:
            hydrated = self._blob_store.get_raw_text(raw_sha)
            if hydrated:
                raw_text = hydrated
        return SeedEntryRecord(
            id=row[0],
            raw_text=raw_text,
            chunk_text=row[2],
            embedding_semantic=[float(x) for x in sem],
            embedding_category=[float(x) for x in cat],
            category_slug=row[5],
            severity=row[6],
            source=row[7],
            reviewed_by=row[8],
            content_hash=content_hash or "",
            raw_text_sha256=raw_sha or "",
            created_at=_parse_ts(row[9]),
            updated_at=_parse_ts(row[10]),
        )

    def _ann_search(
        self,
        vector: list[float],
        *,
        field: str,
        category_slugs: list[str] | None,
        top_k: int,
    ) -> list[VectorSearchResult]:
        column = "embedding_semantic" if field == "semantic" else "embedding_category"
        vec = vector_literal(vector)
        params: list[Any] = [vec, vec]
        where = ""
        if category_slugs is not None:
            where = "WHERE category_slug = ANY(%s)"
            params.append(category_slugs)
        params.append(top_k)
        sql = f"""
            SELECT id, category_slug, chunk_text, severity,
                   1 - ({column} <=> %s::vector) AS score
            FROM {self._seeds}
            {where}
            ORDER BY {column} <=> %s::vector
            LIMIT %s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [
            VectorSearchResult(
                entry_id=r[0],
                score=float(r[4]),
                category_slug=r[1],
                chunk_text=r[2],
                severity=r[3],
            )
            for r in rows
        ]

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
