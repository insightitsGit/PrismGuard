"""CLI: ``prismguard-profile`` — quick pipeline stage latency report."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "profile_pipeline_latency.py"
    sys.argv[0] = str(script)
    import runpy

    runpy.run_path(str(script), run_name="__main__")
