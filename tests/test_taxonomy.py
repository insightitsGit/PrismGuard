import pytest

from prismguard.runtime.check import RuntimeChecker
from prismguard.seed import import_bundled_seed, load_bundled_seed
from prismguard.storage import create_storage
from prismguard.taxonomy.embedder import HashEmbedder
from prismguard.taxonomy.mapping import build_mapping_from_parsed_seed
from prismguard.taxonomy.pipeline import run_post_seed_pipeline

prismrag = pytest.importorskip("prismrag_patch")


def test_mapping_assigns_direct_override_category() -> None:
    parsed = load_bundled_seed(profile="authored")
    engine = build_mapping_from_parsed_seed(parsed)
    sample = next(e for e in parsed.entries if e.category_slug == "direct_instruction_override")
    tier1 = engine.match_tier1(sample.canonical_text().lower())
    assert tier1 is not None
    assert tier1.category_slug == "direct_instruction_override"


def test_post_seed_pipeline_embeds_all_authored_entries() -> None:
    storage = create_storage("memory")
    try:
        parsed = load_bundled_seed(profile="authored")
        report = import_bundled_seed(storage, profile="authored")
        assert report.taxonomy is not None
        assert report.taxonomy.ingest.embedded > 0
        assert report.taxonomy.coverage.unembedded_entries == 0
        assert report.taxonomy.coverage.uncovered_attack_categories == []
        assert report.taxonomy.llm_reduction["llm_judge_pct"] < 5.0
    finally:
        storage.close()


def test_runtime_checker_blocks_tier1_override() -> None:
    storage = create_storage("memory")
    try:
        parsed = load_bundled_seed(profile="authored")
        import_bundled_seed(storage, profile="authored")
        checker = RuntimeChecker.from_storage(storage, parsed, embedder=HashEmbedder())
        override = next(e for e in parsed.entries if e.category_slug == "direct_instruction_override")
        result = checker.check(override.canonical_text())
        assert result.decision in ("block", "gray")
        assert result.resolution_gate in ("tier1_rule", "corpus_match", "fusion_block")
    finally:
        storage.close()


def test_runtime_checker_allows_benign_research_framing() -> None:
    storage = create_storage("memory")
    try:
        parsed = load_bundled_seed(profile="authored")
        import_bundled_seed(storage, profile="authored")
        checker = RuntimeChecker.from_storage(storage, parsed, embedder=HashEmbedder())
        benign = next(e for e in parsed.entries if e.category_slug == "benign_adjacent")
        result = checker.check(benign.canonical_text())
        assert result.decision == "allow"
        assert result.resolution_gate in ("benign_fast_path", "fusion_allow", "structural")
    finally:
        storage.close()


def test_ingest_idempotent_without_force() -> None:
    storage = create_storage("memory")
    try:
        first = import_bundled_seed(storage, profile="authored")
        second = import_bundled_seed(storage, profile="authored")
        assert first.taxonomy is not None
        assert first.taxonomy.ingest.embedded > 0
        assert second.taxonomy is not None
        assert second.taxonomy.ingest.embedded == 0
        assert second.taxonomy.ingest.skipped_already_embedded == first.taxonomy.ingest.embedded
    finally:
        storage.close()
