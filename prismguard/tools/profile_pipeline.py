"""CLI: ``prismguard-profile`` — quick pipeline stage latency report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_script() -> Path | None:
    """Locate scripts/profile_pipeline_latency.py in a source checkout (not in the wheel)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "scripts" / "profile_pipeline_latency.py",  # editable / source tree
        Path.cwd() / "scripts" / "profile_pipeline_latency.py",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _wheel_help_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="prismguard-profile",
        description=(
            "Pipeline stage latency profiler. "
            "Full profiling requires a source checkout with scripts/ and benchmark data; "
            "the PyPI wheel only exposes this help entry point."
        ),
    )


def main() -> None:
    script = _repo_script()
    if script is None:
        parser = _wheel_help_parser()
        parser.parse_args()  # handles --help / -h with exit 0
        raise SystemExit(
            "prismguard-profile requires a source checkout "
            "(scripts/profile_pipeline_latency.py is not shipped in the wheel)."
        )

    sys.argv[0] = str(script)
    import runpy

    runpy.run_path(str(script), run_name="__main__")
