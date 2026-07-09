"""ChorusGraph integration — guard node for native graphs (OSS)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class GuardNodeResult:
    decision: str
    resolution_gate: str
    matched_category: str | None
    blocked: bool
    latency_ms: float
    details: dict[str, Any]


class GuardChecker(Protocol):
    def check(self, text: str, *, session_id: str | None = None) -> Any: ...


def make_guard_handler(
    checker: GuardChecker,
    *,
    text_key: str = "text",
    session_id_key: str = "session_id",
    block_on: frozenset[str] = frozenset({"block"}),
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """
    Build a ChorusGraph-compatible node handler: read ``text_key`` from state,
    run PrismGuard, write guard metadata back, set ``blocked`` when appropriate.

    By default only ``decision == "block"`` sets ``blocked``. Gray continues the
    graph unless you pass ``block_on=frozenset({"block", "gray"})``.

    Example graph::

        START → guard → [blocked → END | retrieve → writer → END]

    Wire with ``Graph.add_node("guard", dict_node_adapter(make_guard_handler(checker)))``.
    """
    import time

    def _handler(state: dict[str, Any]) -> dict[str, Any]:
        text = str(state.get(text_key, "") or "")
        session_id = state.get(session_id_key)
        start = time.perf_counter()
        result = checker.check(text, session_id=session_id if isinstance(session_id, str) else None)
        elapsed = (time.perf_counter() - start) * 1000
        decision = str(getattr(result, "decision", "allow"))
        gate = str(getattr(result, "resolution_gate", "unknown"))
        blocked = decision in block_on
        guard_result = GuardNodeResult(
            decision=decision,
            resolution_gate=gate,
            matched_category=getattr(result, "matched_category", None),
            blocked=blocked,
            latency_ms=elapsed,
            details=dict(getattr(result, "details", {}) or {}),
        )
        return {
            **state,
            "guard": {
                "decision": guard_result.decision,
                "resolution_gate": guard_result.resolution_gate,
                "matched_category": guard_result.matched_category,
                "blocked": guard_result.blocked,
                "latency_ms": guard_result.latency_ms,
                "details": guard_result.details,
            },
            "blocked": blocked,
        }

    _handler.__name__ = "prismguard_guard_node"
    return _handler


def route_after_guard(state: dict[str, Any]) -> str:
    """Conditional edge: ``blocked`` → ``end`` else ``continue``."""
    if state.get("blocked"):
        return "end"
    return "continue"


def create_checker_from_env() -> Any:
    """Build a RuntimeChecker from environment (dogfood-safe: ONNX opt-in only)."""
    from prismguard.runtime.factory import create_checker_from_env as _create

    return _create()


def create_checker_for_app(profile: str = "web_chat", **kwargs: Any) -> Any:
    """See ``prismguard.runtime.factory.create_checker_for_app``."""
    from prismguard.runtime.factory import create_checker_for_app as _create

    return _create(profile, **kwargs)  # type: ignore[arg-type]
