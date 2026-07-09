"""Phase 3: train DistilBERT fast artifact (128 tokens) with optional INT8 export."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    train_cmd = [
        sys.executable,
        "-m",
        "prismguard.models.cli",
        "train",
        "--profile",
        "full",
        "--artifact-id",
        "prism-pi-v2-fast",
        "--base-model",
        "distilbert-base-uncased",
        "--max-length",
        "128",
        "--law-pack",
        "--oversample-law",
        "--focal-loss",
        "--holdout-early-stop",
        "--holdout-domain",
        "law",
    ]
    print("Running:", " ".join(train_cmd))
    rc = subprocess.call(train_cmd)
    if rc != 0:
        return rc
    export_cmd = [
        sys.executable,
        "-m",
        "prismguard.models.export",
        "--base-model",
        "prismguard/models/artifacts/prism-pi-v2-fast-hf",
        "--artifact-id",
        "prism-pi-v2-fast",
        "--max-length",
        "128",
        "--quantize-int8",
    ]
    print("Running:", " ".join(export_cmd))
    return subprocess.call(export_cmd)


if __name__ == "__main__":
    raise SystemExit(main())
