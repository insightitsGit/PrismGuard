"""Fit temperature calibration on law holdout + normals for the active artifact."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "prismguard.models.fit_calibration",
        "--artifact-id",
        "prism-pi-v1",
        "--base-model",
        "prismguard/models/artifacts/prism-pi-v1-hf",
        "--domain",
        "law",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
