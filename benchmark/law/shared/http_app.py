from __future__ import annotations

import os
from typing import Callable

from fastapi import FastAPI
from pydantic import BaseModel, Field

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
    latency_ms: float = 0.0
    guard_llm_calls: int = 0
    agent_llm_calls: int = 0
    traffic_kind: str = "benign"
    error: str | None = None


def _to_response(result: StackResult) -> QueryResponse:
    return QueryResponse(
        stack_id=result.stack_id,
        framework=result.framework,
        guardrail=result.guardrail,
        decision=result.guard.decision,
        resolution_gate=result.guard.resolution_gate,
        mapped_category=result.guard.mapped_category,
        answer=result.answer,
        task_success=result.task_success,
        latency_ms=result.latency_ms,
        guard_llm_calls=result.guard.guard_llm_calls,
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
    def query(req: QueryRequest) -> QueryResponse:
        law_query = _queries().get(req.query_id) if req.query_id else None
        text = law_query.text if law_query and req.traffic_kind == "benign" else req.text
        result = runner(
            stack_id=stack_id,
            guard=guard,
            assistant=assistant,
            text=text,
            query=law_query,
            traffic_kind=req.traffic_kind,
        )
        return _to_response(result)

    return app


def main(stack_id: str, framework: str, guard_factory: Callable[[], GuardGate]) -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(create_app(stack_id=stack_id, framework=framework, guard_factory=guard_factory), host="0.0.0.0", port=port)
