from __future__ import annotations

from typing import Any, Callable

from prismguard.storage.backends.chroma import ChromaBackend
from prismguard.storage.backends.pgvector import PgvectorBackend
from prismguard.storage.backends.pinecone import PineconeBackend
from prismguard.storage.backends.weaviate import WeaviateBackend
from prismguard.storage.memory import InMemoryStorageBackend
from prismguard.storage.protocols import StorageBackend

BackendFactory = Callable[[dict[str, Any]], StorageBackend]

_REGISTRY: dict[str, BackendFactory] = {
    "memory": lambda _cfg: InMemoryStorageBackend(),
    "pgvector": lambda cfg: PgvectorBackend.from_config(cfg),
    "chroma": lambda cfg: ChromaBackend.from_config(cfg),
    "pinecone": lambda cfg: PineconeBackend.from_config(cfg),
    "weaviate": lambda cfg: WeaviateBackend.from_config(cfg),
}

SUPPORTED_BACKENDS = tuple(_REGISTRY.keys())
DEFAULT_BACKEND = "pgvector"


def register_backend(name: str, factory: BackendFactory) -> None:
    """Allow deployments to plug in custom vector stores without forking PrismGuard."""
    _REGISTRY[name] = factory


def create_storage(backend: str = DEFAULT_BACKEND, **config: Any) -> StorageBackend:
    """
    Create a storage backend by name.

    Examples:
        create_storage("memory")
        create_storage("pgvector", dsn="postgresql://...")
        create_storage("chroma", persist_directory="./data/chroma")
        create_storage("pinecone", index_name="prismguard", api_key="...")
    """
    key = backend.lower().strip()
    if key not in _REGISTRY:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown storage backend {backend!r}. Supported: {supported}")
    return _REGISTRY[key](dict(config))


def create_storage_from_env() -> StorageBackend:
    """Read PRISMGUARD_STORAGE_BACKEND and PRISMGUARD_STORAGE_DSN (or backend-specific vars)."""
    import os

    backend = os.environ.get("PRISMGUARD_STORAGE_BACKEND", DEFAULT_BACKEND)
    config: dict[str, Any] = {}
    if dsn := os.environ.get("PRISMGUARD_STORAGE_DSN"):
        config["dsn"] = dsn
    if index := os.environ.get("PRISMGUARD_PINECONE_INDEX"):
        config["index_name"] = index
    if persist := os.environ.get("PRISMGUARD_CHROMA_PERSIST_DIR"):
        config["persist_directory"] = persist
    if url := os.environ.get("PRISMGUARD_WEAVIATE_URL"):
        config["url"] = url
    return create_storage(backend, **config)
