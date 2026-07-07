from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import numpy as np

from prismguard.taxonomy.embedder import Embedder

log = logging.getLogger(__name__)

_TENANT = "prismguard"


@dataclass
class TaxonomyGraphEngine:
    """Word-graph BFS + Louvain community routing via prismRAG patch."""

    _store: object | None = None
    _mapping_id: str = ""
    _attack_categories: set[str] = field(default_factory=set)
    _category_by_word: dict[str, str] = field(default_factory=dict)
    _ready: bool = False
    _init_error: str = ""

    @classmethod
    def from_mapping(
        cls,
        *,
        mapping_dict: dict,
        embedder: Embedder,
        attack_categories: set[str],
        seed_texts: list[tuple[str, str]] | None = None,
    ) -> TaxonomyGraphEngine:
        engine = cls(_attack_categories=set(attack_categories))
        try:
            from prismrag_patch.graph.builder import build_graph
            from prismrag_patch.graph.community import build_communities
            from prismrag_patch.models import MappingConfig
            from prismrag_patch.store.memory import MemoryStore
        except ImportError as exc:
            engine._init_error = f"prismrag_patch graph unavailable: {exc}"
            return engine

        try:
            from prismrag_patch.retrieval.search import _bfs_expand, _rank_communities  # noqa: PLC2701

            store = MemoryStore()
            config = MappingConfig.from_dict(mapping_dict)
            mapping_id = store.persist_mapping(_TENANT, config, strategy="rules")
            category_by_word: dict[str, str] = {}

            def add_word(word: str, text: str, slug: str) -> None:
                token = word.lower().strip()
                if len(token) < 4:
                    return
                sem = np.array(embedder.embed_semantic(text), dtype=float)
                store.upsert_chunk(
                    _TENANT,
                    mapping_id,
                    chunk_ref=token,
                    chunk_text=text[:500],
                    category_slug=slug,
                    embedding=sem,
                    sem_embedding=sem,
                )
                category_by_word[token] = slug

            for rule in mapping_dict.get("rules", []):
                add_word(str(rule.get("word", "")), str(rule.get("word", "")), str(rule["category_slug"]))

            for text, slug in seed_texts or []:
                for token in re.findall(r"[a-z0-9]{4,}", text.lower()):
                    add_word(token, text, slug)

            build_graph(store, _TENANT, mapping_id)
            try:
                build_communities(store, _TENANT, mapping_id)
            except Exception as comm_exc:
                log.warning("Louvain community build skipped: %s", comm_exc)

            engine._store = store
            engine._mapping_id = mapping_id
            engine._category_by_word = category_by_word
            engine._ready = True
            engine._bfs_expand = _bfs_expand  # type: ignore[attr-defined]
            engine._rank_communities = _rank_communities  # type: ignore[attr-defined]
        except Exception as exc:
            engine._init_error = str(exc)
            log.warning("TaxonomyGraphEngine init failed: %s", exc)
        return engine

    @property
    def ready(self) -> bool:
        return self._ready

    def graph_connectivity_score(self, text: str, category_slug: str | None) -> float:
        if not self._ready or not category_slug or self._store is None:
            return 0.0
        tokens = list(dict.fromkeys(re.findall(r"[a-z0-9]{4,}", text.lower())))[:12]
        if not tokens:
            return 0.0
        expanded = self._bfs_expand(self._store, _TENANT, self._mapping_id, tokens)  # type: ignore[attr-defined]
        reachable = set(tokens) | set(expanded)
        category_hits = sum(1 for word in reachable if self._category_by_word.get(word) == category_slug)
        if category_hits == 0:
            return 0.0
        return min(1.0, category_hits / max(1, len(tokens)))

    def community_confidence(
        self,
        semantic_vector: list[float],
        category_slug: str | None,
        *,
        rule_matched: bool,
    ) -> float:
        if not self._ready or self._store is None:
            if rule_matched and category_slug:
                return 1.0
            return 0.5 if category_slug else 0.0

        communities_raw = self._store.list_communities(_TENANT, self._mapping_id)
        if not communities_raw:
            if rule_matched and category_slug:
                return 1.0
            return 0.5 if category_slug else 0.0

        communities = [
            {
                "community_id": c.community_id,
                "label": c.label,
                "centroid_vec": c.centroid_vec,
                "top_words": c.top_words,
            }
            for c in communities_raw
        ]
        query_sem = np.array(semantic_vector, dtype=float)
        norm = np.linalg.norm(query_sem)
        if norm > 0:
            query_sem = query_sem / norm

        ranked = self._rank_communities(query_sem, communities)  # type: ignore[attr-defined]
        if not ranked:
            return 0.5 if category_slug else 0.0

        best_cid, best_weight = ranked[0]
        comm = next((c for c in communities if c["community_id"] == best_cid), None)
        if comm is None:
            return float(best_weight)

        top_words = comm.get("top_words") or []
        member_categories = {self._category_by_word.get(word) for word in top_words}
        if category_slug and category_slug in member_categories:
            return min(1.0, 0.55 + float(best_weight))
        if rule_matched and category_slug:
            return 0.85
        return max(0.0, float(best_weight) * 0.75)
