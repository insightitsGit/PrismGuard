"""
Train hub/general ONNX artifact (opt-in).

Default production still uses prism-pi-v1 (law proof) only when
PRISMGUARD_USE_ONNX=1. This script builds prism-pi-hub-v1 for hubs.

Usage:
  python scripts/train_prism_pi_hub.py
  python scripts/train_prism_pi_hub.py --max-train-examples 4000  # faster smoke

Gates (post-train, run separately if GPU train is remote):
  prismguard-model eval --domain general --artifact-id prism-pi-hub-v1 \\
    --normal-txt benchmark/hub/benign_faq.txt
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train prism-pi-hub-v1 (opt-in hub artifact)")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-train-examples", type=int, default=0)
    parser.add_argument("--output-dir", default="")
    parser.add_argument(
        "--base-model",
        default="ProtectAI/deberta-v3-base-prompt-injection",
    )
    args = parser.parse_args(argv)

    out = args.output_dir or str(
        Path("prismguard/models/artifacts/prism-pi-hub-v1").resolve()
    )
    cmd = [
        sys.executable,
        "-m",
        "prismguard.models.cli",
        "train",
        "--profile",
        "full",
        "--artifact-id",
        "prism-pi-hub-v1",
        "--domain-pack",
        "general",
        "--holdout-domain",
        "general",
        "--normal-txt",
        "benchmark/hub/benign_faq.txt",
        "--holdout-early-stop",
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--base-model",
        args.base_model,
        "--output-dir",
        out,
    ]
    if args.max_train_examples > 0:
        cmd.extend(["--max-train-examples", str(args.max_train_examples)])
    print("Running:", " ".join(cmd))
    print(
        "Note: domain-pack general is OPT-IN. Default train (no --domain-pack) "
        "uses bundled seed only; runtime default artifact remains prism-pi-v1."
    )
    code = subprocess.call(cmd)
    if code != 0:
        return code

    eval_cmd = [
        sys.executable,
        "-m",
        "prismguard.models.cli",
        "eval",
        "--domain",
        "general",
        "--artifact-path",
        out,
        "--normal-txt",
        "benchmark/hub/benign_faq.txt",
        "--json",
    ]
    print("Evaluating hub gates:", " ".join(eval_cmd))
    return subprocess.call(eval_cmd)


if __name__ == "__main__":
    raise SystemExit(main())
