"""CLI for PrismGuard Guard Model artifacts: export, train, corpus stats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prismguard-model",
        description="PrismGuard Guard Model artifact management",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export_cmd = sub.add_parser("export", help="Export a HuggingFace checkpoint to ONNX")
    export_cmd.add_argument("--base-model", default="ProtectAI/deberta-v3-base-prompt-injection")
    export_cmd.add_argument("--artifact-id", default="prism-pi-v1")
    export_cmd.add_argument("--output-dir", default="")
    export_cmd.add_argument("--max-length", type=int, default=512)

    train_cmd = sub.add_parser("train", help="Fine-tune on seed DB + optional feedback")
    train_cmd.add_argument("--base-model", default="ProtectAI/deberta-v3-base-prompt-injection")
    train_cmd.add_argument("--artifact-id", default="prism-pi-v1")
    train_cmd.add_argument("--profile", default="full", choices=["authored", "full"])
    train_cmd.add_argument("--from-storage", action="store_true")
    train_cmd.add_argument("--storage-backend", default="")
    train_cmd.add_argument("--epochs", type=int, default=1)
    train_cmd.add_argument("--batch-size", type=int, default=8)
    train_cmd.add_argument("--learning-rate", type=float, default=2e-5)
    train_cmd.add_argument("--max-length", type=int, default=256)
    train_cmd.add_argument("--max-train-examples", type=int, default=0)
    train_cmd.add_argument("--feedback-jsonl", action="append", default=[])
    train_cmd.add_argument("--output-dir", default="")

    stats_cmd = sub.add_parser("corpus-stats", help="Show training corpus size from seed DB")
    stats_cmd.add_argument("--profile", default="full", choices=["authored", "full"])
    stats_cmd.add_argument("--from-storage", action="store_true")
    stats_cmd.add_argument("--storage-backend", default="")
    stats_cmd.add_argument("--feedback-jsonl", action="append", default=[])

    args = parser.parse_args(argv)
    if args.command == "export":
        from prismguard.models.export import main as export_main

        export_argv = [
            "--base-model",
            args.base_model,
            "--artifact-id",
            args.artifact_id,
            "--max-length",
            str(args.max_length),
        ]
        if args.output_dir:
            export_argv.extend(["--output-dir", args.output_dir])
        return export_main(export_argv)

    if args.command == "train":
        from prismguard.models.train import main as train_main

        train_argv = [
            "--base-model",
            args.base_model,
            "--artifact-id",
            args.artifact_id,
            "--profile",
            args.profile,
            "--epochs",
            str(args.epochs),
            "--batch-size",
            str(args.batch_size),
            "--learning-rate",
            str(args.learning_rate),
            "--max-length",
            str(args.max_length),
            "--max-train-examples",
            str(args.max_train_examples),
        ]
        if args.from_storage:
            train_argv.append("--from-storage")
        if args.storage_backend:
            train_argv.extend(["--storage-backend", args.storage_backend])
        for path in args.feedback_jsonl:
            train_argv.extend(["--feedback-jsonl", path])
        if args.output_dir:
            train_argv.extend(["--output-dir", args.output_dir])
        return train_main(train_argv)

    if args.command == "corpus-stats":
        from prismguard.models.train import print_corpus_stats

        manifest = print_corpus_stats(
            profile=args.profile,
            feedback_paths=[Path(p) for p in args.feedback_jsonl],
            from_storage=args.from_storage,
            storage_backend=args.storage_backend,
        )
        return 0 if manifest.total_examples > 0 else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
