"""Ensure the PrismGuard checkout is importable when running examples as files.

Usage (first import in each example)::

    import _repo_path  # noqa: F401
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
