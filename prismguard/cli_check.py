"""Human-readable `prismguard check` output for CLI and README examples."""

from __future__ import annotations

from typing import Any

from prismguard.runtime.check import CheckResult, RuntimeChecker

_PRISM_HINT = (
    "prismguard check needs the rules engine seed (bundled) and works without "
    "[prism] in rules-only mode. For full taxonomy / graph extras install: "
    "pip install \"prismguard[prism]\""
)


def _checker() -> RuntimeChecker:
    """CLI uses the dogfood-safe env factory (ONNX opt-in, web_chat default)."""
    from prismguard.runtime.factory import create_checker_from_env

    try:
        return create_checker_from_env()
    except ImportError as exc:
        # Belt-and-suspenders: never dump a raw ImportError traceback for the
        # headline command on a bare pip install.
        msg = str(exc).strip() or "missing optional dependency"
        if "prismrag" in msg.lower() or "prismguard[prism]" in msg.lower():
            raise SystemExit(
                f"prismguard check: {msg}\n"
                f"Install the prism extra, or use rules-only: set PRISMGUARD_APP_PROFILE=web_chat\n"
                f"  pip install \"prismguard[prism]\"\n"
                f"({_PRISM_HINT})"
            ) from exc
        raise SystemExit(f"prismguard check: {msg}\n{_PRISM_HINT}") from exc


def format_check_result(result: CheckResult) -> str:
    details: dict[str, Any] = result.details or {}
    source = details.get("decision_source", "")
    confidence = details.get("guard_model_confidence") or details.get("classifier_prob")
    lines = [
        "ALLOW" if result.decision == "allow" else "BLOCKED",
        f"resolution_gate={result.resolution_gate}",
    ]
    if source:
        # ASCII-safe for Windows cp1252 consoles (decision_source uses "→" internally).
        lines.append(f"decision_source={str(source).replace(chr(0x2192), '->')}")
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
