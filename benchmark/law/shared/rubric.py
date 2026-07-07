from __future__ import annotations

from benchmark.law.shared.cases import LawQuery


def score_law_answer(answer: str, query: LawQuery) -> bool:
    text = (answer or "").strip().lower()
    if len(text) < 20:
        return False
    if not query.must_cite:
        return True
    return all(term.lower() in text for term in query.must_cite)
