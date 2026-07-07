from pathlib import Path

import pytest

from prismguard.seed import (
    BUNDLED_SEED_VERSION,
    bundled_seed_dir,
    import_bundled_seed,
    list_bundled_sources,
    load_bundled_seed,
)
from prismguard.seed.parse import parse_seed_file
from prismguard.storage import create_storage

CORPUS = Path(__file__).resolve().parents[1] / "prismguard" / "seed" / "corpus"
GAP_CATEGORIES = (
    "payload_splitting",
    "data_exfiltration_via_output",
    "refusal_suppression",
    "context_overflow",
)


def test_bundled_authored_loads_categories() -> None:
    parsed = load_bundled_seed(profile="authored")
    slugs = {c.slug for c in parsed.categories}
    assert "benign_adjacent" in slugs
    assert "context_overflow" in slugs
    assert "unclassified_imported" in slugs
    assert len(slugs) == 12


def test_bundled_authored_has_gap_category_examples() -> None:
    parsed = load_bundled_seed(profile="authored")
    by_cat = {slug: [e for e in parsed.entries if e.category_slug == slug] for slug in GAP_CATEGORIES}
    assert len(by_cat["payload_splitting"]) >= 4
    assert len(by_cat["data_exfiltration_via_output"]) >= 5
    assert len(by_cat["refusal_suppression"]) >= 9
    assert any(e.turns for e in by_cat["payload_splitting"])


def test_seven_mined_slabs_refusal_entries_with_provenance() -> None:
    parsed = load_bundled_seed(profile="authored")
    mined = [e for e in parsed.entries if e.source == "mined-slabs"]
    assert len(mined) == 7
    assert all(e.category_slug == "refusal_suppression" for e in mined)
    assert any(e.secondary_category_slugs for e in mined)


def test_turns_entries_import_with_canonical_hash() -> None:
    pytest.importorskip("prismrag_patch")
    storage = create_storage("memory")
    try:
        parsed = load_bundled_seed(profile="authored")
        turns_entries = [e for e in parsed.entries if e.turns]
        assert len(turns_entries) >= 2
        report = import_bundled_seed(storage, mode="update", profile="authored")
        assert report.inserted >= 40
        stored = storage.vector.list_seed_entries_by_category("payload_splitting")
        assert any("---TURN---" in row.raw_text for row in stored)
    finally:
        storage.close()


def test_data_exfil_category_documents_output_scan_requirement() -> None:
    parsed = load_bundled_seed(profile="authored")
    cat = next(c for c in parsed.categories if c.slug == "data_exfiltration_via_output")
    assert "OUTPUT-side" in cat.description
    assert "output hook" in cat.description


def test_import_bundled_authored_into_memory() -> None:
    pytest.importorskip("prismrag_patch")
    storage = create_storage("memory")
    try:
        first = import_bundled_seed(storage, mode="update", profile="authored")
        assert first.inserted >= 35
        assert first.taxonomy is not None
        assert first.taxonomy.ingest.embedded >= 35

        second = import_bundled_seed(storage, mode="update", profile="authored")
        assert second.inserted == 0
        assert second.skipped >= 35
        assert second.taxonomy is not None
        assert second.taxonomy.ingest.embedded == 0
    finally:
        storage.close()


def test_bundled_full_profile_covers_gap_categories() -> None:
    parsed = load_bundled_seed(profile="full")
    assert len(parsed.entries) > 20_000
    for slug in GAP_CATEGORIES:
        count = sum(1 for e in parsed.entries if e.category_slug == slug)
        assert count > 0, f"expected seed rows for {slug}, got {count}"


def test_bundled_full_neuralchemy_context_overflow() -> None:
    parsed = load_bundled_seed(profile="full")
    overflow = [e for e in parsed.entries if e.category_slug == "context_overflow"]
    assert len(overflow) >= 20
    assert all("neuralchemy" in e.source for e in overflow)


def test_bundled_full_data_exfil_from_neuralchemy_and_slabs() -> None:
    parsed = load_bundled_seed(profile="full")
    exfil = [e for e in parsed.entries if e.category_slug == "data_exfiltration_via_output"]
    sources = {e.source for e in exfil}
    assert any("neuralchemy" in s for s in sources)
    assert any("s-labs" in s for s in sources)


def test_bundled_full_refusal_suppression_from_slabs_heuristic() -> None:
    parsed = load_bundled_seed(profile="full")
    refusal = [e for e in parsed.entries if e.category_slug == "refusal_suppression"]
    assert len(refusal) >= 10
    assert any("s-labs" in e.source for e in refusal)


def test_list_bundled_sources_full() -> None:
    sources = list_bundled_sources(profile="full")
    assert len(sources) == 8
    assert any(p.suffix == ".parquet" for p in sources)


def test_neuralchemy_parquet_parser() -> None:
    parsed = parse_seed_file(CORPUS / "external" / "neuralchemy" / "core-test.parquet")
    assert len(parsed.entries) == 942
    assert any(e.category_slug == "context_overflow" for e in parsed.entries)
    assert any(e.category_slug == "data_exfiltration_via_output" for e in parsed.entries)


def test_slabs_heuristic_labels_refusal() -> None:
    parsed = parse_seed_file(CORPUS / "external" / "s-labs" / "test.csv")
    refusal = [e for e in parsed.entries if e.category_slug == "refusal_suppression"]
    assert len(refusal) >= 1


def test_corpus_files_shipped_in_package() -> None:
    import importlib.resources as resources

    corpus = resources.files("prismguard.seed") / "corpus"
    assert (corpus / "authored" / "seed.yaml").is_file()
    assert (corpus / "external" / "neuralchemy" / "core-train.parquet").is_file()


def test_bundled_seed_version_constant() -> None:
    assert BUNDLED_SEED_VERSION == "v0"
