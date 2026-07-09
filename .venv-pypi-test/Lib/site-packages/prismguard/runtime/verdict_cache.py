"""Content-addressed verdict cache (PrismCortex-style deterministic replay)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prismguard.runtime.check import CheckResult

_SEP = "\x00"
_DEFAULT_TTL = 3600


@dataclass(frozen=True)
class CachedVerdict:
    decision: str
    resolution_gate: str
    matched_category: str | None
    details: dict[str, Any]
    cached_at: float


def _enabled() -> bool:
    return os.environ.get("PRISMGUARD_VERDICT_CACHE", "").strip().lower() in ("1", "true", "yes")


def _ttl_seconds() -> int:
    raw = os.environ.get("PRISMGUARD_VERDICT_CACHE_TTL", str(_DEFAULT_TTL))
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_TTL


def content_address(
    *,
    normalized_prompt: str,
    artifact_id: str,
    classifier_mode: str,
    rule_version: str,
    structural_threshold: float,
    veto_threshold: float,
) -> str:
    """Stable cache key for a guard verdict given inputs and policy snapshot."""
    payload = _SEP.join(
        [
            " ".join(normalized_prompt.lower().split()),
            artifact_id,
            classifier_mode,
            rule_version,
            f"{structural_threshold:.4f}",
            f"{veto_threshold:.4f}",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rule_version_snapshot(*, tier1_rules: list[Any], structural_version: str = "1") -> str:
    """Hash tier-1 rule ids/patterns so cache invalidates when rules change."""
    rows = sorted(
        (
            getattr(rule, "rule_id", str(rule.get("rule_id", ""))),
            getattr(rule, "pattern", str(rule.get("pattern", ""))),
        )
        for rule in tier1_rules
    )
    body = json.dumps({"structural": structural_version, "tier1": rows}, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


class VerdictCache:
    def __init__(self, *, ttl_seconds: int | None = None) -> None:
        self._ttl = _ttl_seconds() if ttl_seconds is None else ttl_seconds
        self._store: dict[str, CachedVerdict] = {}

    def get(self, key: str) -> "CheckResult | None":
        from prismguard.runtime.check import CheckResult
        entry = self._store.get(key)
        if entry is None:
            return None
        if self._ttl > 0 and (time.time() - entry.cached_at) > self._ttl:
            del self._store[key]
            return None
        return CheckResult(
            decision=entry.decision,  # type: ignore[arg-type]
            resolution_gate=entry.resolution_gate,  # type: ignore[arg-type]
            matched_category=entry.matched_category,
            normalized_prompt="",
            details={**entry.details, "verdict_cache_hit": True},
        )

    def put(self, key: str, result: "CheckResult") -> None:
        self._store[key] = CachedVerdict(
            decision=result.decision,
            resolution_gate=result.resolution_gate,
            matched_category=result.matched_category,
            details=dict(result.details),
            cached_at=time.time(),
        )

    def clear(self) -> None:
        self._store.clear()


_global_cache: VerdictCache | None = None


def get_verdict_cache() -> VerdictCache | None:
    global _global_cache
    if not _enabled():
        return None
    if _global_cache is None:
        _global_cache = VerdictCache()
    return _global_cache
