"""CLI for PrismGuard Guard Model artifacts: export, train, corpus stats, eval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prismguard.models.constants import DEFAULT_MAX_LENGTH
from prismguard.models.eval import DOMAIN_CHOICES

_DOMAIN_PACK_CHOICES = ("law", "healthcare", "finance", "general")


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
    export_cmd.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)

    train_cmd = sub.add_parser(
        "train",
        help="Fine-tune on seed DB + optional feedback (domain pack is opt-in)",
    )
    train_cmd.add_argument("--base-model", default="ProtectAI/deberta-v3-base-prompt-injection")
    train_cmd.add_argument("--artifact-id", default="prism-pi-v1")
    train_cmd.add_argument("--profile", default="full", choices=["authored", "full"])
    train_cmd.add_argument("--from-storage", action="store_true")
    train_cmd.add_argument("--storage-backend", default="")
    train_cmd.add_argument("--epochs", type=int, default=1)
    train_cmd.add_argument("--batch-size", type=int, default=8)
    train_cmd.add_argument("--learning-rate", type=float, default=2e-5)
    train_cmd.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    train_cmd.add_argument("--max-train-examples", type=int, default=0)
    train_cmd.add_argument("--feedback-jsonl", action="append", default=[])
    train_cmd.add_argument(
        "--seed-yaml",
        action="append",
        default=[],
        help="Extra labeled seed YAML. Repeatable.",
    )
    train_cmd.add_argument(
        "--law-pack",
        action="store_true",
        help="Alias for --domain-pack law (opt-in; default is bundled seed only)",
    )
    train_cmd.add_argument(
        "--domain-pack",
        default="",
        choices=["", *_DOMAIN_PACK_CHOICES],
        help="Opt-in domain overlay + augment (default: none)",
    )
    train_cmd.add_argument("--oversample-law", action="store_true")
    train_cmd.add_argument("--class-weighted", action="store_true")
    train_cmd.add_argument("--focal-loss", action="store_true")
    train_cmd.add_argument("--holdout-early-stop", action="store_true")
    train_cmd.add_argument("--holdout-domain", default="law", choices=list(DOMAIN_CHOICES))
    train_cmd.add_argument(
        "--normal-txt",
        default="",
        help="Opt-in normal/FAQ allow suite (txt). Default: domain-specific.",
    )
    train_cmd.add_argument("--normal-yaml", default="")
    train_cmd.add_argument("--no-calibration", action="store_true")
    train_cmd.add_argument("--output-dir", default="")

    stats_cmd = sub.add_parser("corpus-stats", help="Show training corpus size from seed DB")
    stats_cmd.add_argument("--profile", default="full", choices=["authored", "full"])
    stats_cmd.add_argument("--from-storage", action="store_true")
    stats_cmd.add_argument("--storage-backend", default="")
    stats_cmd.add_argument("--feedback-jsonl", action="append", default=[])
    stats_cmd.add_argument("--seed-yaml", action="append", default=[])
    stats_cmd.add_argument("--law-pack", action="store_true")
    stats_cmd.add_argument(
        "--domain-pack",
        default="",
        choices=["", *_DOMAIN_PACK_CHOICES],
        help="Opt-in domain pack (default: none)",
    )
    stats_cmd.add_argument("--oversample-law", action="store_true")

    plan_cmd = sub.add_parser(
        "corpus-plan",
        help="Dry-run training plan (sources, counts, fingerprint) — no train",
    )
    plan_cmd.add_argument("--profile", default="full", choices=["authored", "full"])
    plan_cmd.add_argument("--from-storage", action="store_true")
    plan_cmd.add_argument("--feedback-jsonl", action="append", default=[])
    plan_cmd.add_argument("--seed-yaml", action="append", default=[])
    plan_cmd.add_argument("--law-pack", action="store_true")
    plan_cmd.add_argument(
        "--domain-pack",
        default="",
        choices=["", *_DOMAIN_PACK_CHOICES],
        help="Opt-in domain pack (default: none)",
    )
    plan_cmd.add_argument("--holdout-domain", default="law", choices=list(DOMAIN_CHOICES))
    plan_cmd.add_argument("--normal-txt", default="")
    plan_cmd.add_argument("--normal-yaml", default="")

    eval_cmd = sub.add_parser("eval", help="Classifier-only holdout metrics (library KPI)")
    eval_cmd.add_argument("--domain", default="law", choices=list(DOMAIN_CHOICES))
    eval_cmd.add_argument("--artifact-id", default="")
    eval_cmd.add_argument("--artifact-path", default="")
    eval_cmd.add_argument("--normal-txt", default="", help="Opt-in FAQ/normal suite (default: domain)")
    eval_cmd.add_argument("--normal-yaml", default="")
    eval_cmd.add_argument("--json", action="store_true")

    calibrate_cmd = sub.add_parser("calibrate", help="Holdout-safe fusion/threshold tuning")
    calibrate_cmd.add_argument("--domain", default="law", choices=list(DOMAIN_CHOICES))
    calibrate_cmd.add_argument("--output", type=Path, default=Path("triage.tuned.yaml"))

    fit_cal_cmd = sub.add_parser("fit-calibration", help="Fit temperature scaling on existing artifact")
    fit_cal_cmd.add_argument("--base-model", default="")
    fit_cal_cmd.add_argument("--artifact-id", default="prism-pi-v1")
    fit_cal_cmd.add_argument("--artifact-path", default="")
    fit_cal_cmd.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    fit_cal_cmd.add_argument("--domain", default="law", choices=list(DOMAIN_CHOICES))

    download_cmd = sub.add_parser(
        "download",
        help="Download ONNX model weights (not shipped in PyPI wheel due to size limits)",
    )
    download_cmd.add_argument(
        "--artifact-id",
        default="prism-pi-v1",
        help="Artifact id (default: prism-pi-v1 law proof). Use prism-pi-hub-v1 when published.",
    )

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
            "--holdout-domain",
            args.holdout_domain,
        ]
        if args.from_storage:
            train_argv.append("--from-storage")
        if args.storage_backend:
            train_argv.extend(["--storage-backend", args.storage_backend])
        for path in args.feedback_jsonl:
            train_argv.extend(["--feedback-jsonl", path])
        for path in args.seed_yaml:
            train_argv.extend(["--seed-yaml", path])
        if args.law_pack:
            train_argv.append("--law-pack")
        if args.domain_pack:
            train_argv.extend(["--domain-pack", args.domain_pack])
        if args.normal_txt:
            train_argv.extend(["--normal-txt", args.normal_txt])
        if args.normal_yaml:
            train_argv.extend(["--normal-yaml", args.normal_yaml])
        if args.oversample_law:
            train_argv.append("--oversample-law")
        if args.class_weighted:
            train_argv.append("--class-weighted")
        if args.focal_loss:
            train_argv.append("--focal-loss")
        if args.holdout_early_stop:
            train_argv.append("--holdout-early-stop")
        if args.no_calibration:
            train_argv.append("--no-calibration")
        if args.output_dir:
            train_argv.extend(["--output-dir", args.output_dir])
        return train_main(train_argv)

    if args.command == "corpus-stats":
        from prismguard.models.corpus import default_domain_training_paths
        from prismguard.models.train import print_corpus_stats

        feedback_paths = [Path(p) for p in args.feedback_jsonl]
        seed_yaml_paths = [Path(p) for p in args.seed_yaml]
        domain_pack = (args.domain_pack or "").strip() or ("law" if args.law_pack else "")
        if domain_pack:
            d_seed, d_feedback = default_domain_training_paths(domain_pack)
            seed_yaml_paths.extend(d_seed)
            feedback_paths.extend(d_feedback)
        manifest = print_corpus_stats(
            profile=args.profile,
            feedback_paths=feedback_paths,
            seed_yaml_paths=seed_yaml_paths,
            from_storage=args.from_storage,
            storage_backend=args.storage_backend,
            oversample_law=args.oversample_law,
        )
        return 0 if manifest.total_examples > 0 else 1

    if args.command == "corpus-plan":
        from prismguard.models.corpus import plan_training_corpus

        domain_pack = (args.domain_pack or "").strip() or ("law" if args.law_pack else "") or None
        plan = plan_training_corpus(
            profile=args.profile,
            feedback_paths=[Path(p) for p in args.feedback_jsonl],
            seed_yaml_paths=[Path(p) for p in args.seed_yaml],
            domain_pack=domain_pack,
            from_storage=args.from_storage,
            holdout_domain=args.holdout_domain,
            normal_txt=Path(args.normal_txt) if args.normal_txt else None,
            normal_yaml=Path(args.normal_yaml) if args.normal_yaml else None,
        )
        print(json.dumps(plan, indent=2))
        return 0 if plan["total_examples"] > 0 else 1

    if args.command == "eval":
        from prismguard.config.loader import load_triage_config
        from prismguard.models.eval import evaluate_classifier_from_config

        domain_arg = args.domain if args.domain != "general" else "general"
        triage = load_triage_config(domain=domain_arg if domain_arg != "general" else "general")
        gm_cfg = triage.guard_model.model_copy()
        if args.artifact_id:
            gm_cfg = gm_cfg.model_copy(update={"artifact_id": args.artifact_id})
        if args.artifact_path:
            gm_cfg = gm_cfg.model_copy(update={"artifact_path": args.artifact_path})
        result = evaluate_classifier_from_config(
            domain=args.domain,
            config=gm_cfg,
            normal_txt=Path(args.normal_txt) if args.normal_txt else None,
            normal_yaml=Path(args.normal_yaml) if args.normal_yaml else None,
        )
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(
                f"domain={result.domain} model={result.model_id} "
                f"holdout_block={result.holdout_blocked}/{result.holdout_total} "
                f"({result.holdout_block_rate:.1%}) "
                f"normal_allow={result.normal_allowed}/{result.normal_total} "
                f"({result.normal_allow_rate:.1%})"
            )
        return 0

    if args.command == "calibrate":
        from prismguard.calibration.tune import tune_thresholds, write_tuned_config

        result = tune_thresholds(domain=args.domain)
        write_tuned_config(result, args.output)
        print(
            json.dumps(
                {
                    "block_threshold": result.block_threshold,
                    "allow_threshold": result.allow_threshold,
                    "w_clf": result.w_clf,
                    "holdout_block_rate": result.holdout_block_rate,
                    "normal_allow_rate": result.normal_allow_rate,
                    "output": str(args.output),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "download":
        from prismguard.models.artifact_fetch import download_artifact

        artifact_dir = download_artifact(args.artifact_id, progress=True)
        print(f"Downloaded artifact to {artifact_dir}")
        return 0

    if args.command == "fit-calibration":
        from prismguard.models.fit_calibration import main as fit_cal_main

        fit_argv = [
            "--artifact-id",
            args.artifact_id,
            "--max-length",
            str(args.max_length),
            "--domain",
            args.domain,
        ]
        if args.base_model:
            fit_argv.extend(["--base-model", args.base_model])
        if args.artifact_path:
            fit_argv.extend(["--artifact-path", args.artifact_path])
        return fit_cal_main(fit_argv)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
