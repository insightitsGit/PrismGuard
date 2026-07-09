from __future__ import annotations

from typing import Literal

GuardModelDecision = Literal["block", "allow", "uncertain"]


def injection_probability_to_decision(
    injection_probability: float,
    *,
    uncertain_low: float,
    uncertain_high: float,
) -> GuardModelDecision:
    if uncertain_low <= injection_probability <= uncertain_high:
        return "uncertain"
    if injection_probability > uncertain_high:
        return "block"
    return "allow"
