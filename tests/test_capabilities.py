"""DX: capability truth table for hub vs scorecard vs learn-from-seed."""

from __future__ import annotations

import pytest


def test_ascii_safe_strips_arrows() -> None:
    from prismguard.runtime.capabilities import ascii_safe

    assert "->" in ascii_safe("export\u2192train")
    assert "-" in ascii_safe("ready\u2014now")
    # Must be encodable on Windows cp1252
    ascii_safe("HEAVY ONNX \u2014 max coverage; export\u2192train").encode("cp1252")


def test_format_capabilities_cp1252_safe() -> None:
    from prismguard.runtime.capabilities import format_capabilities, guard_capabilities

    text = format_capabilities(guard_capabilities(profile="light", probe_onnx=False))
    text.encode("cp1252")


def test_web_chat_caps_taxonomy_false() -> None:
    from prismguard.runtime.capabilities import guard_capabilities

    caps = guard_capabilities(profile="web_chat", probe_onnx=False)
    assert caps["profile"] == "web_chat"
    assert caps["prismrag_taxonomy"] is False
    assert caps["hash_only_profile"] is True
    assert caps["scorecard_path_ready"] is False


def test_security_bench_caps_warns_taxonomy_skipped() -> None:
    from prismguard.runtime.capabilities import guard_capabilities

    caps = guard_capabilities(profile="security_bench", probe_onnx=False)
    assert caps["prismrag_taxonomy"] is False
    assert caps["onnx_tier"] == "heavy"
    assert "skip_taxonomy" in caps["taxonomy_skip_reason"] or "HashEmbedder" in caps["taxonomy_skip_reason"]
    assert any("HEAVY" in n or "security_bench" in n for n in caps["notes"])


def test_law_pilot_taxonomy_depends_on_prism(monkeypatch) -> None:
    from prismguard.runtime import capabilities as caps_mod
    from prismguard.taxonomy import mapping as mapping_mod

    # Shell may have PRISMGUARD_DOMAIN=finance from local bake-offs — alias must stay law.
    monkeypatch.setenv("PRISMGUARD_DOMAIN", "finance")
    monkeypatch.setattr(mapping_mod, "has_prismrag", lambda: False)
    caps = caps_mod.guard_capabilities(profile="law_pilot", probe_onnx=False)
    assert caps["prismrag_taxonomy"] is False
    assert "[prism]" in caps["taxonomy_skip_reason"]
    assert caps["domain_overlay"] == "law"

    monkeypatch.setattr(mapping_mod, "has_prismrag", lambda: True)
    monkeypatch.delenv("PRISMGUARD_OFFLINE", raising=False)
    caps2 = caps_mod.guard_capabilities(profile="law_pilot", probe_onnx=False)
    assert caps2["prismrag_taxonomy"] is True
    assert caps2["domain_overlay"] == "law"


def test_feedback_and_storage_flags(monkeypatch) -> None:
    from prismguard.runtime.capabilities import guard_capabilities

    monkeypatch.setenv("PRISMGUARD_FEEDBACK_PERSIST", "1")
    monkeypatch.setenv("PRISMGUARD_STORAGE_BACKEND", "pgvector")
    caps = guard_capabilities(profile="law_pilot", probe_onnx=False)
    assert caps["feedback_persist"] is True
    assert caps["storage_persistent"] is True
    assert caps["storage_tier"] == "Team+"


def test_format_and_cli_caps(monkeypatch) -> None:
    from prismguard.app_cli import cmd_caps
    from prismguard.runtime.capabilities import format_capabilities, guard_capabilities

    caps = guard_capabilities(profile="web_chat", probe_onnx=False)
    text = format_capabilities(caps)
    assert "prismrag_taxonomy" in text
    assert "onnx_ready" in text

    class Args:
        profile = "web_chat"
        json = False

    assert cmd_caps(Args()) == 0


def test_cli_caps_law_pilot_without_onnx_nonzero(monkeypatch) -> None:
    from prismguard.app_cli import cmd_caps
    from prismguard.runtime import capabilities as caps_mod

    monkeypatch.setattr(
        caps_mod, "_onnx_artifact_ready", lambda **_kwargs: (False, "missing")
    )

    class Args:
        profile = "law_pilot"
        json = True

    # Re-import path: cmd_caps calls guard_capabilities which uses _onnx_artifact_ready
    assert cmd_caps(Args()) == 1
