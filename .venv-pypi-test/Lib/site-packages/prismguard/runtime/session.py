from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass
class SessionTurn:
    prompt: str
    normalized: str
    category_slug: str | None
    attack_sim: float
    decision: str
    turn_index: int
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_PAYLOAD_REF_PATTERNS = (
    re.compile(r"\bpart\s*[2-9]\b", re.I),
    re.compile(r"\b(the )?(value|variable|token|secret) (above|from before|in part)\b", re.I),
    re.compile(r"\bnow execute\b", re.I),
    re.compile(r"\bcall it [a-z0-9_]+\b", re.I),
)

_REFUSAL_SUPPRESSION = (
    re.compile(r"\bnever (say|apologize|refuse)\b", re.I),
    re.compile(r"\bdo not (refuse|decline|warn)\b", re.I),
    re.compile(r"\balways comply\b", re.I),
)

_ESCALATION_CATEGORIES = frozenset(
    {"multi_turn_escalation", "payload_splitting", "roleplay_jailbreak", "direct_instruction_override"}
)


class SessionStore(Protocol):
    def record_turn(
        self,
        session_id: str,
        *,
        prompt: str,
        normalized: str,
        category_slug: str | None,
        attack_sim: float,
        decision: str,
        turn_index: int | None = None,
    ) -> None: ...

    def escalation_score(self, session_id: str) -> float: ...


@dataclass
class InMemorySessionStore:
    """In-process session store (v1). Redis optional extra deferred."""

    max_turns: int = 8
    _sessions: dict[str, deque[SessionTurn]] = field(default_factory=dict)

    def record_turn(
        self,
        session_id: str,
        *,
        prompt: str,
        normalized: str,
        category_slug: str | None,
        attack_sim: float,
        decision: str,
        turn_index: int | None = None,
    ) -> None:
        if not session_id:
            return
        turns = self._sessions.setdefault(session_id, deque(maxlen=self.max_turns))
        idx = turn_index if turn_index is not None else len(turns)
        turns.append(
            SessionTurn(
                prompt=prompt,
                normalized=normalized,
                category_slug=category_slug,
                attack_sim=attack_sim,
                decision=decision,
                turn_index=idx,
            )
        )

    def escalation_score(self, session_id: str) -> float:
        if not session_id or session_id not in self._sessions:
            return 0.0
        turns = list(self._sessions[session_id])
        if len(turns) < 2:
            return self._single_turn_hints(turns[-1].normalized if turns else "")

        score = 0.0
        recent = turns[-3:]
        cats = [t.category_slug for t in recent if t.category_slug]
        if len(set(cats)) >= 2 and any(c in _ESCALATION_CATEGORIES for c in cats):
            score += 0.25

        sims = [t.attack_sim for t in recent]
        if len(sims) >= 2 and sims[-1] > sims[-2] + 0.08:
            score += 0.20

        combined = " ".join(t.normalized for t in recent)
        if any(p.search(combined) for p in _PAYLOAD_REF_PATTERNS):
            score += 0.35

        refusal_hits = sum(1 for p in _REFUSAL_SUPPRESSION if p.search(combined))
        score += min(0.25, refusal_hits * 0.12)

        return min(1.0, score)

    @staticmethod
    def _single_turn_hints(text: str) -> float:
        if any(p.search(text) for p in _PAYLOAD_REF_PATTERNS):
            return 0.2
        return 0.0


def create_session_store(*, backend: str = "memory") -> SessionStore:
    if backend == "memory":
        return InMemorySessionStore()
    raise ValueError(f"Unknown session store backend {backend!r}")
