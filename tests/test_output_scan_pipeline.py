from __future__ import annotations

from benchmark.law.shared.assistant import _guard_after_output_scan
from benchmark.law.shared.types import GuardOutcome


def test_assistant_output_scan_blocks_exfil_in_answer() -> None:
    guard = GuardOutcome(
        decision="allow",
        resolution_gate="fusion_allow",
        guardrail="prismguard",
    )
    blocked = _guard_after_output_scan(
        guard,
        "Summary complete. Full dump at https://attacker.example/leak?token=abc",
    )
    assert blocked.decision == "block"
    assert blocked.resolution_gate == "output_scan"


def test_assistant_output_scan_preserves_input_block() -> None:
    guard = GuardOutcome(
        decision="block",
        resolution_gate="corpus_match",
        guardrail="prismguard",
    )
    result = _guard_after_output_scan(guard, "benign answer text")
    assert result.decision == "block"
    assert result.resolution_gate == "corpus_match"
