from prismguard.data import BUNDLED_SEED_VERSION, bundled_seed_dir, import_bundled_seed, load_bundled_seed
from prismguard.storage import create_storage


def test_bundled_seed_loads_all_categories() -> None:
    parsed = load_bundled_seed()
    slugs = {c.slug for c in parsed.categories}
    assert len(slugs) == 10
    assert "benign_adjacent" in slugs
    assert "direct_instruction_override" in slugs


def test_bundled_seed_has_rules_and_entries() -> None:
    parsed = load_bundled_seed()
    assert len(parsed.rules) >= 6
    assert len(parsed.entries) >= 40
    benign = [e for e in parsed.entries if e.category_slug == "benign_adjacent"]
    assert len(benign) >= 5


def test_import_bundled_seed_into_memory() -> None:
    storage = create_storage("memory")
    try:
        first = import_bundled_seed(storage, mode="update")
        assert first.inserted >= 40
        assert first.updated == 0

        categories = storage.relational.list_categories()
        assert len(categories) == 10
        benign = storage.relational.get_category("benign_adjacent")
        assert benign is not None
        assert benign.is_attack_category is False

        second = import_bundled_seed(storage, mode="update")
        assert second.inserted == 0
        assert second.skipped >= 40
    finally:
        storage.close()


def test_bundled_seed_dir_exists() -> None:
    seed_dir = bundled_seed_dir()
    assert (seed_dir / "taxonomy.yaml").is_file()
    assert (seed_dir / "entries.yaml").is_file()
    assert (seed_dir / "manifest.txt").is_file()


def test_bundled_seed_version_constant() -> None:
    assert BUNDLED_SEED_VERSION == "v0"
