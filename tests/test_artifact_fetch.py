"""Tests for ONNX artifact download (PyPI ships metadata only)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from prismguard.models import artifact_fetch


def test_sync_metadata_copies_model_card(tmp_path: Path) -> None:
    src = tmp_path / "packaged"
    dst = tmp_path / "cache"
    src.mkdir()
    (src / "model_card.yaml").write_text("model_id: test\n", encoding="utf-8")
    artifact_fetch.sync_metadata(src, dst)
    assert (dst / "model_card.yaml").read_text(encoding="utf-8") == "model_id: test\n"


def test_ensure_artifact_ready_uses_packaged_when_onnx_present(tmp_path: Path) -> None:
    packaged = tmp_path / "prism-pi-v1"
    packaged.mkdir()
    (packaged / "model.onnx").write_bytes(b"onnx")
    (packaged / "model_card.yaml").write_text("model_id: prism-pi-v1\n", encoding="utf-8")

    with patch.object(artifact_fetch, "packaged_artifact_dir", return_value=packaged):
        resolved = artifact_fetch.ensure_artifact_ready("prism-pi-v1", auto_download=False)
    assert resolved == packaged


def test_download_artifact_writes_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packaged = tmp_path / "packaged" / "prism-pi-v1"
    packaged.mkdir(parents=True)
    (packaged / "model_card.yaml").write_text("model_id: prism-pi-v1\n", encoding="utf-8")
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PRISMGUARD_ARTIFACT_CACHE", str(cache_root))

    payload = b"fake-onnx-bytes"
    spec = {
        "url": "https://example.test/model.onnx",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }

    with (
        patch.object(artifact_fetch, "packaged_artifact_dir", return_value=packaged),
        patch.dict(artifact_fetch.ARTIFACT_DOWNLOADS, {"prism-pi-v1": {"model.onnx": spec}}),
        patch.object(artifact_fetch, "download_file") as mock_download,
    ):
        out = artifact_fetch.download_artifact("prism-pi-v1", progress=False)

    mock_download.assert_called_once()
    assert out == cache_root / "prism-pi-v1"
    assert (out / "model_card.yaml").is_file()


def test_ensure_artifact_without_download_raises(tmp_path: Path) -> None:
    packaged = tmp_path / "packaged" / "prism-pi-v1"
    packaged.mkdir(parents=True)
    (packaged / "model_card.yaml").write_text("model_id: prism-pi-v1\n", encoding="utf-8")
    cache = tmp_path / "cache" / "prism-pi-v1"
    cache.mkdir(parents=True)

    with (
        patch.object(artifact_fetch, "packaged_artifact_dir", return_value=packaged),
        patch.object(artifact_fetch, "cache_artifact_dir", return_value=cache),
    ):
        with pytest.raises(FileNotFoundError, match="prismguard-model download"):
            artifact_fetch.ensure_artifact_ready("prism-pi-v1", auto_download=False)
