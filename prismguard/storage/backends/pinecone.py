from __future__ import annotations

from typing import Any

from prismguard.storage.protocols import StorageBackend


class PineconeBackend(StorageBackend):
    """Pinecone vector backend — implementation in T2b."""

    def __init__(self, index_name: str, *, namespace: str = "prismguard") -> None:
        self._index_name = index_name
        self._namespace = namespace

    @property
    def backend_name(self) -> str:
        return "pinecone"

    @property
    def vector(self):
        raise NotImplementedError("PineconeBackend is wired in T2b — use backend='memory' for tests.")

    @property
    def relational(self):
        raise NotImplementedError("PineconeBackend is wired in T2b — use backend='memory' for tests.")

    def healthcheck(self) -> bool:
        raise NotImplementedError("PineconeBackend is wired in T2b.")

    def close(self) -> None:
        return None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> PineconeBackend:
        index_name = config.get("index_name")
        if not index_name:
            raise ValueError("pinecone backend requires 'index_name' in storage config")
        return cls(index_name=index_name, namespace=config.get("namespace", "prismguard"))
