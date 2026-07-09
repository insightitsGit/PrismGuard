from __future__ import annotations

import os

import pytest

from prismguard.calibration.tune import tune_thresholds
from prismguard.config.loader import load_triage_config
from prismguard.feedback.review import FeedbackReviewService
from prismguard.runtime.check import CheckResult
from prismguard.runtime.output_scan import scan_output
from prismguard.storage import create_storage


def test_output_scan_blocks_exfil_url() -> None:
    result = scan_output("See details at https://attacker.example/leak?data=ALL")
    assert result.decision == "block"
    assert result.matched_pattern == "suspicious_url"


def test_output_scan_allows_normal_text() -> None:
    result = scan_output("The NDA requires 30 days written notice for termination.")
    assert result.decision == "allow"


def test_feedback_store_roundtrip(tmp_path) -> None:
    store_path = tmp_path / "feedback.json"
    storage = create_storage("memory")
    os.environ["PRISMGUARD_FEEDBACK_PERSIST"] = "1"
    try:
        service = FeedbackReviewService(storage, store_path=store_path)
        item = service.enqueue_block(
            prompt="test attack",
            check_result=CheckResult(
                decision="block",
                resolution_gate="guard_model",
                normalized_prompt="test attack",
            ),
            origin="guard_model",
            category_slug="direct_instruction_override",
        )
        reloaded = FeedbackReviewService(storage, store_path=store_path)
        assert item.id in reloaded._queue
        restored = reloaded._queue[item.id]
        assert isinstance(restored.check_result, CheckResult)
        assert restored.check_result.decision == "block"
        assert restored.check_result.resolution_gate == "guard_model"
    finally:
        os.environ.pop("PRISMGUARD_FEEDBACK_PERSIST", None)
        storage.close()


def test_tune_thresholds_law() -> None:
    pytest.importorskip("prismrag_patch")
    result = tune_thresholds(
        domain="law",
        block_grid=[0.68, 0.74],
        allow_grid=[0.40, 0.46],
        w_clf_grid=[0.25, 0.32],
    )
    assert result.normal_allow_rate == 1.0
    assert 0.0 <= result.holdout_block_rate <= 1.0


def test_domain_triage_merge() -> None:
    cfg = load_triage_config(domain="law")
    assert cfg.triage.block_threshold == 0.74
    assert cfg.fusion.w_clf == 0.35
    assert cfg.guard_model.disagreement_escalation is True


def test_domain_holdout_packs_exist() -> None:
    from prismguard.domains.registry import get_domain_pack

    for domain in ("law", "healthcare", "finance"):
        pack = get_domain_pack(domain)
        assert pack.holdout_path is not None
        assert pack.holdout_path.is_file()
