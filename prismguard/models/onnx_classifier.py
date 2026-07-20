from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from prismguard.models.calibration import apply_temperature, load_calibration
from prismguard.models.deps import require_numpy, require_onnxruntime, require_tokenizers_tokenizer
from prismguard.models.model_card import ModelCard
from prismguard.models.verdict import injection_probability_to_decision


def _softmax(logits: Any) -> Any:
    np = require_numpy()
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def _default_ort_intra_threads() -> int:
    explicit = int(os.environ.get("PRISMGUARD_ORT_INTRA_THREADS", "0"))
    if explicit > 0:
        return explicit
    return min(4, os.cpu_count() or 1)


def _default_ort_inter_threads() -> int:
    explicit = int(os.environ.get("PRISMGUARD_ORT_INTER_THREADS", "0"))
    if explicit > 0:
        return explicit
    return 1


def _ort_providers() -> list[str]:
    """
    Select ORT execution providers.

    Override with comma-separated ``PRISMGUARD_ORT_PROVIDERS``
    (e.g. ``CUDAExecutionProvider,CPUExecutionProvider``).
    Default: first available of CUDA → Dml → CoreML → CPU.
    """
    explicit = os.environ.get("PRISMGUARD_ORT_PROVIDERS", "").strip()
    if explicit:
        return [p.strip() for p in explicit.split(",") if p.strip()]
    ort = require_onnxruntime()
    available = set(ort.get_available_providers())
    preferred = (
        "CUDAExecutionProvider",
        "DmlExecutionProvider",
        "CoreMLExecutionProvider",
        "CPUExecutionProvider",
    )
    chosen = [p for p in preferred if p in available]
    return chosen or ["CPUExecutionProvider"]


def _dynamic_pad_length(token_len: int, *, max_length: int) -> int:
    """Pad to next multiple of 8 (ORT-friendly) without always padding to max_length."""
    if token_len <= 0:
        return min(8, max_length)
    padded = ((token_len + 7) // 8) * 8
    return min(max(padded, 8), max_length)


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
        self._providers: list[str] = []
        calibration = load_calibration(artifact_dir)
        self._temperature = calibration.temperature if calibration else card.calibration_temperature
        self._warmed_up = False

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
        if os.environ.get("PRISMGUARD_ONNX_INT8", "").strip().lower() in ("1", "true", "yes"):
            int8_path = artifact_dir / "model.int8.onnx"
            if int8_path.is_file():
                onnx_path = int8_path
        tokenizer_path = artifact_dir / "tokenizer.json"
        if not onnx_path.is_file():
            raise FileNotFoundError(
                f"ONNX model not found at {onnx_path}. "
                "Run: prismguard-model download"
            )
        if not tokenizer_path.is_file():
            raise FileNotFoundError(
                f"Tokenizer not found at {tokenizer_path}. "
                "Run: python -m prismguard.models.export --artifact-id prism-pi-v1"
            )

        ort = require_onnxruntime()
        Tokenizer = require_tokenizers_tokenizer()

        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.intra_op_num_threads = _default_ort_intra_threads()
        session_options.inter_op_num_threads = _default_ort_inter_threads()
        # Prefer sequential for single-request CPU latency over multi-stream overhead.
        if hasattr(ort, "ExecutionMode"):
            session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        providers = _ort_providers()
        session = ort.InferenceSession(
            str(onnx_path),
            session_options,
            providers=providers,
        )
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        instance = cls(
            artifact_dir=artifact_dir,
            card=card,
            session=session,
            tokenizer=tokenizer,
            uncertain_low=uncertain_low,
            uncertain_high=uncertain_high,
        )
        instance._providers = list(session.get_providers())  # noqa: SLF001
        if os.environ.get("PRISMGUARD_ORT_WARMUP", "1").strip().lower() not in ("0", "false", "no"):
            # Warm short + medium lengths so dynamic pad paths are primed.
            instance.warmup()
            instance.predict("warmup medium length prompt for ORT kernel cache " * 4)
            instance._warmed_up = True
        return instance

    def warmup(self) -> None:
        """Prime ORT session caches with a short dummy inference."""
        if self._warmed_up or not self.is_ready:
            return
        self.predict("warmup")
        self._warmed_up = True

    def _encode(self, text: str) -> tuple[Any, Any]:
        np = require_numpy()
        encoding = self._tokenizer.encode(text)
        token_ids = encoding.ids[: self._card.max_length]
        pad_len = _dynamic_pad_length(len(token_ids), max_length=self._card.max_length)
        attention_mask = [1] * len(token_ids)
        if pad_len > len(token_ids):
            pad_count = pad_len - len(token_ids)
            token_ids = token_ids + [0] * pad_count
            attention_mask = attention_mask + [0] * pad_count
        ids = np.array([token_ids], dtype=np.int64)
        mask = np.array([attention_mask], dtype=np.int64)
        return ids, mask

    def predict(self, text: str) -> ClassifierPrediction:
        np = require_numpy()
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
                "sequence_length": int(input_ids.shape[1]),
                "ort_providers": list(self._providers),
            },
        )


@lru_cache(maxsize=4)
def _cached_classifier_key(
    artifact_dir: str,
    uncertain_low: float,
    uncertain_high: float,
) -> str:
    return f"{artifact_dir}\0{uncertain_low}\0{uncertain_high}"


_classifier_singletons: dict[str, ONNXPromptInjectionClassifier] = {}


def get_or_load_classifier(
    artifact_dir: Path,
    *,
    card: ModelCard,
    uncertain_low: float,
    uncertain_high: float,
) -> ONNXPromptInjectionClassifier:
    """Reuse a warmed ONNX session per artifact path (process lifetime)."""
    key = _cached_classifier_key(str(artifact_dir.resolve()), uncertain_low, uncertain_high)
    if key not in _classifier_singletons:
        _classifier_singletons[key] = ONNXPromptInjectionClassifier.from_artifact_dir(
            artifact_dir,
            card=card,
            uncertain_low=uncertain_low,
            uncertain_high=uncertain_high,
        )
    return _classifier_singletons[key]


def clear_classifier_cache() -> None:
    """Clear singleton cache (tests)."""
    _classifier_singletons.clear()
    _cached_classifier_key.cache_clear()
