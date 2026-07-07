from __future__ import annotations

import re
from pathlib import Path

from prismguard.seed.models import EntrySeed, ParsedSeed

# Verified against core-train.parquet category column (2026-07-06).
NEURALCHEMY_TO_PRISM: dict[str, str] = {
    "benign": "benign_adjacent",
    "direct_injection": "direct_instruction_override",
    "instruction_override": "direct_instruction_override",
    "prompt_injection": "direct_instruction_override",
    "jailbreak": "roleplay_jailbreak",
    "persona_replacement": "roleplay_jailbreak",
    "system_extraction": "system_prompt_exfiltration",
    "prompt_extraction": "system_prompt_exfiltration",
    "prompt_leak": "system_prompt_exfiltration",
    "training_extraction": "system_prompt_exfiltration",
    "model_fingerprinting": "system_prompt_exfiltration",
    "encoding": "encoding_obfuscation",
    "encoding_obfuscation": "encoding_obfuscation",
    "token_smuggling": "encoding_obfuscation",
    "token_injection": "encoding_obfuscation",
    "crescendo": "multi_turn_escalation",
    "many_shot": "multi_turn_escalation",
    "multi_turn": "multi_turn_escalation",
    "indirect_injection": "indirect_injection",
    "rag_poisoning": "indirect_injection",
    "agent_manipulation": "indirect_injection",
    "context_confusion": "context_overflow",
    "output_manipulation": "data_exfiltration_via_output",
    "response_manipulation": "data_exfiltration_via_output",
    "payload_injection": "payload_splitting",
    "system_manipulation": "direct_instruction_override",
    "adversarial": "unclassified_imported",
    "edge_case": "unclassified_imported",
    "control": "unclassified_imported",
    "code_execution": "unclassified_imported",
    "chain_of_thought": "unclassified_imported",
}

_SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def parse_neuralchemy_parquet(path: Path) -> ParsedSeed:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError(
            "neuralchemy parquet import requires pyarrow — install with: pip install prismguard[seed]"
        ) from exc

    table = pq.read_table(path)
    rows = table.to_pylist()
    source = f"neuralchemy-{path.stem}"
    entries: list[EntrySeed] = []

    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        raw_category = (row.get("category") or "").strip()
        category_slug = NEURALCHEMY_TO_PRISM.get(raw_category, "unclassified_imported")
        raw_severity = (row.get("severity") or "medium").strip().lower()
        severity = _SEVERITY_MAP.get(raw_severity, "medium")
        label = row.get("label")
        if label == 0 and category_slug != "benign_adjacent":
            category_slug = "benign_adjacent"
            severity = "low"
        notes = None
        if raw_category not in NEURALCHEMY_TO_PRISM:
            notes = f"unmapped neuralchemy category: {raw_category}"
        elif raw_category != category_slug:
            notes = f"neuralchemy:{raw_category}"
        entries.append(
            EntrySeed(
                text=text,
                category_slug=category_slug,
                severity=severity,  # type: ignore[arg-type]
                source=source,
                notes=notes,
            )
        )

    return ParsedSeed(entries=entries)
