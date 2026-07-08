"""Tests for law-focused corpus oversampling."""

from __future__ import annotations

from prismguard.models.corpus import TrainingExample, oversample_thin_categories


def test_oversample_thin_categories_increases_refusal_suppression() -> None:
    examples = [
        TrainingExample(text="attack one", label=1, category_slug="refusal_suppression"),
        TrainingExample(text="safe one", label=0, category_slug="benign_adjacent"),
    ]
    boosted = oversample_thin_categories(examples, min_count=5)
    refusal = [row for row in boosted if row.category_slug == "refusal_suppression"]
    assert len(refusal) >= 5
