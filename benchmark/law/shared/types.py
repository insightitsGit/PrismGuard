from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GuardDecision = Literal["allow", "block", "gray"]


@dataclass
class GuardOutcome:
    decision: GuardDecision
    resolution_gate: str
    guardrail: str
    guard_classifier_calls: int = 0
    guard_generative_llm_calls: int = 0
    guard_model_tier: str = "classifier"
    latency_ms: float = 0.0
    mapped_category: str | None = None
    details: dict = field(default_factory=dict)


@dataclass
class StackResult:
    stack_id: str
    framework: str
    guardrail: str
    query_id: str | None
    input_text: str
    guard: GuardOutcome
    answer: str = ""
    task_success: bool = False
    pipeline_latency_ms: float = 0.0
    latency_ms: float = 0.0  # alias for pipeline_latency_ms (legacy)
    agent_llm_calls: int = 0
    error: str | None = None
    traffic_kind: str = "benign"

    def __post_init__(self) -> None:
        if self.pipeline_latency_ms == 0.0 and self.latency_ms != 0.0:
            self.pipeline_latency_ms = self.latency_ms
        elif self.latency_ms == 0.0 and self.pipeline_latency_ms != 0.0:
            self.latency_ms = self.pipeline_latency_ms
