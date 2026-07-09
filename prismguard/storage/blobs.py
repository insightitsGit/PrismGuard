"""Content-addressed raw text blob storage (PrismCortex-style cold storage)."""

from __future__ import annotations

import hashlib
from typing import Protocol


def raw_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class BlobStore(Protocol):
    def put_raw_text(self, text: str) -> str: ...

    def get_raw_text(self, sha256: str) -> str | None: ...


class InMemoryBlobStore:
    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}

    def put_raw_text(self, text: str) -> str:
        digest = raw_text_sha256(text)
        self._blobs.setdefault(digest, text.encode("utf-8"))
        return digest

    def get_raw_text(self, sha256: str) -> str | None:
        payload = self._blobs.get(sha256)
        if payload is None:
            return None
        return payload.decode("utf-8")


class PgBlobStore:
    def __init__(self, conn, *, schema_prefix: str = "prismguard") -> None:
        from prismguard.storage.backends.pgvector_schema import qualified

        self._conn = conn
        self._table = qualified(schema_prefix, "raw_blobs")

    def put_raw_text(self, text: str) -> str:
        digest = raw_text_sha256(text)
        payload = text.encode("utf-8")
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self._table} (sha256, payload, byte_len, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (sha256) DO NOTHING
                """,
                (digest, payload, len(payload)),
            )
        self._conn.commit()
        return digest

    def get_raw_text(self, sha256: str) -> str | None:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT payload FROM {self._table} WHERE sha256 = %s", (sha256,))
            row = cur.fetchone()
        if not row:
            return None
        payload = row[0]
        if isinstance(payload, memoryview):
            payload = payload.tobytes()
        return bytes(payload).decode("utf-8")
