from benchmark.shared.holdout_quality import infer_register, infer_style, verify_phrasing_diversity


def test_infer_style_short_fragment() -> None:
    assert infer_style("Indemnity cap in vendor SaaS agreement", "") == "short_fragment"


def test_infer_style_full_question() -> None:
    assert infer_style("What is the typical cure period before a lease default?", "") == "full_question"


def test_infer_register_casual() -> None:
    assert infer_register("hey — can you help me with this clause?", "") == "casual"


def test_phrasing_diversity_passes_balanced_set() -> None:
    rows = [
        {"text": "a", "style": "short_fragment", "register": "formal"},
        {"text": "b", "style": "short_fragment", "register": "formal"},
        {"text": "c", "style": "short_fragment", "register": "casual"},
        {"text": "d", "style": "short_fragment", "register": "casual"},
        {"text": "What is x?", "style": "full_question", "register": "formal"},
        {"text": "What is y?", "style": "full_question", "register": "formal"},
        {"text": "Can you explain z?", "style": "full_question", "register": "casual"},
        {"text": "Help me with w?", "style": "full_question", "register": "casual"},
    ] + [{"text": f"pad {i}?", "style": "full_question", "register": "formal"} for i in range(12)]
    report = verify_phrasing_diversity(rows, min_per_quadrant=2, min_total_for_rule=20)
    assert report.passes


def test_phrasing_diversity_fails_missing_quadrant() -> None:
    rows = [{"text": f"formal short {i}", "style": "short_fragment", "register": "formal"} for i in range(20)]
    report = verify_phrasing_diversity(rows, min_per_quadrant=4, min_total_for_rule=20)
    assert not report.passes
    assert any("casual" in v for v in report.violations)
