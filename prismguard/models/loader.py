from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

from prismguard.config.loader import GuardModelConfig
from prismguard.models.model_card import load_model_card
from prismguard.models.onnx_classifier import ONNXPromptInjectionClassifier


def default_artifacts_root() -> Path:
    return Path(resources.files("prismguard.models") / "artifacts")


def resolve_artifact_dir(config: GuardModelConfig) -> Path:
    if config.artifact_path:
        return Path(config.artifact_path).expanduser().resolve()
    env_path = os.environ.get("PRISMGUARD_GUARD_MODEL_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    return default_artifacts_root() / config.artifact_id


def load_onnx_classifier(config: GuardModelConfig) -> ONNXPromptInjectionClassifier:
    artifact_dir = resolve_artifact_dir(config)
    card = load_model_card(artifact_dir)
    return ONNXPromptInjectionClassifier.from_artifact_dir(
        artifact_dir,
        card=card,
        uncertain_low=config.uncertain_low,
        uncertain_high=config.uncertain_high,
    )
