from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from prismguard.models.calibration import apply_temperature, load_calibration
from prismguard.models.model_card import ModelCard
from prismguard.models.verdict import injection_probability_to_decision


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


@dataclass
class ClassifierPrediction:
    injection_probability: float
    decision: str
    latency_ms: float
    details: dict[str, Any] = field(default_factory=dict)


class ONNXPromptInjectionClassifier:
    """Local ONNX sequence classifier for prompt-injection detection."""

    def __init__(
        self,
        *,
        artifact_dir: Path,
        card: ModelCard,
        session: Any,
        tokenizer: Any,
        uncertain_low: float,
        uncertain_high: float,
    ) -> None:
        self._artifact_dir = artifact_dir
        self._card = card
        self._session = session
        self._tokenizer = tokenizer
        self._uncertain_low = uncertain_low
        self._uncertain_high = uncertain_high
        calibration = load_calibration(artifact_dir)
        self._temperature = calibration.temperature if calibration else card.calibration_temperature

    @property
    def model_id(self) -> str:
        return self._card.model_id

    @property
    def is_ready(self) -> bool:
        return self._session is not None and self._tokenizer is not None

    @classmethod
    def from_artifact_dir(
        cls,
        artifact_dir: Path,
        *,
        card: ModelCard,
        uncertain_low: float,
        uncertain_high: float,
    ) -> ONNXPromptInjectionClassifier:
        onnx_path = artifact_dir / "model.onnx"
        tokenizer_path = artifact_dir / "tokenizer.json"
        if not onnx_path.is_file():
            raise FileNotFoundError(
                f"ONNX model not found at {onnx_path}. "
                "Run: python -m prismguard.models.export --artifact-id prism-pi-v1"
            )
        if not tokenizer_path.is_file():
            raise FileNotFoundError(
                f"Tokenizer not found at {tokenizer_path}. "
                "Run: python -m prismguard.models.export --artifact-id prism-pi-v1"
            )

        import onnxruntime as ort
        from tokenizers import Tokenizer

        session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        return cls(
            artifact_dir=artifact_dir,
            card=card,
            session=session,
            tokenizer=tokenizer,
            uncertain_low=uncertain_low,
            uncertain_high=uncertain_high,
        )

    def _encode(self, text: str) -> tuple[np.ndarray, np.ndarray]:
        encoding = self._tokenizer.encode(text)
        input_ids = encoding.ids[: self._card.max_length]
        attention_mask = [1] * len(input_ids)
        pad_len = self._card.max_length - len(input_ids)
        if pad_len > 0:
            input_ids = input_ids + [0] * pad_len
            attention_mask = attention_mask + [0] * pad_len
        ids = np.array([input_ids], dtype=np.int64)
        mask = np.array([attention_mask], dtype=np.int64)
        return ids, mask

    def predict(self, text: str) -> ClassifierPrediction:
        start = time.perf_counter()
        input_ids, attention_mask = self._encode(text)
        outputs = self._session.run(
            None,
            {"input_ids": input_ids, "attention_mask": attention_mask},
        )
        logits = np.asarray(outputs[0], dtype=np.float64)
        logits = apply_temperature(logits, self._temperature)
        probs = _softmax(logits)[0]
        injection_probability = float(probs[self._card.injection_label])
        decision = injection_probability_to_decision(
            injection_probability,
            uncertain_low=self._uncertain_low,
            uncertain_high=self._uncertain_high,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ClassifierPrediction(
            injection_probability=injection_probability,
            decision=decision,
            latency_ms=elapsed,
            details={
                "injection_probability": injection_probability,
                "label_probabilities": probs.tolist(),
                "artifact_dir": str(self._artifact_dir),
                "calibration_temperature": self._temperature,
            },
        )
