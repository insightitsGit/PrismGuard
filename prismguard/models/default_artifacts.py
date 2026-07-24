"""Optional starter ONNX defaults (law / finance / healthcare).

These are convenience downloads for users without their own labeled DB.
They do **not** guarantee accuracy on production traffic — train on your
feedback for real gates, then use ``domain_pilot`` + your artifact id.
"""

from __future__ import annotations

from typing import TypedDict


class DefaultArtifactInfo(TypedDict):
    artifact_id: str
    domain: str
    label: str
    accuracy_guarantee: bool
    notes: str


# Starter defaults only — never claim scorecard / PI rates from these alone
# on a customer's unseen traffic.
DEFAULT_ARTIFACTS: dict[str, DefaultArtifactInfo] = {
    "law": {
        "artifact_id": "prism-pi-v1",
        "domain": "law",
        "label": "Law / compliance starter",
        "accuracy_guarantee": False,
        "notes": "Published law-bench proof default. Still retrain for your legal product traffic.",
    },
    "finance": {
        "artifact_id": "prism-pi-finance-v1",
        "domain": "finance",
        "label": "Finance / FX / FAQ starter",
        "accuracy_guarantee": False,
        "notes": "Optional finance starter. Prefer train on your bank/FAQ feedback for production.",
    },
    "healthcare": {
        "artifact_id": "prism-pi-healthcare-v1",
        "domain": "healthcare",
        "label": "Healthcare / HIPAA-theme starter",
        "accuracy_guarantee": False,
        "notes": "Optional healthcare starter. Prefer train on your clinical traffic for production.",
    },
}

DEFAULT_ARTIFACT_IDS: tuple[str, ...] = tuple(
    info["artifact_id"] for info in DEFAULT_ARTIFACTS.values()
)


def resolve_default_artifact_id(name_or_id: str) -> str:
    """Map domain shortcut (law|finance|healthcare) or artifact id → artifact id."""
    key = (name_or_id or "").strip().lower()
    if not key:
        return DEFAULT_ARTIFACTS["law"]["artifact_id"]
    if key in DEFAULT_ARTIFACTS:
        return DEFAULT_ARTIFACTS[key]["artifact_id"]
    if key in DEFAULT_ARTIFACT_IDS:
        return key
    # Allow custom ids through unchanged (customer train).
    return name_or_id.strip()


def format_default_artifacts_help() -> str:
    lines = [
        "Optional starter defaults (NO accuracy guarantee on your traffic):",
        "  Prefer: train on your DB -> domain_pilot + prism-pi-<your-slug>-v1",
        "",
    ]
    for domain, info in DEFAULT_ARTIFACTS.items():
        lines.append(
            f"  {domain:12} -> {info['artifact_id']}  ({info['label']})"
        )
    lines.append("")
    lines.append(
        "Download: prismguard-model download --artifact-id prism-pi-finance-v1"
    )
    lines.append("       or: prismguard-model download --domain finance")
    return "\n".join(lines)
