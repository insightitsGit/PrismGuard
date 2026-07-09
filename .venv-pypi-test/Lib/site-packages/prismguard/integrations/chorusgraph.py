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
    """Build a RuntimeChecker from environment (domain, storage, seed profile)."""
    import os

    from prismguard.config.loader import load_triage_config
    from prismguard.runtime.check import RuntimeChecker
    from prismguard.runtime.guard_model import create_guard_model
    from prismguard.runtime.llm_judge import create_llm_judge
    from prismguard.seed import import_bundled_seed, load_bundled_seed
    from prismguard.storage import create_storage_from_env
    from prismguard.taxonomy.embedder import create_embedder_from_config

    domain = os.environ.get("PRISMGUARD_DOMAIN", "law")
    profile = os.environ.get("PRISMGUARD_SEED_PROFILE", "authored")
    storage = create_storage_from_env()
    parsed = load_bundled_seed(profile=profile)
    import_bundled_seed(storage, profile=profile)
    cfg = load_triage_config(domain=domain)
    embedder = create_embedder_from_config(cfg)
    guard_model = create_guard_model(cfg.guard_model) if cfg.guard_model.enabled else None
    llm_judge = None
    if cfg.gray_zone_policy == "escalate" and guard_model is not None:
        llm_judge = create_llm_judge(
            prefer_openai=False,
            rate_cap_per_minute=cfg.judge.rate_cap_per_minute,
            embedder=embedder,
            cache_similarity_threshold=cfg.cache.semantic_cache_threshold,
        )
    return RuntimeChecker.from_storage(
        storage,
        parsed,
        embedder=embedder,
        config=cfg,
        guard_model=guard_model,
        llm_judge=llm_judge,
    )
