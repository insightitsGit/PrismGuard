from __future__ import annotations

SCHEMA_VERSION = 2


def qualified(schema_prefix: str, table: str) -> str:
    return f"{schema_prefix}_{table}"


def _migrate_to_v2(cur, *, schema_prefix: str) -> None:
    seeds = qualified(schema_prefix, "seed_entries")
    blobs = qualified(schema_prefix, "raw_blobs")
    meta = qualified(schema_prefix, "schema_meta")

    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {blobs} (
            sha256 TEXT PRIMARY KEY,
            payload BYTEA NOT NULL,
            byte_len INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        f"ALTER TABLE {seeds} ADD COLUMN IF NOT EXISTS content_hash TEXT NOT NULL DEFAULT ''"
    )
    cur.execute(
        f"ALTER TABLE {seeds} ADD COLUMN IF NOT EXISTS raw_text_sha256 TEXT NOT NULL DEFAULT ''"
    )
    cur.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{schema_prefix}_seed_content_hash ON {seeds} (content_hash)"
    )
    cur.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{schema_prefix}_seed_raw_sha ON {seeds} (raw_text_sha256)"
    )
    cur.execute(f"UPDATE {meta} SET version = %s, updated_at = NOW()", (SCHEMA_VERSION,))


def ensure_schema(conn, *, schema_prefix: str = "prismguard") -> None:
    """Create pgvector extension and PrismGuard tables if missing."""
    categories = qualified(schema_prefix, "categories")
    rules = qualified(schema_prefix, "rules")
    seeds = qualified(schema_prefix, "seed_entries")
    imports = qualified(schema_prefix, "import_logs")
    meta = qualified(schema_prefix, "schema_meta")
    blobs = qualified(schema_prefix, "raw_blobs")

    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {meta} (
                version INTEGER NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {categories} (
                slug TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                is_attack_category BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {rules} (
                rule_id TEXT PRIMARY KEY,
                pattern TEXT NOT NULL,
                pattern_type TEXT NOT NULL DEFAULT 'regex',
                category_slug TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                rationale TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {seeds} (
                id TEXT PRIMARY KEY,
                raw_text TEXT NOT NULL DEFAULT '',
                chunk_text TEXT NOT NULL,
                embedding_semantic vector(768) NOT NULL,
                embedding_category vector(256) NOT NULL,
                category_slug TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                source TEXT NOT NULL DEFAULT '',
                reviewed_by TEXT NULL,
                content_hash TEXT NOT NULL DEFAULT '',
                raw_text_sha256 TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {blobs} (
                sha256 TEXT PRIMARY KEY,
                payload BYTEA NOT NULL,
                byte_len INTEGER NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {imports} (
                id TEXT PRIMARY KEY,
                source_filename TEXT NOT NULL,
                mode TEXT NOT NULL,
                scope TEXT NOT NULL,
                inserted INTEGER NOT NULL DEFAULT 0,
                updated INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                errored INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{schema_prefix}_seed_category ON {seeds} (category_slug)")
        cur.execute(f"SELECT COUNT(*) FROM {meta}")
        if cur.fetchone()[0] == 0:
            cur.execute(f"INSERT INTO {meta} (version, updated_at) VALUES (%s, NOW())", (SCHEMA_VERSION,))
        else:
            cur.execute(f"SELECT version FROM {meta} ORDER BY updated_at DESC LIMIT 1")
            version_row = cur.fetchone()
            current = int(version_row[0]) if version_row else 1
            if current < 2:
                _migrate_to_v2(cur, schema_prefix=schema_prefix)
    conn.commit()
