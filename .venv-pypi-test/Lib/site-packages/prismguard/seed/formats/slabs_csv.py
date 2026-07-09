from __future__ import annotations

import re
from pathlib import Path

from prismguard.seed.models import EntrySeed, ParsedSeed

_BENIGN = "benign_adjacent"
_STAGING = "unclassified_imported"

_REFUSAL = re.compile(
    r"never (refuse|apologize|say you can)|must comply|no matter what|always comply",
    re.IGNORECASE,
)
_EXFIL = re.compile(
    r"markdown image|base64.*(response|reply|output)|session token|api key.*(url|response)|"
    r"exfiltrat|leak.*(secret|token|password)",
    re.IGNORECASE,
)
_SPLIT = re.compile(
    r"part \d of \d|execute [A-Z][\.\s]|variable [A-Z]|call the value in part",
    re.IGNORECASE,
)


def _classify_attack_text(text: str) -> tuple[str, str]:
    """Heuristic re-label for binary injection rows — fills taxonomy gaps safely."""
    if _REFUSAL.search(text):
        return "refusal_suppression", "high"
    if _EXFIL.search(text):
        return "data_exfiltration_via_output", "high"
    if _SPLIT.search(text):
        return "payload_splitting", "medium"
    return _STAGING, "medium"


def parse_slabs_csv(path: Path) -> ParsedSeed:
    """S-Labs/prompt-injection-dataset: columns text,label (0=benign, 1=injection)."""
    import csv

    entries: list[EntrySeed] = []
    source = f"s-labs-{path.stem}"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "text" not in reader.fieldnames or "label" not in reader.fieldnames:
            raise ValueError(f"S-Labs CSV must have text,label columns: {path}")
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            label = (row.get("label") or "").strip()
            if label == "0":
                category_slug = _BENIGN
                severity = "low"
            else:
                category_slug, severity = _classify_attack_text(text)
            entries.append(
                EntrySeed(
                    text=text,
                    category_slug=category_slug,
                    severity=severity,  # type: ignore[arg-type]
                    source=source,
                )
            )
    return ParsedSeed(entries=entries)
