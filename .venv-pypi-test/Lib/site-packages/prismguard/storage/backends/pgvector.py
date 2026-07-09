from __future__ import annotations

from typing import Any

from prismguard.storage.backends.pgvector_schema import ensure_schema
from prismguard.storage.backends.pgvector_stores import PgvectorRelationalStore, PgvectorVectorStore
from prismguard.storage.blobs import PgBlobStore
from prismguard.storage.protocols import RelationalStore, StorageBackend, VectorStore


class PgvectorBackend(StorageBackend):
    """
    Production backend: Postgres + pgvector for ANN, relational tables co-located.
    """

    def __init__(self, dsn: str, *, schema_prefix: str = "prismguard", autocommit: bool = False) -> None:
        self._dsn = dsn
        self._schema_prefix = schema_prefix
        self._autocommit = autocommit
        self._conn: Any = None
        self._vector: PgvectorVectorStore | None = None
        self._relational: PgvectorRelationalStore | None = None

    def _connect(self) -> Any:
        if self._conn is not None:
            return self._conn
        try:
            import psycopg2
        except ImportError as exc:
            raise ImportError(
                "pgvector backend requires psycopg2 — pip install prismguard[pgvector]"
            ) from exc
        self._conn = psycopg2.connect(self._dsn)
        self._conn.autocommit = self._autocommit
        ensure_schema(self._conn, schema_prefix=self._schema_prefix)
        blob_store = PgBlobStore(self._conn, schema_prefix=self._schema_prefix)
        self._vector = PgvectorVectorStore(
            self._conn,
            schema_prefix=self._schema_prefix,
            blob_store=blob_store,
        )
        self._relational = PgvectorRelationalStore(self._conn, schema_prefix=self._schema_prefix)
        return self._conn

    @property
    def backend_name(self) -> str:
        return "pgvector"

    @property
    def vector(self) -> VectorStore:
        self._connect()
        assert self._vector is not None
        return self._vector

    @property
    def relational(self) -> RelationalStore:
        self._connect()
        assert self._relational is not None
        return self._relational

    def healthcheck(self) -> bool:
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        except Exception:
            return False

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._vector = None
            self._relational = None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> PgvectorBackend:
        dsn = config.get("dsn")
        if not dsn:
            raise ValueError("pgvector backend requires 'dsn' in storage config")
        return cls(dsn=dsn, schema_prefix=config.get("schema_prefix", "prismguard"))
