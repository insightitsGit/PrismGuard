import pytest


def test_eval_self_check_config_only() -> None:
    from prismguard.eval.self_check import run_user_verify

    report = run_user_verify(skip_runtime=True)
    assert any(g.name == "disagreement_escalation" for g in report.gates)
    assert report.ok
