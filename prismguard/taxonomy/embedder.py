from __future__ import annotations

import hashlib
import math
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


def create_embedder(prefer_transformer: bool = True) -> Embedder:
    if prefer_transformer:
        try:
            return SentenceTransformerEmbedder()
        except ImportError:
            pass
    return HashEmbedder()


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
