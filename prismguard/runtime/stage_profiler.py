from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("prismguard.pipeline.profile")

# Stages rolled up for reports (maps raw timer keys → bucket).
STAGE_BUCKETS: dict[str, str] = {
    "normalize": "normalize",
    "classifier_start": "classifier",
    "classifier": "classifier",
    "classifier_gray": "classifier",
    "tier1": "rules",
    "tenant": "rules",
    "structural": "structural",
    "embed": "embedding",
    "category": "embedding",
    "ann_search": "ann_corpus",
    "graph": "graph_fusion",
    "fusion": "graph_fusion",
    "gray_resolve": "gray_escalation",
    "judge": "judge",
}


def profile_enabled() -> bool:
    return os.environ.get("PRISMGUARD_PROFILE_STAGES", "").strip().lower() in ("1", "true", "yes")


def profile_log_enabled() -> bool:
    return os.environ.get("PRISMGUARD_PROFILE_LOG", "").strip().lower() in ("1", "true", "yes")


def bucket_stages(raw: dict[str, float]) -> dict[str, float]:
    """Roll raw stage keys into coarse buckets for summary tables."""
    out: dict[str, float] = {}
    for key, ms in raw.items():
        bucket = STAGE_BUCKETS.get(key, key)
        out[bucket] = out.get(bucket, 0.0) + ms
    return {k: round(v, 3) for k, v in out.items()}


class StageProfiler:
    """Per-request pipeline stage timings.

    Enable collection: ``PRISMGUARD_PROFILE_STAGES=1``
    Enable per-request JSON logs: ``PRISMGUARD_PROFILE_LOG=1``
    """

    _active: StageProfiler | None = None

    def __init__(self) -> None:
        self._ms: dict[str, float] = {}

    @classmethod
    def begin(cls) -> StageProfiler | None:
        if not profile_enabled():
            return None
        profiler = cls()
        cls._active = profiler
        return profiler

    @classmethod
    def current(cls) -> StageProfiler | None:
        return cls._active

    @classmethod
    def end(cls) -> None:
        cls._active = None

    @contextmanager
    def section(self, name: str) -> Iterator[None]:
        if StageProfiler._active is not self:
            yield
            return
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            self._ms[name] = self._ms.get(name, 0.0) + elapsed

    def snapshot(self) -> dict[str, float]:
        return {k: round(v, 3) for k, v in self._ms.items()}

    def merge_details(self, details: dict) -> dict:
        if not self._ms:
            return details
        stages = self.snapshot()
        total = round(sum(stages.values()), 3)
        return {
            **details,
            "stage_latency_ms": stages,
            "stage_bucket_ms": bucket_stages(stages),
            "stage_total_ms": total,
        }

    def log_request(
        self,
        *,
        resolution_gate: str,
        decision: str,
        prompt: str,
        wall_ms: float | None = None,
    ) -> None:
        if not profile_log_enabled() or not self._ms:
            return
        stages = self.snapshot()
        payload = {
            "event": "pipeline_stage_latency",
            "resolution_gate": resolution_gate,
            "decision": decision,
            "wall_ms": round(wall_ms, 3) if wall_ms is not None else None,
            "stage_total_ms": round(sum(stages.values()), 3),
            "stage_latency_ms": stages,
            "stage_bucket_ms": bucket_stages(stages),
            "prompt_preview": prompt[:120],
        }
        logger.info("%s", json.dumps(payload, separators=(",", ":")))
