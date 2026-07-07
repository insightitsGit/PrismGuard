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
    latency_ms: float = 0.0
    agent_llm_calls: int = 0
    error: str | None = None
    traffic_kind: str = "benign"
