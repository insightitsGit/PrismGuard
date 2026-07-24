from __future__ import annotations

import json
import os
from importlib import resources
from pathlib import Path

from prismguard.config.loader import GuardModelConfig
from prismguard.models.artifact_fetch import ensure_artifact_ready
from prismguard.models.model_card import load_model_card


def default_artifacts_root() -> Path:
    return Path(resources.files("prismguard.models") / "artifacts")


def resolve_artifact_dir(config: GuardModelConfig) -> Path:
    """Resolve ONNX artifact directory for the configured id — never swap domains.

    Silent fallback to ``prism-pi-v1`` (law) when another artifact is missing is
    forbidden: that mis-calibrates finance/healthcare/custom traffic.
    """
    if config.artifact_path:
        return Path(config.artifact_path).expanduser().resolve()
    env_path = os.environ.get("PRISMGUARD_GUARD_MODEL_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    artifact_id = (config.artifact_id or "").strip() or "prism-pi-v1"
    try:
        return ensure_artifact_ready(artifact_id, auto_download=True, progress=False)
    except FileNotFoundError:
        candidate = default_artifacts_root() / artifact_id
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(
            f"ONNX artifact {artifact_id!r} not found under "
            f"{default_artifacts_root()} or the download cache. "
            "Train with `prismguard-model train --artifact-id …` or set "
            "PRISMGUARD_GUARD_MODEL_PATH. Refusing to silently load prism-pi-v1 "
            "for a different domain."
        ) from None


def load_corpus_manifest(artifact_dir: Path) -> dict | None:
    path = artifact_dir / "corpus_manifest.json"
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def load_onnx_classifier(config: GuardModelConfig):
    from prismguard.models.onnx_classifier import get_or_load_classifier

    artifact_dir = resolve_artifact_dir(config)
    card = load_model_card(artifact_dir)
    return get_or_load_classifier(
        artifact_dir,
        card=card,
        uncertain_low=config.uncertain_low,
        uncertain_high=config.uncertain_high,
    )
