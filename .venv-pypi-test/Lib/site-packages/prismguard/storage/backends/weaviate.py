from __future__ import annotations

from typing import Any

from prismguard.storage.protocols import StorageBackend


class WeaviateBackend(StorageBackend):
    """Weaviate vector backend — implementation in T2b."""

    def __init__(self, class_name: str = "PrismGuardSeed", *, url: str | None = None) -> None:
        self._class_name = class_name
        self._url = url

    @property
    def backend_name(self) -> str:
        return "weaviate"

    @property
    def vector(self):
        raise NotImplementedError("WeaviateBackend is wired in T2b — use backend='memory' for tests.")

    @property
    def relational(self):
        raise NotImplementedError("WeaviateBackend is wired in T2b — use backend='memory' for tests.")

    def healthcheck(self) -> bool:
        raise NotImplementedError("WeaviateBackend is wired in T2b.")

    def close(self) -> None:
        return None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> WeaviateBackend:
        return cls(class_name=config.get("class_name", "PrismGuardSeed"), url=config.get("url"))
