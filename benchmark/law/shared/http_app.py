from __future__ import annotations

import os
from typing import Callable

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from benchmark.law.shared.assistant import LawAssistant, run_chorus_pipeline, run_langgraph_pipeline
from benchmark.law.shared.cases import LawQuery, load_queries
from benchmark.law.shared.guards import GuardGate
from benchmark.law.shared.types import StackResult

_QUERY_INDEX: dict[str, LawQuery] | None = None


def _queries() -> dict[str, LawQuery]:
    global _QUERY_INDEX
    if _QUERY_INDEX is None:
        _QUERY_INDEX = {q.query_id: q for q in load_queries()}
    return _QUERY_INDEX


class QueryRequest(BaseModel):
    text: str
    query_id: str | None = None
    traffic_kind: str = "benign"


class QueryResponse(BaseModel):
    stack_id: str
    framework: str
    guardrail: str
    decision: str
    resolution_gate: str
    mapped_category: str | None = None
    answer: str = ""
    task_success: bool = False
    guard_latency_ms: float = 0.0
    pipeline_latency_ms: float = 0.0
    latency_ms: float = 0.0
    guard_classifier_calls: int = 0
    guard_generative_llm_calls: int = 0
    guard_model_tier: str = ""
    agent_llm_calls: int = 0
    traffic_kind: str = "benign"
    error: str | None = None


def _to_response(result: StackResult) -> QueryResponse:
    pipeline_ms = result.pipeline_latency_ms or result.latency_ms
    guard_ms = result.guard.latency_ms
    return QueryResponse(
        stack_id=result.stack_id,
        framework=result.framework,
        guardrail=result.guardrail,
        decision=result.guard.decision,
        resolution_gate=result.guard.resolution_gate,
        mapped_category=result.guard.mapped_category,
        answer=result.answer,
        task_success=result.task_success,
        guard_latency_ms=guard_ms,
        pipeline_latency_ms=pipeline_ms,
        latency_ms=pipeline_ms,
        guard_classifier_calls=result.guard.guard_classifier_calls,
        guard_generative_llm_calls=result.guard.guard_generative_llm_calls,
        guard_model_tier=result.guard.guard_model_tier,
        agent_llm_calls=result.agent_llm_calls,
        traffic_kind=result.traffic_kind,
        error=result.error,
    )


def create_app(
    *,
    stack_id: str,
    framework: str,
    guard_factory: Callable[[], GuardGate],
) -> FastAPI:
    app = FastAPI(title=f"PrismGuard Law Benchmark — {stack_id}")
    assistant = LawAssistant()
    guard = guard_factory()
    runner = run_chorus_pipeline if framework == "chorusgraph" else run_langgraph_pipeline

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "stack": stack_id}

    @app.post("/query", response_model=QueryResponse)
    async def query(req: QueryRequest) -> QueryResponse:
        law_query = _queries().get(req.query_id) if req.query_id else None
        text = law_query.text if law_query and req.traffic_kind == "benign" else req.text
        result = await run_in_threadpool(
            runner,
            stack_id=stack_id,
            guard=guard,
            assistant=assistant,
            text=text,
            query=law_query,
            traffic_kind=req.traffic_kind,
        )
        return _to_response(result)

    return app


def serve_app(*, import_target: str) -> None:
    """Run uvicorn with optional multi-worker (``UVICORN_WORKERS``)."""
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    workers = max(1, int(os.environ.get("UVICORN_WORKERS", "1")))
    uvicorn.run(import_target, host="0.0.0.0", port=port, workers=workers)


def main(stack_id: str, framework: str, guard_factory: Callable[[], GuardGate]) -> None:
    """Legacy entry: single-worker in-process app (used by tests)."""
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    app = create_app(stack_id=stack_id, framework=framework, guard_factory=guard_factory)
    uvicorn.run(app, host="0.0.0.0", port=port)
