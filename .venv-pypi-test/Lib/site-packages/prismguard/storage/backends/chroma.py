from __future__ import annotations

from typing import Any

from prismguard.storage.backends.pgvector import PgvectorBackend
from prismguard.storage.protocols import StorageBackend


class ChromaBackend(StorageBackend):
    """
    ChromaDB vector backend — delegates ANN to prismrag-patch ChromaAdapter pattern.

    Relational taxonomy/audit tables use embedded SQLite unless `relational_dsn` is set.
    Full implementation in T2b.
    """

    def __init__(self, collection_name: str = "prismguard_seeds", *, persist_directory: str | None = None) -> None:
        self._collection_name = collection_name
        self._persist_directory = persist_directory
        self._delegate: StorageBackend | None = None

    @property
    def backend_name(self) -> str:
        return "chroma"

    @property
    def vector(self):
        raise NotImplementedError("ChromaBackend is wired in T2b — use backend='memory' for tests.")

    @property
    def relational(self):
        raise NotImplementedError("ChromaBackend is wired in T2b — use backend='memory' for tests.")

    def healthcheck(self) -> bool:
        raise NotImplementedError("ChromaBackend is wired in T2b.")

    def close(self) -> None:
        return None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ChromaBackend:
        return cls(
            collection_name=config.get("collection_name", "prismguard_seeds"),
            persist_directory=config.get("persist_directory"),
        )
