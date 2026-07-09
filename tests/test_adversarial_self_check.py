from scripts.adversarial_self_check import run_self_check


def test_adversarial_self_check_fast_gates() -> None:
    report = run_self_check(skip_slow=True)
    assert report.ship_ready, [(g.name, g.detail) for g in report.gates if not g.passed]
