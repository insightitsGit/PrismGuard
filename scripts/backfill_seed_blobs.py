"""Backfill prismguard_raw_blobs from inline seed_entries.raw_text (pgvector)."""
from __future__ import annotations

import argparse
import os

from prismguard.storage.backends.pgvector import PgvectorBackend
from prismguard.storage.backends.pgvector_schema import qualified
from prismguard.storage.blobs import raw_text_sha256


def backfill(dsn: str, *, schema_prefix: str = "prismguard", clear_inline: bool = False) -> dict:
    backend = PgvectorBackend(dsn=dsn, schema_prefix=schema_prefix)
    conn = backend._connect()  # noqa: SLF001
    seeds = qualified(schema_prefix, "seed_entries")
    blobs = qualified(schema_prefix, "raw_blobs")
    inserted = 0
    updated = 0
    with conn.cursor() as cur:
        cur.execute(f"SELECT id, raw_text, raw_text_sha256 FROM {seeds}")
        rows = cur.fetchall()
    for entry_id, raw_text, existing_sha in rows:
        if not raw_text:
            continue
        digest = existing_sha or raw_text_sha256(raw_text)
        payload = raw_text.encode("utf-8")
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {blobs} (sha256, payload, byte_len, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (sha256) DO NOTHING
                """,
                (digest, payload, len(payload)),
            )
            if cur.rowcount:
                inserted += 1
            cur.execute(
                f"""
                UPDATE {seeds}
                SET raw_text_sha256 = %s, raw_text = %s
                WHERE id = %s
                """,
                (digest, "" if clear_inline else raw_text, entry_id),
            )
            updated += 1
    conn.commit()
    backend.close()
    return {"blob_rows_inserted": inserted, "seed_rows_updated": updated, "total": len(rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill raw text blobs for pgvector seed storage")
    parser.add_argument("--dsn", default=os.environ.get("PRISMGUARD_PG_DSN", ""))
    parser.add_argument("--schema-prefix", default="prismguard")
    parser.add_argument(
        "--clear-inline",
        action="store_true",
        help="Clear inline raw_text after blob write (blob-only mode)",
    )
    args = parser.parse_args(argv)
    if not args.dsn:
        raise SystemExit("Provide --dsn or PRISMGUARD_PG_DSN")
    stats = backfill(args.dsn, schema_prefix=args.schema_prefix, clear_inline=args.clear_inline)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
