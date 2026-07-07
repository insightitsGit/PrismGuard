from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelCard:
    model_id: str
    version: str
    architecture: str
    max_length: int
    injection_label: int
    base_model: str
    description: str = ""

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> ModelCard:
        return cls(
            model_id=str(data["model_id"]),
            version=str(data.get("version", "1")),
            architecture=str(data.get("architecture", "sequence_classification")),
            max_length=int(data.get("max_length", 512)),
            injection_label=int(data.get("injection_label", 1)),
            base_model=str(data.get("base_model", "")),
            description=str(data.get("description", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "architecture": self.architecture,
            "max_length": self.max_length,
            "injection_label": self.injection_label,
            "base_model": self.base_model,
            "description": self.description,
        }


def load_model_card(artifact_dir: Path) -> ModelCard:
    path = artifact_dir / "model_card.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Missing model card: {path}")
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected mapping in {path}, got {type(raw)!r}")
    return ModelCard.from_mapping(raw)


def write_model_card(artifact_dir: Path, card: ModelCard) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "model_card.yaml"
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(card.to_dict(), handle, sort_keys=False)
    return path
