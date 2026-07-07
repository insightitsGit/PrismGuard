from __future__ import annotations

from typing import Any

from prismguard.storage.protocols import RelationalStore, StorageBackend, VectorStore


class PgvectorBackend(StorageBackend):
    """
    Default production backend: Postgres + pgvector for ANN, relational tables co-located.

    Implementation lands in T2 — this class defines the constructor contract only.
    Runtime/seed/audit code must depend on StorageBackend, never import psycopg2 here
    from call sites outside this module.
    """

    def __init__(self, dsn: str, *, schema_prefix: str = "prismguard") -> None:
        self._dsn = dsn
        self._schema_prefix = schema_prefix
        self._vector: VectorStore | None = None
        self._relational: RelationalStore | None = None

    @property
    def backend_name(self) -> str:
        return "pgvector"

    @property
    def vector(self) -> VectorStore:
        if self._vector is None:
            raise NotImplementedError(
                "PgvectorBackend.vector is wired in T2 — use backend='memory' for tests."
            )
        return self._vector

    @property
    def relational(self) -> RelationalStore:
        if self._relational is None:
            raise NotImplementedError(
                "PgvectorBackend.relational is wired in T2 — use backend='memory' for tests."
            )
        return self._relational

    def healthcheck(self) -> bool:
        raise NotImplementedError("PgvectorBackend.healthcheck is wired in T2.")

    def close(self) -> None:
        return None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> PgvectorBackend:
        dsn = config.get("dsn")
        if not dsn:
            raise ValueError("pgvector backend requires 'dsn' in storage config")
        return cls(dsn=dsn, schema_prefix=config.get("schema_prefix", "prismguard"))
