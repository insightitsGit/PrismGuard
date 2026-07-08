"""Shared Guard Model training and inference constants."""

DEFAULT_MAX_LENGTH = 256

# Categories under-represented in the full seed; oversample during law-focused training.
THIN_ATTACK_CATEGORIES = (
    "refusal_suppression",
    "data_exfiltration_via_output",
    "system_prompt_exfiltration",
    "multi_turn_escalation",
    "payload_splitting",
    "indirect_injection",
    "context_overflow",
)
