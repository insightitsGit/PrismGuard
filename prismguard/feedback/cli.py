"""CLI for feedback review export (customer/pilot training loop)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from prismguard.feedback.store import default_feedback_store_path
from prismguard.storage import create_storage, create_storage_from_env


def _storage(backend: str | None):
    if backend:
        return create_storage(backend)
    if os.environ.get("PRISMGUARD_STORAGE_BACKEND") or os.environ.get("PRISMGUARD_STORAGE_DSN"):
        return create_storage_from_env()
    return create_storage("memory")


def cmd_export(args: argparse.Namespace) -> int:
    """Export approved blocks (+ optional calibration allows) to training JSONL.

    Default: export approved blocks only. Calibration allows are opt-in.
    Requires PRISMGUARD_FEEDBACK_PERSIST=1 (or an existing feedback store file).
    """
    from prismguard.feedback.review import FeedbackReviewService

    store_path = Path(args.store) if args.store else default_feedback_store_path()
    # Load from disk even if persist env is off (export of prior pilot data).
    os.environ.setdefault("PRISMGUARD_FEEDBACK_PERSIST", "1")
    storage = _storage(args.backend)
    try:
        review = FeedbackReviewService(storage, store_path=store_path)
        count = review.export_training_jsonl(
            Path(args.output),
            include_approved_blocks=not args.calibration_only,
            include_calibration_allows=bool(args.include_calibration_allows or args.calibration_only),
        )
        print(
            json.dumps(
                {
                    "exported": count,
                    "output": str(Path(args.output).resolve()),
                    "store": str(store_path),
                    "include_calibration_allows": bool(
                        args.include_calibration_allows or args.calibration_only
                    ),
                },
                indent=2,
            )
        )
        return 0 if count >= 0 else 1
    finally:
        storage.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prismguard feedback",
        description="Export reviewed feedback for customer/hub ONNX training (opt-in).",
    )
    sub = parser.add_subparsers(dest="feedback_command", required=True)

    export_cmd = sub.add_parser(
        "export",
        help="Export training JSONL (default: approved blocks only)",
    )
    export_cmd.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output JSONL path for prismguard-model train --feedback-jsonl",
    )
    export_cmd.add_argument(
        "--include-calibration-allows",
        action="store_true",
        help="Also export near-miss allow calibration rows (opt-in; default off)",
    )
    export_cmd.add_argument(
        "--calibration-only",
        action="store_true",
        help="Export only calibration allows (skips approved blocks)",
    )
    export_cmd.add_argument(
        "--store",
        default="",
        help="Feedback store path (default: PRISMGUARD_FEEDBACK_PATH or .prismguard/feedback.json)",
    )
    export_cmd.add_argument("--backend", default=None, help="Storage backend (default memory)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.feedback_command == "export":
        return cmd_export(args)
    parser.error(f"Unknown feedback command {args.feedback_command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
