"""Bundled seed corpus shipped inside the prismguard package."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from prismguard.seed.importer import ImportMode, ImportReport, import_seeds
from prismguard.seed.models import ParsedSeed
from prismguard.seed.parse import parse_seed_sources
from prismguard.storage.protocols import StorageBackend

BUNDLED_SEED_VERSION = "v0"


def _seed_resource_dir(version: str) -> resources.abc.Traversable:
    return resources.files("prismguard.data") / "seeds" / version


def bundled_seed_dir(version: str = BUNDLED_SEED_VERSION) -> Path:
    """
    Return path to bundled seed files.

    When called outside an `as_file` context on zipped installs, prefer
    `load_bundled_seed()` / `import_bundled_seed()` which handle extraction safely.
    """
    ref = _seed_resource_dir(version)
    return Path(str(ref))


def bundled_seed_sources(version: str = BUNDLED_SEED_VERSION) -> list[Path]:
    """Resolved paths for taxonomy + entries (+ manifest-driven extras)."""
    with resources.as_file(_seed_resource_dir(version)) as seed_dir:
        manifest = seed_dir / "manifest.txt"
        if manifest.is_file():
            from prismguard.seed.parse import _read_manifest

            return _read_manifest(manifest)
        return [seed_dir / "taxonomy.yaml", seed_dir / "entries.yaml"]


def load_bundled_seed(version: str = BUNDLED_SEED_VERSION) -> ParsedSeed:
    """Parse the bundled seed corpus without writing to storage."""
    with resources.as_file(_seed_resource_dir(version)) as seed_dir:
        manifest = seed_dir / "manifest.txt"
        if manifest.is_file():
            return parse_seed_sources([f"@{manifest}"])
        return parse_seed_sources([seed_dir / "taxonomy.yaml", seed_dir / "entries.yaml"])


def import_bundled_seed(
    storage: StorageBackend,
    *,
    mode: ImportMode = "update",
    scope: str = "all",
    dry_run: bool = False,
    confirm_replace_all: bool = False,
    version: str = BUNDLED_SEED_VERSION,
) -> ImportReport:
    """Import the bundled v0 seed into the given storage backend."""
    parsed = load_bundled_seed(version=version)
    return import_seeds(
        storage,
        parsed,
        mode=mode,
        scope=scope,
        dry_run=dry_run,
        confirm_replace_all=confirm_replace_all,
    )
