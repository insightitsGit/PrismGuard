from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Protocol

from prismguard.config.loader import GuardModelConfig, load_triage_config
from prismguard.models.loader import load_onnx_classifier
from prismguard.models.verdict import GuardModelDecision


@dataclass(frozen=True)
class GuardModelVerdict:
    decision: GuardModelDecision
    confidence: float
    latency_ms: float = 0.0
    model_id: str = "unknown"
    details: dict = field(default_factory=dict)


class GuardModel(Protocol):
    """Local classifier invoked only on fusion gray-zone traffic."""

    @property
    def model_id(self) -> str: ...

    @property
    def call_count(self) -> int: ...

    @property
    def is_ready(self) -> bool: ...

    def check(self, text: str, *, context: dict | None = None) -> GuardModelVerdict: ...


class CountingGuardModel:
    """Wrap any GuardModel and track invocation count for tests and benchmarks."""

    def __init__(self, inner: GuardModel) -> None:
        self._inner = inner
        self._calls = 0

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    @property
    def call_count(self) -> int:
        return self._calls

    @property
    def is_ready(self) -> bool:
        return self._inner.is_ready

    def check(self, text: str, *, context: dict | None = None) -> GuardModelVerdict:
        self._calls += 1
        return self._inner.check(text, context=context)


class PrismONNXGuardModel:
    """PrismGuard-owned ONNX classifier for the Guard Model tier."""

    def __init__(self, config: GuardModelConfig) -> None:
        self._config = config
        self._classifier = None
        self._init_error = ""
        try:
            self._classifier = load_onnx_classifier(config)
        except Exception as exc:  # pragma: no cover - missing artifact in dev
            self._init_error = str(exc)

    @property
    def model_id(self) -> str:
        if self._classifier is not None:
            return self._classifier.model_id
        return self._config.artifact_id

    @property
    def call_count(self) -> int:
        return 0

    @property
    def is_ready(self) -> bool:
        return self._classifier is not None and self._classifier.is_ready

    def check(self, text: str, *, context: dict | None = None) -> GuardModelVerdict:
        _ = context
        start = time.perf_counter()
        if self._classifier is None:
            return GuardModelVerdict(
                decision="uncertain",
                confidence=0.0,
                latency_ms=(time.perf_counter() - start) * 1000,
                model_id=self.model_id,
                details={"error": self._init_error or "guard model artifact not loaded"},
            )
        prediction = self._classifier.predict(text)
        return GuardModelVerdict(
            decision=prediction.decision,  # type: ignore[arg-type]
            confidence=prediction.injection_probability,
            latency_ms=prediction.latency_ms,
            model_id=self.model_id,
            details=prediction.details,
        )


def create_guard_model(
    config: GuardModelConfig | None = None,
) -> GuardModel | None:
    """Load the PrismGuard ONNX Guard Model when enabled and artifacts are present."""
    cfg = config or load_triage_config().guard_model
    if not cfg.enabled:
        return None
    model = PrismONNXGuardModel(cfg)
    if not model.is_ready:
        return None
    return CountingGuardModel(model)
