import pytest


def test_eval_self_check_config_only() -> None:
    from prismguard.eval.self_check import run_user_verify

    report = run_user_verify(skip_runtime=True)
    assert any(g.name == "disagreement_escalation" for g in report.gates)
    assert report.ok


def test_eval_self_check_rules_only_passes(monkeypatch) -> None:
    """Bare install path: no ONNX opt-in → VERIFY_OK with rules-only attack bar."""
    monkeypatch.delenv("PRISMGUARD_USE_ONNX", raising=False)
    monkeypatch.setenv("PRISMGUARD_OFFLINE", "1")
    from prismguard.eval.self_check import format_report, run_user_verify
    from prismguard.runtime.factory import clear_checker_singletons

    clear_checker_singletons()
    report = run_user_verify()
    assert report.ok, format_report(report)
    names = {g.name: g for g in report.gates}
    assert names["classifier_ready"].passed
    assert "rules-only" in names["classifier_ready"].detail
    assert names["fresh_attacks_rules_only"].passed
