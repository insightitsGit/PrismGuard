"""HO-018: generic domain_pilot profile (no per-domain *_pilot inventions)."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("PRISMGUARD_USE_ONNX", raising=False)
    monkeypatch.delenv("PRISMGUARD_SHADOW_ONNX", raising=False)
    monkeypatch.setenv("PRISMGUARD_OFFLINE", "1")
    monkeypatch.delenv("PRISMGUARD_DOMAIN", raising=False)
    monkeypatch.delenv("PRISMGUARD_APP_PROFILE", raising=False)
    monkeypatch.delenv("PRISMGUARD_ARTIFACT_ID", raising=False)
    from prismguard.runtime.factory import clear_checker_singletons

    clear_checker_singletons()
    yield
    clear_checker_singletons()


def test_normalize_law_pilot_alias_to_domain_pilot() -> None:
    from prismguard.runtime.factory import normalize_app_profile

    assert normalize_app_profile("law_pilot") == "domain_pilot"
    assert normalize_app_profile("domain_pilot") == "domain_pilot"


def test_domain_pilot_requires_domain(monkeypatch) -> None:
    from prismguard.runtime.factory import create_checker_for_app

    monkeypatch.delenv("PRISMGUARD_DOMAIN", raising=False)
    with pytest.raises(ValueError, match="requires domain"):
        create_checker_for_app("domain_pilot", use_onnx=False)


def test_domain_pilot_finance_builds(monkeypatch) -> None:
    from prismguard.runtime.factory import create_checker_for_app

    checker = create_checker_for_app("domain_pilot", domain="finance", use_onnx=False)
    assert checker is not None
    # Offline → no ONNX, but finance overlay is loaded into storage path.
    result = checker.check("Hi")
    assert result.decision != "block"


def test_law_pilot_alias_defaults_domain_law(monkeypatch) -> None:
    from prismguard.runtime.factory import create_checker_for_app, resolve_domain_pilot_domain

    # Alias must stay law even when shell has a finance bake-off domain.
    monkeypatch.setenv("PRISMGUARD_DOMAIN", "finance")
    assert resolve_domain_pilot_domain(None, requested_profile="law_pilot") == "law"
    checker = create_checker_for_app("law_pilot", use_onnx=False)
    assert checker is not None
    assert getattr(checker, "_config", None) is not None


def test_rejects_finance_pilot_invention() -> None:
    from prismguard.runtime.factory import create_checker_for_app

    with pytest.raises(ValueError, match="do not invent"):
        create_checker_for_app("finance_pilot", domain="finance")  # type: ignore[arg-type]


def test_resolve_domain_order(monkeypatch) -> None:
    from prismguard.runtime.factory import resolve_domain_pilot_domain

    monkeypatch.setenv("PRISMGUARD_DOMAIN", "healthcare")
    assert resolve_domain_pilot_domain("finance", requested_profile="domain_pilot") == "finance"
    assert resolve_domain_pilot_domain(None, requested_profile="domain_pilot") == "healthcare"
    # law_pilot alias ignores env — always law
    assert resolve_domain_pilot_domain(None, requested_profile="law_pilot") == "law"
    assert resolve_domain_pilot_domain("finance", requested_profile="law_pilot") == "law"


def test_caps_domain_pilot_taxonomy_when_prism_available(monkeypatch) -> None:
    from prismguard.runtime import capabilities as caps_mod
    from prismguard.taxonomy import mapping as mapping_mod

    monkeypatch.delenv("PRISMGUARD_OFFLINE", raising=False)
    monkeypatch.setenv("PRISMGUARD_DOMAIN", "finance")
    monkeypatch.setenv(
        "PRISMGUARD_ARTIFACT_ID",
        "prism-pi-finance-v1",
    )
    monkeypatch.setenv(
        "PRISMGUARD_GUARD_MODEL_PATH",
        r"C:\code\PrismGaurd\prismguard\models\artifacts\prism-pi-finance-v1",
    )
    # Force taxonomy status true path when prism is installed; skip if not.
    if not mapping_mod.has_prismrag():
        pytest.skip("prismrag-patch not installed")
    caps = caps_mod.guard_capabilities(profile="domain_pilot", probe_onnx=True)
    assert caps["profile"] == "domain_pilot"
    assert caps["domain_overlay"] == "finance"
    assert caps["prismrag_taxonomy"] is True


def test_caps_law_pilot_alias_note(monkeypatch) -> None:
    from prismguard.runtime.capabilities import guard_capabilities

    monkeypatch.setenv("PRISMGUARD_OFFLINE", "1")
    caps = guard_capabilities(profile="law_pilot", probe_onnx=False)
    assert caps["profile"] == "domain_pilot"
    assert caps["profile_requested"] == "law_pilot"
    assert caps["domain_overlay"] == "law"
    assert any("deprecated alias" in n for n in caps["notes"])


def test_custom_domain_scaffolds_and_builds(monkeypatch, tmp_path) -> None:
    from prismguard.domains.registry import get_domain_pack, normalize_domain_slug
    from prismguard.runtime.factory import create_checker_for_app

    monkeypatch.setenv("PRISMGUARD_DOMAIN_ROOT", str(tmp_path))
    slug = normalize_domain_slug("acme_claims")
    pack = get_domain_pack(slug, scaffold_if_missing=True)
    assert pack.overlay_path.is_file()
    assert pack.bundled is False
    checker = create_checker_for_app("domain_pilot", domain="acme_claims", use_onnx=False)
    assert checker.check("Hi").decision != "block"


def test_bundled_domains_remain_optional_shortcuts() -> None:
    from prismguard.domains.registry import is_bundled_domain, list_bundled_domains

    bundled = set(list_bundled_domains())
    assert "law" in bundled and "finance" in bundled
    assert is_bundled_domain("law") is True
    assert is_bundled_domain("acme_claims") is False


def test_finance_overlay_not_stub() -> None:
    from pathlib import Path

    import yaml

    path = Path(__file__).resolve().parents[1] / "prismguard" / "domains" / "finance" / "overlay.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    assert len(entries) >= 20
    attacks = [e for e in entries if e.get("category_slug") != "benign_adjacent"]
    benigns = [e for e in entries if e.get("category_slug") == "benign_adjacent"]
    assert len(attacks) >= 15
    assert len(benigns) >= 8
    blob = " ".join(e["text"].lower() for e in attacks)
    for needle in ("compliance", "bypass", "invent", "credentials", "waiver"):
        assert needle in blob
