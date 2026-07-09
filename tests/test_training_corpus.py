"""Tests for seed-derived classifier training corpus."""

from __future__ import annotations

import json
from pathlib import Path

from prismguard.feedback.review import FeedbackReviewService
from prismguard.models.corpus import (
    TrainingExample,
    build_training_corpus,
    examples_from_parsed_seed,
    merge_training_examples,
)
from prismguard.runtime.check import CheckResult
from prismguard.seed import load_bundled_seed
from prismguard.storage import create_storage


def test_full_seed_corpus_has_attack_and_benign_labels() -> None:
    parsed = load_bundled_seed(profile="full")
    examples = examples_from_parsed_seed(parsed)
    assert len(examples) > 20_000
    injection = sum(1 for row in examples if row.label == 1)
    benign = sum(1 for row in examples if row.label == 0)
    assert injection > 10_000
    assert benign > 10_000


def test_merge_training_examples_fail_closed_on_label_conflict() -> None:
    merged = merge_training_examples(
        [TrainingExample(text="Same prompt text", label=0, source="a")],
        [TrainingExample(text="Same prompt text", label=1, source="b")],
    )
    assert len(merged) == 1
    assert merged[0].label == 1


def test_feedback_jsonl_merges_into_corpus(tmp_path: Path) -> None:
    feedback = tmp_path / "feedback.jsonl"
    feedback.write_text(
        json.dumps({"prompt": "unique reviewed attack", "decision": "block", "source": "feedback"})
        + "\n",
        encoding="utf-8",
    )
    parsed = load_bundled_seed(profile="authored")
    examples, manifest = build_training_corpus(
        parsed_seed=parsed,
        feedback_paths=[feedback],
        profile="authored",
    )
    assert manifest.total_examples >= len(parsed.entries)
    assert any(row.text == "unique reviewed attack" and row.label == 1 for row in examples)


def test_subsample_training_examples_is_stratified() -> None:
    from prismguard.models.corpus import subsample_training_examples

    examples = [TrainingExample(text=f"text-{i}", label=i % 2, source="t") for i in range(100)]
    sampled = subsample_training_examples(examples, max_examples=40)
    assert len(sampled) == 40
    labels = {row.label for row in sampled}
    assert labels == {0, 1}


def test_feedback_export_training_jsonl(tmp_path: Path) -> None:
    storage = create_storage("memory")
    review = FeedbackReviewService(storage)
    result = CheckResult(
        decision="block",
        resolution_gate="guard_model",
        matched_category="direct_instruction_override",
        normalized_prompt="attack",
        details={},
    )
    item = review.enqueue_block(
        prompt="approved attack prompt",
        check_result=result,
        origin="guard_model",
        category_slug="direct_instruction_override",
    )
    review.approve_block(item.id, reviewer="tester")
    out = tmp_path / "feedback.jsonl"
    count = review.export_training_jsonl(out)
    assert count == 1
    payload = json.loads(out.read_text(encoding="utf-8").strip())
    assert payload["decision"] == "block"


def test_feedback_cli_export_default_approved_only(tmp_path: Path, monkeypatch) -> None:
    """CLI export is opt-in; default includes approved blocks, not calibration."""
    from prismguard.feedback.cli import cmd_export
    from types import SimpleNamespace

    store = tmp_path / "feedback.json"
    monkeypatch.setenv("PRISMGUARD_FEEDBACK_PERSIST", "1")
    monkeypatch.setenv("PRISMGUARD_FEEDBACK_PATH", str(store))
    storage = create_storage("memory")
    review = FeedbackReviewService(storage, store_path=store)
    result = CheckResult(
        decision="block",
        resolution_gate="tier1_rule",
        matched_category="direct_instruction_override",
        normalized_prompt="x",
        details={},
    )
    item = review.enqueue_block(
        prompt="cli export attack",
        check_result=result,
        origin="guard_model",
        category_slug="direct_instruction_override",
    )
    review.approve_block(item.id, reviewer="qa")
    out = tmp_path / "out.jsonl"
    code = cmd_export(
        SimpleNamespace(
            output=str(out),
            include_calibration_allows=False,
            calibration_only=False,
            store=str(store),
            backend="memory",
        )
    )
    assert code == 0
    assert "cli export attack" in out.read_text(encoding="utf-8")


def test_default_domain_training_paths_general_opt_in() -> None:
    from prismguard.models.corpus import default_domain_training_paths, plan_training_corpus

    seed, fb = default_domain_training_paths("general")
    assert any("hub_attacks" in str(p) for p in seed)
    assert any("hub_benign" in str(p) for p in fb)

    # Default plan: no domain pack
    plan = plan_training_corpus(profile="authored", domain_pack=None)
    assert plan["domain_pack"] is None
    assert plan["total_examples"] > 0

    plan_g = plan_training_corpus(profile="authored", domain_pack="general")
    assert plan_g["domain_pack"] == "general"
    assert plan_g["total_examples"] >= plan["total_examples"]


def test_eval_holdout_general_schema() -> None:
    from prismguard.models.eval import _holdout_rows, _normal_rows

    rows = _holdout_rows("general")
    assert any(r["traffic_kind"] == "attack" for r in rows)
    normals = _normal_rows("general")
    assert any("Hi" in r["text"] or "pricing" in r["text"].lower() for r in normals) or len(normals) >= 4
