"""Download large ONNX artifacts outside the PyPI wheel."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path

DEFAULT_ARTIFACT_ID = "prism-pi-v1"

METADATA_FILES = (
    "model_card.yaml",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "added_tokens.json",
    "spm.model",
    "calibration.json",
    "corpus_manifest.json",
    "train_metrics.json",
)

# PyPI wheels ship metadata only; model.onnx is fetched on first use.
#
# Optional starter defaults (law / finance / healthcare): convenience for users
# without their own labeled DB. They do NOT guarantee accuracy on customer traffic.
# Prefer: train on your feedback → domain_pilot + prism-pi-<your-slug>-v1.
#
# Release assets for finance/healthcare: tag v0.1.10+ (upload via scripts/publish_default_artifacts.md).
ARTIFACT_DOWNLOADS: dict[str, dict[str, dict[str, str | int]]] = {
    "prism-pi-v1": {
        "model.onnx": {
            "url": os.environ.get(
                "PRISMGUARD_MODEL_DOWNLOAD_URL",
                "https://github.com/insightitsGit/PrismGuard/releases/download/v0.1.2/prism-pi-v1-model.onnx",
            ),
            "sha256": "02e1531e3399c28daffa1a3e67da1b6b6dbd25f3628df16c9b2ab1345d4dd73d",
            "size_bytes": 738_656_170,
        }
    },
    "prism-pi-finance-v1": {
        "model.onnx": {
            "url": os.environ.get(
                "PRISMGUARD_FINANCE_MODEL_DOWNLOAD_URL",
                "https://github.com/insightitsGit/PrismGuard/releases/download/v0.1.10/prism-pi-finance-v1-model.onnx",
            ),
            "sha256": os.environ.get(
                "PRISMGUARD_FINANCE_MODEL_SHA256",
                "1ade911b48e8e44e53bd76219fe78ead40aa6d342697cbdaad1d8942904d1260",
            ),
            "size_bytes": 738_656_170,
        }
    },
    "prism-pi-healthcare-v1": {
        "model.onnx": {
            "url": os.environ.get(
                "PRISMGUARD_HEALTHCARE_MODEL_DOWNLOAD_URL",
                "https://github.com/insightitsGit/PrismGuard/releases/download/v0.1.10/prism-pi-healthcare-v1-model.onnx",
            ),
            "sha256": os.environ.get(
                "PRISMGUARD_HEALTHCARE_MODEL_SHA256",
                "0928e3b7917db70cbfcde5d075063bfc66a47aa895c0115ca094ded87795cab7",
            ),
            "size_bytes": 738_656_170,
        }
    },
}


def default_cache_root() -> Path:
    env = os.environ.get("PRISMGUARD_ARTIFACT_CACHE", "").strip()
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg:
        return Path(xdg) / "prismguard" / "artifacts"
    return Path.home() / ".cache" / "prismguard" / "artifacts"


def packaged_artifact_dir(artifact_id: str) -> Path:
    return Path(resources.files("prismguard.models") / "artifacts" / artifact_id)


def cache_artifact_dir(artifact_id: str) -> Path:
    return default_cache_root() / artifact_id


def sync_metadata(from_dir: Path, to_dir: Path) -> None:
    to_dir.mkdir(parents=True, exist_ok=True)
    for name in METADATA_FILES:
        src = from_dir / name
        if not src.is_file():
            continue
        dst = to_dir / name
        if not dst.is_file() or src.stat().st_mtime_ns > dst.stat().st_mtime_ns:
            shutil.copy2(src, dst)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _format_bytes(num: int) -> str:
    if num >= 1024 * 1024 * 1024:
        return f"{num / (1024 * 1024 * 1024):.1f} GB"
    if num >= 1024 * 1024:
        return f"{num / (1024 * 1024):.1f} MB"
    if num >= 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num} B"


def download_file(
    url: str,
    dest: Path,
    *,
    expected_sha256: str = "",
    expected_size: int = 0,
    progress: bool = True,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    if tmp.is_file():
        tmp.unlink()

    request = urllib.request.Request(url, headers={"User-Agent": "prismguard-artifact-fetch/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length") or expected_size or 0)
            downloaded = 0
            with tmp.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if progress and total > 0:
                        pct = min(100, downloaded * 100 // total)
                        bar = "=" * (pct // 2)
                        sys.stderr.write(
                            f"\rDownloading {dest.name}: [{bar:<50}] {pct:3d}% "
                            f"({_format_bytes(downloaded)}/{_format_bytes(total)})"
                        )
                        sys.stderr.flush()
            if progress and total > 0:
                sys.stderr.write("\n")
    except urllib.error.HTTPError as exc:
        raise FileNotFoundError(
            f"Failed to download {dest.name} from {url} (HTTP {exc.code}). "
            "Create the GitHub release asset or set PRISMGUARD_MODEL_DOWNLOAD_URL."
        ) from exc
    except urllib.error.URLError as exc:
        raise FileNotFoundError(
            f"Failed to download {dest.name} from {url}: {exc.reason}. "
            "Check network access or set PRISMGUARD_MODEL_DOWNLOAD_URL."
        ) from exc

    if expected_size:
        actual_size = tmp.stat().st_size
        if actual_size != expected_size:
            tmp.unlink(missing_ok=True)
            raise ValueError(
                f"Downloaded {dest.name} size mismatch: got {actual_size}, expected {expected_size}"
            )

    if expected_sha256:
        actual = _sha256_file(tmp)
        if actual != expected_sha256.lower():
            tmp.unlink(missing_ok=True)
            raise ValueError(f"Downloaded {dest.name} checksum mismatch.")

    tmp.replace(dest)


def download_artifact(artifact_id: str = DEFAULT_ARTIFACT_ID, *, progress: bool = True) -> Path:
    packaged = packaged_artifact_dir(artifact_id)
    cache = cache_artifact_dir(artifact_id)
    if packaged.is_dir():
        sync_metadata(packaged, cache)

    spec = ARTIFACT_DOWNLOADS.get(artifact_id, {}).get("model.onnx")
    if spec is None:
        # Custom / customer-trained ids are not downloadable starters.
        local = packaged if packaged.is_dir() else cache
        if (local / "model.onnx").is_file():
            return local
        raise FileNotFoundError(
            f"No download spec for artifact {artifact_id!r}. "
            "Custom artifacts: train locally "
            "(`prismguard-model train --artifact-id …`) and set "
            "PRISMGUARD_GUARD_MODEL_PATH / PRISMGUARD_ARTIFACT_ID. "
            "Starter list: prismguard-model download --list"
        )

    dest = cache / "model.onnx"
    expected_sha = str(spec.get("sha256", "") or "").lower()
    if dest.is_file() and expected_sha:
        if _sha256_file(dest) == expected_sha:
            return cache

    if not str(spec.get("url", "")).strip():
        raise FileNotFoundError(
            f"Download URL not configured for {artifact_id!r}. "
            "Train locally or set PRISMGUARD_*_MODEL_DOWNLOAD_URL."
        )

    if progress:
        sys.stderr.write(
            f"Fetching {artifact_id} ONNX model (~{_format_bytes(int(spec.get('size_bytes', 0)))}) "
            f"to {cache}\n"
            "Note: starter defaults do NOT guarantee accuracy on your traffic.\n"
        )
    download_file(
        str(spec["url"]),
        dest,
        expected_sha256=expected_sha,
        expected_size=int(spec.get("size_bytes", 0) or 0),
        progress=progress,
    )
    return cache


def ensure_artifact_ready(
    artifact_id: str = DEFAULT_ARTIFACT_ID,
    *,
    auto_download: bool = True,
    progress: bool = False,
) -> Path:
    packaged = packaged_artifact_dir(artifact_id)
    cache = cache_artifact_dir(artifact_id)

    if packaged.is_dir() and (packaged / "model.onnx").is_file():
        return packaged

    if (cache / "model.onnx").is_file():
        if packaged.is_dir():
            sync_metadata(packaged, cache)
        return cache

    # Starter downloads only when we have a registered URL/sha.
    if artifact_id not in ARTIFACT_DOWNLOADS and not packaged.is_dir():
        raise FileNotFoundError(
            f"Unknown artifact id {artifact_id!r}. "
            "Train with `prismguard-model train --artifact-id …` or set "
            "PRISMGUARD_GUARD_MODEL_PATH. Starters: prismguard-model download --list"
        )

    if not auto_download:
        raise FileNotFoundError(
            f"ONNX model not found for {artifact_id!r}. "
            "Run: prismguard-model download"
        )

    return download_artifact(artifact_id, progress=progress)
