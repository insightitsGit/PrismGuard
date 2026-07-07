from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from prismguard.seed import load_bundled_seed
from prismguard.seed.parse import parse_seed_file

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_SEEDED_OVERLAY = _DATA_DIR / "legal_attacks.yaml"
_HOLDOUT_OVERLAY = _DATA_DIR / "legal_attacks_holdout.yaml"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _texts_from_yaml(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    entries = raw.get("entries") or raw.get("scenarios") or []
    texts: set[str] = set()
    for row in entries:
        text = row.get("text")
        if text:
            texts.add(_normalize(text))
    return texts


def prismguard_seeded_texts() -> set[str]:
    """Texts imported into PrismGuardGate at container init (authored + legal overlay)."""
    authored = {_normalize(entry.canonical_text()) for entry in load_bundled_seed(profile="authored").entries}
    overlay = _texts_from_yaml(_SEEDED_OVERLAY)
    return authored | overlay


def bundled_full_texts() -> set[str]:
    return {_normalize(entry.canonical_text()) for entry in load_bundled_seed(profile="full").entries}


def bundled_full_minus_authored() -> set[str]:
    authored = {_normalize(entry.canonical_text()) for entry in load_bundled_seed(profile="authored").entries}
    return bundled_full_texts() - authored


def holdout_attack_texts() -> set[str]:
    return _texts_from_yaml(_HOLDOUT_OVERLAY)


@dataclass(frozen=True)
class OverlapReport:
    holdout_vs_prismguard_seed: list[str]
    holdout_vs_seeded_overlay: list[str]
    bundled_full_vs_authored_count: int
    bundled_full_minus_authored_count: int

    @property
    def holdout_clean(self) -> bool:
        return not self.holdout_vs_prismguard_seed and not self.holdout_vs_seeded_overlay


def verify_holdout_overlap() -> OverlapReport:
    seeded = prismguard_seeded_texts()
    holdout = holdout_attack_texts()
    seeded_overlay = _texts_from_yaml(_SEEDED_OVERLAY)
    full = bundled_full_texts()
    authored = {_normalize(entry.canonical_text()) for entry in load_bundled_seed(profile="authored").entries}
    return OverlapReport(
        holdout_vs_prismguard_seed=sorted(holdout & seeded),
        holdout_vs_seeded_overlay=sorted(holdout & seeded_overlay),
        bundled_full_vs_authored_count=len(full & authored),
        bundled_full_minus_authored_count=len(full - authored),
    )
