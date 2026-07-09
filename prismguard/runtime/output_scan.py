from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

OutputDecision = Literal["allow", "block"]


@dataclass(frozen=True)
class OutputScanResult:
    decision: OutputDecision
    matched_pattern: str | None
    details: dict
    resolution_gate: str


_URL_PATTERN = re.compile(r"https?://[^\s\])>]+", re.IGNORECASE)
_EMAIL_EXFIL_PATTERN = re.compile(
    r"\b(?:email|send|post|transmit)\b.{0,40}\b(?:@|mailto:)",
    re.IGNORECASE,
)
_BASE64_BLOB_PATTERN = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")
_MARKDOWN_EXFIL_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*(?:exfil|leak|attacker)[^)]*\)", re.IGNORECASE)
_JSON_LEAK_PATTERN = re.compile(r'\{\s*"(?:ssn|mrn|account|matter|client)[^"]*"\s*:', re.IGNORECASE)


def scan_output(text: str, *, max_base64_len: int = 120) -> OutputScanResult:
    """Post-generation exfiltration scan (Phase 4 output-side guard)."""
    if not text or not text.strip():
        return OutputScanResult(
            decision="allow",
            matched_pattern=None,
            details={},
            resolution_gate="output_allow",
        )

    checks: list[tuple[str, bool]] = [
        ("markdown_exfil_link", bool(_MARKDOWN_EXFIL_PATTERN.search(text))),
        ("json_structured_leak", bool(_JSON_LEAK_PATTERN.search(text))),
        ("email_exfil_instruction", bool(_EMAIL_EXFIL_PATTERN.search(text))),
    ]
    for match in _URL_PATTERN.finditer(text):
        url = match.group(0).lower()
        if any(token in url for token in ("exfil", "leak", "attacker", "evil.", "proton.me")):
            checks.append(("suspicious_url", True))
            break

    for match in _BASE64_BLOB_PATTERN.finditer(text):
        if len(match.group(0)) >= max_base64_len:
            checks.append(("large_base64_blob", True))
            break

    for name, hit in checks:
        if hit:
            return OutputScanResult(
                decision="block",
                matched_pattern=name,
                details={"pattern": name, "sample": text[:240]},
                resolution_gate="output_pattern",
            )
    return OutputScanResult(
        decision="allow",
        matched_pattern=None,
        details={},
        resolution_gate="output_allow",
    )
