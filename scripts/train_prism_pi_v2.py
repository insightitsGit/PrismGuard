"""Phase 1 retrain: focal loss + law oversample + holdout early-stop → prism-pi-v2."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "prismguard.models.cli",
        "train",
        "--profile",
        "full",
        "--artifact-id",
        "prism-pi-v2",
        "--law-pack",
        "--oversample-law",
        "--focal-loss",
        "--holdout-early-stop",
        "--holdout-domain",
        "law",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
