from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from prismguard.seed.importer import ImportOptions, SeedImporter
from prismguard.seed.models import EntrySeed, ParsedSeed
from prismguard.storage.protocols import StorageBackend

if TYPE_CHECKING:
    from prismguard.runtime.check import CheckResult


def _normalize_prompt(text: str) -> str:
    from prismguard.runtime.normalize import normalize_prompt

    return normalize_prompt(text)

ReviewOrigin = Literal["guard_model", "llm_judge"]
ReviewStatus = Literal["pending", "approved", "rejected"]


@dataclass
class ReviewItem:
    id: str
    prompt: str
    normalized_prompt: str
    category_slug: str
    severity: str
    origin: ReviewOrigin
    status: ReviewStatus
    check_result: CheckResult
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


@dataclass
class CalibrationEntry:
    id: str
    prompt: str
    normalized_prompt: str
    category_slug: str | None
    origin: ReviewOrigin
    fused_score: float
    guard_model_confidence: float | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class FeedbackReviewService:
    """
    Human-in-the-loop feedback: confirmed blocks queue for review before seed append.
    Near-miss allows become calibration data, not seed corpus entries.
    """

    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage
        self._importer = SeedImporter(storage)
        self._queue: dict[str, ReviewItem] = {}
        self._calibration: list[CalibrationEntry] = []

    @property
    def pending_count(self) -> int:
        return len([item for item in self._queue.values() if item.status == "pending"])

    @property
    def calibration_count(self) -> int:
        return len(self._calibration)

    def list_pending(self) -> list[ReviewItem]:
        return [item for item in self._queue.values() if item.status == "pending"]

    def list_calibration(self) -> list[CalibrationEntry]:
        return list(self._calibration)

    def enqueue_block(
        self,
        *,
        prompt: str,
        check_result: CheckResult,
        origin: ReviewOrigin,
        category_slug: str,
        severity: str = "high",
    ) -> ReviewItem:
        item = ReviewItem(
            id=str(uuid4()),
            prompt=prompt,
            normalized_prompt=check_result.normalized_prompt or _normalize_prompt(prompt),
            category_slug=category_slug,
            severity=severity,
            origin=origin,
            status="pending",
            check_result=check_result,
        )
        self._queue[item.id] = item
        return item

    def record_near_miss_allow(
        self,
        *,
        prompt: str,
        check_result: CheckResult,
        origin: ReviewOrigin,
    ) -> CalibrationEntry:
        entry = CalibrationEntry(
            id=str(uuid4()),
            prompt=prompt,
            normalized_prompt=check_result.normalized_prompt or _normalize_prompt(prompt),
            category_slug=check_result.matched_category,
            origin=origin,
            fused_score=float(check_result.details.get("fused_score", check_result.fused_score)),
            guard_model_confidence=check_result.details.get("guard_model_confidence"),
        )
        self._calibration.append(entry)
        return entry

    def approve_block(self, review_id: str, *, reviewer: str) -> str | None:
        item = self._queue.get(review_id)
        if item is None or item.status != "pending":
            return None
        source = "llm_judge_reviewed" if item.origin == "llm_judge" else "guard_model_reviewed"
        parsed = ParsedSeed(
            entries=[
                EntrySeed(
                    text=item.prompt,
                    category_slug=item.category_slug,
                    severity=item.severity,  # type: ignore[arg-type]
                    source=source,
                )
            ],
            source_files=[f"feedback_review:{review_id}"],
        )
        report = self._importer.import_parsed(parsed, ImportOptions(mode="update", skip_taxonomy=True))
        if report.inserted == 0 and report.updated == 0:
            return None
        item.status = "approved"
        item.reviewed_by = reviewer
        item.reviewed_at = datetime.now(UTC)
        return item.id

    def reject_block(self, review_id: str, *, reviewer: str) -> bool:
        item = self._queue.get(review_id)
        if item is None or item.status != "pending":
            return False
        item.status = "rejected"
        item.reviewed_by = reviewer
        item.reviewed_at = datetime.now(UTC)
        return True

    def export_training_jsonl(
        self,
        path: Path,
        *,
        include_approved_blocks: bool = True,
        include_calibration_allows: bool = False,
    ) -> int:
        """Export reviewed feedback rows for classifier retraining (open loop)."""
        rows: list[dict[str, str]] = []
        if include_approved_blocks:
            for item in self._queue.values():
                if item.status != "approved":
                    continue
                rows.append(
                    {
                        "prompt": item.prompt,
                        "decision": "block",
                        "source": "guard_model_reviewed"
                        if item.origin == "guard_model"
                        else "llm_judge_reviewed",
                        "category_slug": item.category_slug,
                    }
                )
        if include_calibration_allows:
            for entry in self._calibration:
                rows.append(
                    {
                        "prompt": entry.prompt,
                        "decision": "allow",
                        "source": f"{entry.origin}_calibration",
                        "category_slug": entry.category_slug or "",
                    }
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return len(rows)

    def seed_entry_exists(self, *, category_slug: str, text: str) -> bool:
        normalized = _normalize_prompt(text)
        for entry in self._storage.vector.list_seed_entries_by_category(category_slug):
            if entry.chunk_text == normalized or entry.raw_text.strip() == text.strip():
                return True
        return False
