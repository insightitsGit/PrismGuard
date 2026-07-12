import pytest


def test_format_check_result_allow_shape() -> None:
    from prismguard.cli_check import format_check_result
    from prismguard.runtime.check import CheckResult

    text = format_check_result(
        CheckResult(
            decision="allow",
            resolution_gate="structural",
            matched_category="benign_adjacent",
            details={"decision_source": "structural_benign_framing"},
        )
    )
    assert text.startswith("ALLOW")
    assert "resolution_gate=structural" in text


def test_format_check_result_block_shape() -> None:
    from prismguard.cli_check import format_check_result
    from prismguard.runtime.check import CheckResult

    text = format_check_result(
        CheckResult(
            decision="block",
            resolution_gate="guard_model_first",
            details={"decision_source": "classifier_first→block", "guard_model_confidence": 0.91},
        )
    )
    assert text.startswith("BLOCKED")
    assert "confidence=0.91" in text
    assert "decision_source=classifier_first->block" in text
    assert "→" not in text


def test_format_check_result_ascii_safe_arrow() -> None:
    from prismguard.cli_check import format_check_result
    from prismguard.runtime.check import CheckResult

    text = format_check_result(
        CheckResult(
            decision="allow",
            resolution_gate="fusion_allow",
            details={"decision_source": "classifier_only→no_model"},
        )
    )
    assert "decision_source=classifier_only->no_model" in text
    assert "→" not in text
