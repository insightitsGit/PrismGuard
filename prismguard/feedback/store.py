from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prismguard.feedback.review import CalibrationEntry, ReviewItem
    from prismguard.runtime.check import CheckResult


def _serialize_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _deserialize_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class FeedbackStore:
    """JSON-backed persistence for review queue and calibration entries."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> tuple[dict[str, "ReviewItem"], list["CalibrationEntry"]]:
        from prismguard.feedback.review import CalibrationEntry, ReviewItem

        if not self._path.is_file():
            return {}, []
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        queue: dict[str, ReviewItem] = {}
        for item_id, row in (raw.get("queue") or {}).items():
            queue[item_id] = ReviewItem(
                id=row["id"],
                prompt=row["prompt"],
                normalized_prompt=row["normalized_prompt"],
                category_slug=row["category_slug"],
                severity=row["severity"],
                origin=row["origin"],
                status=row["status"],
                check_result=_deserialize_check_result(row.get("check_result_snapshot") or row.get("check_result")),
                created_at=_deserialize_dt(row.get("created_at")) or datetime.now(UTC),
                reviewed_by=row.get("reviewed_by"),
                reviewed_at=_deserialize_dt(row.get("reviewed_at")),
            )
        calibration: list[CalibrationEntry] = []
        for row in raw.get("calibration") or []:
            calibration.append(
                CalibrationEntry(
                    id=row["id"],
                    prompt=row["prompt"],
                    normalized_prompt=row["normalized_prompt"],
                    category_slug=row.get("category_slug"),
                    origin=row["origin"],
                    fused_score=float(row.get("fused_score") or 0),
                    guard_model_confidence=row.get("guard_model_confidence"),
                    created_at=_deserialize_dt(row.get("created_at")) or datetime.now(UTC),
                )
            )
        return queue, calibration

    def save(
        self,
        queue: dict[str, "ReviewItem"],
        calibration: list["CalibrationEntry"],
    ) -> None:
        payload: dict[str, Any] = {
            "queue": {
                item_id: {
                    "id": item.id,
                    "prompt": item.prompt,
                    "normalized_prompt": item.normalized_prompt,
                    "category_slug": item.category_slug,
                    "severity": item.severity,
                    "origin": item.origin,
                    "status": item.status,
                    "check_result_snapshot": _check_result_snapshot(item.check_result),
                    "created_at": _serialize_dt(item.created_at),
                    "reviewed_by": item.reviewed_by,
                    "reviewed_at": _serialize_dt(item.reviewed_at),
                }
                for item_id, item in queue.items()
            },
            "calibration": [
                {
                    "id": entry.id,
                    "prompt": entry.prompt,
                    "normalized_prompt": entry.normalized_prompt,
                    "category_slug": entry.category_slug,
                    "origin": entry.origin,
                    "fused_score": entry.fused_score,
                    "guard_model_confidence": entry.guard_model_confidence,
                    "created_at": _serialize_dt(entry.created_at),
                }
                for entry in calibration
            ],
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _deserialize_check_result(raw: Any) -> "CheckResult":
    from prismguard.runtime.check import CheckResult

    if isinstance(raw, CheckResult):
        return raw
    if not isinstance(raw, dict):
        return CheckResult(decision="gray", resolution_gate="uninitialized")
    return CheckResult(
        decision=raw.get("decision", "gray"),
        resolution_gate=raw.get("resolution_gate", "uninitialized"),
        fused_score=float(raw.get("fused_score") or 0),
        matched_category=raw.get("matched_category"),
        details=dict(raw.get("details") or {}),
        normalized_prompt=str(raw.get("normalized_prompt") or ""),
    )


def _check_result_snapshot(check_result: Any) -> dict[str, Any]:
    if hasattr(check_result, "decision"):
        return {
            "decision": check_result.decision,
            "resolution_gate": check_result.resolution_gate,
            "fused_score": getattr(check_result, "fused_score", 0),
            "matched_category": getattr(check_result, "matched_category", None),
            "normalized_prompt": getattr(check_result, "normalized_prompt", ""),
            "details": getattr(check_result, "details", {}),
        }
    if isinstance(check_result, dict):
        return check_result
    return {"decision": "gray", "resolution_gate": "unknown", "details": {}}


def default_feedback_store_path() -> Path:
    import os

    env = os.environ.get("PRISMGUARD_FEEDBACK_PATH", "").strip()
    if env:
        return Path(env)
    return Path.cwd() / ".prismguard" / "feedback.json"
