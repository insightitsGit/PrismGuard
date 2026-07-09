"""Probability calibration for Guard Model artifacts (temperature scaling)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prismguard.models.deps import require_numpy


@dataclass(frozen=True)
class CalibrationArtifact:
    temperature: float
    domain: str = ""
    fitted_at: str = ""
    holdout_block_rate: float | None = None
    normal_allow_rate: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationArtifact:
        return cls(
            temperature=float(data.get("temperature", 1.0)),
            domain=str(data.get("domain", "")),
            fitted_at=str(data.get("fitted_at", "")),
            holdout_block_rate=data.get("holdout_block_rate"),
            normal_allow_rate=data.get("normal_allow_rate"),
        )


def apply_temperature(logits: Any, temperature: float) -> Any:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    if abs(temperature - 1.0) < 1e-6:
        return logits
    return logits / temperature


def fit_temperature(
    logits: Any,
    labels: Any,
    *,
    temperature_grid: list[float] | None = None,
) -> float:
    """Grid-search temperature minimizing binary cross-entropy on labeled rows."""
    np = require_numpy()
    if logits.ndim != 2 or logits.shape[1] != 2:
        raise ValueError("logits must be (n, 2)")
    labels = labels.astype(int)
    temperature_grid = temperature_grid or [
        0.5,
        0.75,
        1.0,
        1.25,
        1.5,
        1.75,
        2.0,
        2.5,
        3.0,
    ]
    best_t = 1.0
    best_loss = float("inf")
    for temp in temperature_grid:
        scaled = apply_temperature(logits, temp)
        shifted = scaled - scaled.max(axis=1, keepdims=True)
        exp = np.exp(shifted)
        probs = exp / exp.sum(axis=1, keepdims=True)
        inj_prob = probs[:, 1]
        loss = -np.mean(
            labels * np.log(inj_prob + 1e-12) + (1 - labels) * np.log(1 - inj_prob + 1e-12)
        )
        if loss < best_loss:
            best_loss = loss
            best_t = temp
    return float(best_t)


def load_calibration(artifact_dir: Path) -> CalibrationArtifact | None:
    path = artifact_dir / "calibration.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return CalibrationArtifact.from_dict(data)


def write_calibration(artifact_dir: Path, calibration: CalibrationArtifact) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "calibration.json"
    payload = calibration.to_dict()
    if not payload.get("fitted_at"):
        payload["fitted_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
