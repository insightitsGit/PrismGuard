"""Phase 2: fine-tune from prism-pi-v2 (or v1) with law hard negatives."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    base = "prismguard/models/artifacts/prism-pi-v2-hf"
    if not Path(base).is_dir():
        base = "prismguard/models/artifacts/prism-pi-v1-hf"
    feedback = "benchmark/law/data/law_benign_hard_negatives.jsonl"
    cmd = [
        sys.executable,
        "-m",
        "prismguard.models.cli",
        "train",
        "--profile",
        "full",
        "--artifact-id",
        "prism-pi-v2-hn",
        "--base-model",
        base,
        "--feedback-jsonl",
        feedback,
        "--law-pack",
        "--oversample-law",
        "--focal-loss",
        "--holdout-early-stop",
        "--epochs",
        "1",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
