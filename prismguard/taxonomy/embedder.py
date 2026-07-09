from __future__ import annotations

import hashlib
import math
import os
from collections import OrderedDict
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    semantic_dim: int
    category_dim: int

    def embed_semantic(self, text: str) -> list[float]: ...

    def embed_category_base(self, text: str, category_slug: str) -> list[float]: ...


def _hash_to_vector(text: str, dim: int) -> list[float]:
    """Deterministic unit vector for tests and offline ingest without GPU."""
    raw: list[float] = []
    counter = 0
    while len(raw) < dim:
        digest = hashlib.blake2b(f"{text}:{counter}".encode("utf-8"), digest_size=64).digest()
        for i in range(0, 64, 4):
            raw.append(int.from_bytes(digest[i : i + 4], "big") / 2**32)
        counter += 1
    raw = raw[:dim]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


def _pool_dims(vector: list[float], target_dim: int) -> list[float]:
    if len(vector) == target_dim:
        return list(vector)
    if target_dim <= 0:
        return []
    chunk = max(1, len(vector) // target_dim)
    pooled: list[float] = []
    for i in range(target_dim):
        start = i * chunk
        end = min(len(vector), start + chunk)
        if start >= len(vector):
            pooled.append(0.0)
            continue
        pooled.append(sum(vector[start:end]) / (end - start))
    norm = math.sqrt(sum(x * x for x in pooled)) or 1.0
    return [x / norm for x in pooled]


class HashEmbedder:
    """Lightweight deterministic embedder — no network, no GPU."""

    semantic_dim = 768
    category_dim = 256

    def embed_semantic(self, text: str) -> list[float]:
        return _hash_to_vector(f"sem:{text}", self.semantic_dim)

    def embed_category_base(self, text: str, category_slug: str) -> list[float]:
        return _hash_to_vector(f"cat:{category_slug}:{text}", self.category_dim)


def create_embedder(prefer_transformer: bool = False, *, model_name: str | None = None) -> Embedder:
    if prefer_transformer:
        try:
            return SentenceTransformerEmbedder(model_name=model_name or "sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            pass
    return HashEmbedder()


def create_embedder_from_config(cfg) -> Embedder:
    embedder = create_embedder(
        prefer_transformer=getattr(cfg.embedding, "prefer_transformer", False),
        model_name=getattr(cfg.embedding, "model_name", None),
    )
    return maybe_cache_embedder(embedder)


class CachedEmbedder:
    """LRU cache for semantic vectors — keyed by normalized prompt text."""

    def __init__(self, inner: Embedder, *, max_entries: int = 512) -> None:
        self._inner = inner
        self._max_entries = max(1, max_entries)
        self._semantic_cache: OrderedDict[str, list[float]] = OrderedDict()
        self._category_cache: OrderedDict[str, list[float]] = OrderedDict()

    @property
    def semantic_dim(self) -> int:
        return self._inner.semantic_dim

    @property
    def category_dim(self) -> int:
        return self._inner.category_dim

    def _remember(self, cache: OrderedDict[str, list[float]], key: str, value: list[float]) -> list[float]:
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        cache[key] = value
        if len(cache) > self._max_entries:
            cache.popitem(last=False)
        return value

    def embed_semantic(self, text: str) -> list[float]:
        return self._remember(self._semantic_cache, text, self._inner.embed_semantic(text))

    def embed_category_base(self, text: str, category_slug: str) -> list[float]:
        key = f"{category_slug}\0{text}"
        return self._remember(
            self._category_cache,
            key,
            self._inner.embed_category_base(text, category_slug),
        )


def maybe_cache_embedder(embedder: Embedder) -> Embedder:
    max_entries = int(os.environ.get("PRISMGUARD_EMBED_CACHE_SIZE", "512"))
    if max_entries <= 0:
        return embedder
    return CachedEmbedder(embedder, max_entries=max_entries)


class SentenceTransformerEmbedder:
    semantic_dim = 768
    category_dim = 256

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        dim = self._model.get_sentence_embedding_dimension()
        if dim is not None:
            self.semantic_dim = int(dim)

    def embed_semantic(self, text: str) -> list[float]:
        vec = self._model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vec]

    def embed_category_base(self, text: str, category_slug: str) -> list[float]:
        anchored = f"[{category_slug}] {text}"
        sem = self.embed_semantic(anchored)
        return _pool_dims(sem, self.category_dim)
