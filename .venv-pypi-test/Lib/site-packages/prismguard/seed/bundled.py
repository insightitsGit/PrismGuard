"""Bundled seed corpus shipped inside the prismguard package."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Literal

from prismguard.seed.importer import ImportMode, ImportReport, import_seeds
from prismguard.seed.models import ParsedSeed
from prismguard.seed.parse import parse_seed_sources
from prismguard.storage.protocols import StorageBackend

BUNDLED_SEED_VERSION = "v0"
BundledProfile = Literal["authored", "full"]

_PROFILE_MANIFESTS: dict[BundledProfile, str] = {
    "authored": "manifest.authored.txt",
    "full": "manifest.txt",
}


def _corpus_root() -> resources.abc.Traversable:
    return resources.files("prismguard.seed") / "corpus"


def bundled_seed_dir(version: str = BUNDLED_SEED_VERSION) -> Path:
    """Path to the packaged seed corpus directory."""
    ref = _corpus_root() / version if version != "v0" else _corpus_root()
    return Path(str(ref))


def _manifest_path(profile: BundledProfile) -> resources.abc.Traversable:
    return _corpus_root() / _PROFILE_MANIFESTS[profile]


def load_bundled_seed(profile: BundledProfile = "authored") -> ParsedSeed:
    """Parse the bundled seed corpus without writing to storage."""
    with resources.as_file(_corpus_root()) as corpus_dir:
        manifest = corpus_dir / _PROFILE_MANIFESTS[profile]
        return parse_seed_sources([f"@{manifest}"])


def import_bundled_seed(
    storage: StorageBackend,
    *,
    mode: ImportMode = "update",
    scope: str = "all",
    dry_run: bool = False,
    confirm_replace_all: bool = False,
    profile: BundledProfile = "authored",
    skip_taxonomy: bool = False,
    force_embed: bool = False,
) -> ImportReport:
    """Import the packaged seed corpus (authored-only or full with external datasets)."""
    parsed = load_bundled_seed(profile=profile)
    return import_seeds(
        storage,
        parsed,
        mode=mode,
        scope=scope,
        dry_run=dry_run,
        confirm_replace_all=confirm_replace_all,
        skip_taxonomy=skip_taxonomy,
        force_embed=force_embed,
    )


def list_bundled_sources(profile: BundledProfile = "authored") -> list[Path]:
    """Resolved paths included in a bundled profile."""
    with resources.as_file(_corpus_root()) as corpus_dir:
        from prismguard.seed.parse import _read_manifest

        manifest = corpus_dir / _PROFILE_MANIFESTS[profile]
        return _read_manifest(manifest)
