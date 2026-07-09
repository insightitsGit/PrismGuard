"""Tests for verdict cache and ingest salience."""

from __future__ import annotations

import os

from prismguard.runtime.verdict_cache import VerdictCache, content_address
from prismguard.runtime.check import CheckResult
from prismguard.seed.salience import should_skip_benign_ingest
from prismguard.storage.memory import new_seed_entry
from prismguard.storage.types import SeedEntryRecord


def test_content_address_stable() -> None:
    a = content_address(
        normalized_prompt="hello world",
        artifact_id="prism-pi-v1",
        classifier_mode="first",
        rule_version="abc",
        structural_threshold=0.75,
        veto_threshold=0.82,
    )
    b = content_address(
        normalized_prompt="hello   world",
        artifact_id="prism-pi-v1",
        classifier_mode="first",
        rule_version="abc",
        structural_threshold=0.75,
        veto_threshold=0.82,
    )
    assert a == b


def test_verdict_cache_roundtrip() -> None:
    cache = VerdictCache(ttl_seconds=60)
    key = "test-key"
    result = CheckResult(
        decision="block",
        resolution_gate="tier1_rule",
        matched_category="direct_instruction_override",
        normalized_prompt="x",
        details={"foo": 1},
    )
    cache.put(key, result)
    hit = cache.get(key)
    assert hit is not None
    assert hit.decision == "block"
    assert hit.details.get("verdict_cache_hit") is True


def test_should_skip_duplicate_benign() -> None:
    existing = {"what is the standard notice period for a mutual nda"}
    entry = SeedEntryRecord(
        id="1",
        raw_text="What is the standard notice period for a mutual NDA?",
        chunk_text="what is the standard notice period for a mutual nda",
        embedding_semantic=[],
        embedding_category=[],
        category_slug="benign_adjacent",
        severity="low",
        source="test",
    )
    assert should_skip_benign_ingest(entry, existing_benign=existing) is True


def test_verdict_cache_env_gate(monkeypatch) -> None:
    from prismguard.runtime import verdict_cache

    verdict_cache._global_cache = None
    monkeypatch.delenv("PRISMGUARD_VERDICT_CACHE", raising=False)
    assert verdict_cache.get_verdict_cache() is None
    monkeypatch.setenv("PRISMGUARD_VERDICT_CACHE", "1")
    assert verdict_cache.get_verdict_cache() is not None
    verdict_cache._global_cache = None
