from prismguard.config import TriageConfig, load_triage_config


def test_load_default_triage_config() -> None:
    config = load_triage_config()
    assert isinstance(config, TriageConfig)
    assert config.fusion.min_weak_signals_for_gray == 2
    assert config.benign_fast_path.benign_margin_delta == 0.08
    assert config.judge.rate_cap_per_minute == 60
    assert config.normalization.max_obfuscation_depth == 3


def test_part_i_fusion_weights_present() -> None:
    config = load_triage_config()
    fusion = config.fusion
    assert fusion.w_sim > 0
    assert fusion.w_benign > 0
    assert fusion.w_session > 0
