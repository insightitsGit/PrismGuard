from __future__ import annotations

from prismguard.taxonomy.embedder import CachedEmbedder, HashEmbedder


def test_cached_embedder_reuses_semantic_vectors() -> None:
    inner = HashEmbedder()
    cached = CachedEmbedder(inner, max_entries=8)
    first = cached.embed_semantic("same prompt")
    second = cached.embed_semantic("same prompt")
    assert first == second
    assert len(cached._semantic_cache) == 1  # noqa: SLF001


def test_cached_embedder_evicts_oldest_entry() -> None:
    inner = HashEmbedder()
    cached = CachedEmbedder(inner, max_entries=2)
    cached.embed_semantic("a")
    cached.embed_semantic("b")
    cached.embed_semantic("c")
    assert len(cached._semantic_cache) == 2  # noqa: SLF001
    assert "a" not in cached._semantic_cache  # noqa: SLF001
