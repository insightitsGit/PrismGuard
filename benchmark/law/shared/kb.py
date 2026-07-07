from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class LawDocument:
    doc_id: str
    category_slug: str
    title: str
    text: str


@dataclass(frozen=True)
class LawCategory:
    slug: str
    label: str


def load_kb_documents(path: Path | None = None) -> list[LawDocument]:
    raw_path = path or DATA_DIR / "kb_documents.yaml"
    with raw_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        LawDocument(
            doc_id=item["id"],
            category_slug=item["category_slug"],
            title=item["title"],
            text=item["text"],
        )
        for item in raw.get("documents", [])
    ]


def load_categories(path: Path | None = None) -> list[LawCategory]:
    raw_path = path or DATA_DIR / "kb_documents.yaml"
    with raw_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        LawCategory(slug=item["slug"], label=item.get("label", item["slug"]))
        for item in raw.get("categories", [])
    ]


def build_in_memory_index(documents: list[LawDocument] | None = None) -> dict[str, Any]:
    """Simple token index for deterministic offline retrieval."""
    docs = documents or load_kb_documents()
    return {
        "documents": docs,
        "by_category": _group_by_category(docs),
    }


def _group_by_category(docs: list[LawDocument]) -> dict[str, list[LawDocument]]:
    grouped: dict[str, list[LawDocument]] = {}
    for doc in docs:
        grouped.setdefault(doc.category_slug, []).append(doc)
    return grouped


def retrieve(index: dict[str, Any], query: str, *, category_slug: str | None = None, top_k: int = 3) -> list[LawDocument]:
    tokens = set(query.lower().split())
    candidates = index["documents"]
    if category_slug:
        candidates = index["by_category"].get(category_slug, candidates)

    scored: list[tuple[float, LawDocument]] = []
    for doc in candidates:
        doc_tokens = set(doc.text.lower().split()) | set(doc.title.lower().split())
        overlap = len(tokens & doc_tokens)
        if overlap:
            scored.append((overlap / max(len(tokens), 1), doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]
