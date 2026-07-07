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


def test_bundled_authored_loads_categories() -> None:
    parsed = load_bundled_seed(profile="authored")
    slugs = {c.slug for c in parsed.categories}
    assert "benign_adjacent" in slugs
    assert "unclassified_imported" in slugs
    assert len(slugs) == 11


def test_bundled_authored_has_rules_and_entries() -> None:
    parsed = load_bundled_seed(profile="authored")
    assert len(parsed.rules) >= 5
    assert len(parsed.entries) >= 28
    assert any(e.category_slug == "encoding_obfuscation" for e in parsed.entries)


def test_import_bundled_authored_into_memory() -> None:
    storage = create_storage("memory")
    try:
        first = import_bundled_seed(storage, mode="update", profile="authored")
        assert first.inserted >= 28

        second = import_bundled_seed(storage, mode="update", profile="authored")
        assert second.inserted == 0
        assert second.skipped >= 28
    finally:
        storage.close()


def test_bundled_full_profile_parses_external_rows() -> None:
    parsed = load_bundled_seed(profile="full")
    assert len(parsed.entries) > 15_000
    staging = [e for e in parsed.entries if e.category_slug == "unclassified_imported"]
    benign = [e for e in parsed.entries if e.category_slug == "benign_adjacent"]
    assert len(staging) > 7_000
    assert len(benign) > 5_000


def test_bundled_seed_dir_points_at_corpus() -> None:
    seed_dir = bundled_seed_dir()
    assert (CORPUS / "authored" / "seed.yaml").exists()
    assert (CORPUS / "manifest.txt").exists()
    assert seed_dir.name == "corpus" or (seed_dir / "authored" / "seed.yaml").exists()


def test_list_bundled_sources_full() -> None:
    sources = list_bundled_sources(profile="full")
    assert len(sources) == 5
    names = {p.name for p in sources}
    assert "seed.yaml" in names
    assert "train.csv" in names


def test_slabs_csv_parser() -> None:
    parsed = parse_seed_file(CORPUS / "external" / "s-labs" / "test.csv")
    assert len(parsed.entries) == 2101


def test_yanismiraoui_csv_parser() -> None:
    parsed = parse_seed_file(CORPUS / "external" / "yanismiraoui" / "prompt_injections.csv")
    assert len(parsed.entries) == 1034


def test_corpus_files_shipped_in_package() -> None:
    import importlib.resources as resources

    corpus = resources.files("prismguard.seed") / "corpus"
    assert (corpus / "authored" / "seed.yaml").is_file()
    assert (corpus / "external" / "s-labs" / "train.csv").is_file()


def test_bundled_seed_version_constant() -> None:
    assert BUNDLED_SEED_VERSION == "v0"
