"""Human-readable `prismguard check` output for CLI and README examples."""

from __future__ import annotations

from typing import Any

from prismguard.runtime.check import CheckResult, RuntimeChecker


def _checker() -> RuntimeChecker:
    """CLI uses the same dogfood-safe env factory (ONNX opt-in, domain not law-by-default)."""
    from prismguard.runtime.factory import create_checker_from_env

    return create_checker_from_env()


def format_check_result(result: CheckResult) -> str:
    details: dict[str, Any] = result.details or {}
    source = details.get("decision_source", "")
    confidence = details.get("guard_model_confidence") or details.get("classifier_prob")
    lines = [
        "ALLOW" if result.decision == "allow" else "BLOCKED",
        f"resolution_gate={result.resolution_gate}",
    ]
    if source:
        lines.append(f"decision_source={source}")
    if confidence is not None:
        lines.append(f"confidence={round(float(confidence), 4)}")
    if result.matched_category:
        lines.append(f"matched_category={result.matched_category}")
    shadow = details.get("shadow_onnx")
    if isinstance(shadow, dict):
        lines.append(f"shadow_onnx={shadow.get('decision', shadow.get('error', 'n/a'))}")
    return "\n".join(lines)


def run_check(text: str) -> CheckResult:
    checker = _checker()
    try:
        return checker.check(text)
    finally:
        storage = getattr(checker, "_storage", None)
        if storage is None and hasattr(checker, "_enforce"):
            storage = getattr(checker._enforce, "_storage", None)  # noqa: SLF001
        if storage is not None:
            storage.close()
