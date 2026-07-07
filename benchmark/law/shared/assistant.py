from __future__ import annotations

import time
from typing import Callable, TypedDict

from benchmark.law.shared.cases import LawQuery
from benchmark.law.shared.guards import GuardGate
from benchmark.law.shared.kb import build_in_memory_index, retrieve
from benchmark.law.shared.rubric import score_law_answer
from benchmark.law.shared.types import GuardOutcome, StackResult


class LawGraphState(TypedDict, total=False):
    text: str
    guard: GuardOutcome
    answer: str
    blocked: bool


def _answer_from_retrieval(query_text: str, category_slug: str, index: dict) -> str:
    hits = retrieve(index, query_text, category_slug=category_slug, top_k=2)
    if not hits:
        hits = retrieve(index, query_text, top_k=2)
    if not hits:
        return "No relevant legal authority found in the knowledge base."
    parts = [f"{doc.title}: {doc.text}" for doc in hits]
    return " ".join(parts)


class LawAssistant:
    """Shared legal RAG task — identical KB and answer synthesis for all stacks."""

    def __init__(self) -> None:
        self._index = build_in_memory_index()

    def answer(self, query: LawQuery) -> tuple[str, int]:
        return _answer_from_retrieval(query.text, query.category_slug, self._index), 0


def run_chorus_pipeline(
    *,
    stack_id: str,
    guard: GuardGate,
    assistant: LawAssistant,
    text: str,
    query: LawQuery | None,
    traffic_kind: str,
) -> StackResult:
    """ChorusGraph-style linear pipeline: guard → retrieve → answer."""
    start = time.perf_counter()
    guard_out = guard.check(text)
    if guard_out.decision == "block":
        return StackResult(
            stack_id=stack_id,
            framework="chorusgraph",
            guardrail=guard.name,
            query_id=query.query_id if query else None,
            input_text=text,
            guard=guard_out,
            latency_ms=(time.perf_counter() - start) * 1000,
            traffic_kind=traffic_kind,
        )
    if query is None:
        return StackResult(
            stack_id=stack_id,
            framework="chorusgraph",
            guardrail=guard.name,
            query_id=None,
            input_text=text,
            guard=guard_out,
            answer="",
            latency_ms=(time.perf_counter() - start) * 1000,
            traffic_kind=traffic_kind,
        )
    answer, llm_calls = assistant.answer(query)
    return StackResult(
        stack_id=stack_id,
        framework="chorusgraph",
        guardrail=guard.name,
        query_id=query.query_id,
        input_text=text,
        guard=guard_out,
        answer=answer,
        task_success=score_law_answer(answer, query),
        latency_ms=(time.perf_counter() - start) * 1000,
        agent_llm_calls=llm_calls,
        traffic_kind=traffic_kind,
    )


def run_langgraph_pipeline(
    *,
    stack_id: str,
    guard: GuardGate,
    assistant: LawAssistant,
    text: str,
    query: LawQuery | None,
    traffic_kind: str,
) -> StackResult:
    """LangGraph-style state machine when available; same node order as Chorus."""
    try:
        from langgraph.graph import END, START, StateGraph

        assistant_ref = assistant
        guard_ref = guard
        query_ref = query

        def guard_node(state: LawGraphState) -> LawGraphState:
            outcome = guard_ref.check(state["text"])
            return {"guard": outcome, "blocked": outcome.decision == "block"}

        def answer_node(state: LawGraphState) -> LawGraphState:
            if query_ref is None:
                return {"answer": ""}
            ans, _ = assistant_ref.answer(query_ref)
            return {"answer": ans}

        graph = StateGraph(LawGraphState)
        graph.add_node("guard", guard_node)
        graph.add_node("answer", answer_node)
        graph.add_edge(START, "guard")

        def route(state: LawGraphState) -> str:
            return END if state.get("blocked") else "answer"

        graph.add_conditional_edges("guard", route, {END: END, "answer": "answer"})
        graph.add_edge("answer", END)
        compiled = graph.compile()
        start = time.perf_counter()
        final = compiled.invoke({"text": text})
        guard_out = final["guard"]
        if final.get("blocked"):
            return StackResult(
                stack_id=stack_id,
                framework="langgraph",
                guardrail=guard.name,
                query_id=query.query_id if query else None,
                input_text=text,
                guard=guard_out,
                latency_ms=(time.perf_counter() - start) * 1000,
                traffic_kind=traffic_kind,
            )
        answer = final.get("answer", "")
        return StackResult(
            stack_id=stack_id,
            framework="langgraph",
            guardrail=guard.name,
            query_id=query.query_id if query else None,
            input_text=text,
            guard=guard_out,
            answer=answer,
            task_success=score_law_answer(answer, query) if query else False,
            latency_ms=(time.perf_counter() - start) * 1000,
            traffic_kind=traffic_kind,
        )
    except ImportError:
        return run_chorus_pipeline(
            stack_id=stack_id,
            guard=guard,
            assistant=assistant,
            text=text,
            query=query,
            traffic_kind=traffic_kind,
        )
