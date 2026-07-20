"""Capability / readiness snapshot so integrators cannot claim scorecard parity on a half-stack."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from prismguard.runtime.factory import (
    AppProfile,
    env_flag,
    normalize_app_profile,
    offline_mode,
    onnx_opt_in,
)


_HASH_ONLY_PROFILES = frozenset(
    {"web_chat", "rules_only", "security_bench", "sidecar", "low_latency"}
)

_PROFILE_CLASSIFIER_MODE = {
    "security_bench": "first",  # heavy
    "low_latency": "hybrid",  # light
    "web_chat": "off",
    "rules_only": "off",
}


def _default_profile() -> str:
    raw = os.environ.get("PRISMGUARD_APP_PROFILE", "").strip().lower()
    return raw or "web_chat"


def _domain_overlay() -> str | None:
    raw = os.environ.get("PRISMGUARD_DOMAIN", "").strip()
    if not raw or raw.lower() in ("none", "general", "core", "-"):
        return None
    return raw


def _taxonomy_status(profile: str) -> tuple[bool, str]:
    """Whether seed import will build prismrag taxonomy / word-graph for this profile."""
    from prismguard.taxonomy.mapping import has_prismrag

    if not has_prismrag():
        return False, "missing [prism] extra (pip install \"prismguard[prism]\")"
    if offline_mode():
        return False, "PRISMGUARD_OFFLINE=1 forces HashEmbedder"
    if profile == "security_bench":
        return (
            False,
            "heavy/security_bench forces HashEmbedder / skip_taxonomy — use law_pilot for learn-from-seed",
        )
    if profile == "low_latency":
        return (
            False,
            "light/low_latency forces HashEmbedder for speed — use law_pilot for learn-from-seed taxonomy",
        )
    if profile in ("web_chat", "rules_only"):
        return False, f"{profile} is rules-first (skip_taxonomy)"
    if profile == "sidecar":
        return False, "sidecar defaults to HashEmbedder; use law_pilot for taxonomy"
    if profile != "law_pilot":
        # Unknown / custom — only law_pilot currently enables transformer taxonomy in factory.
        return False, f"profile {profile!r} does not enable taxonomy in create_checker_for_app"
    return True, ""


def _onnx_artifact_ready() -> tuple[bool, str]:
    """Lightweight check: model.onnx present for configured artifact (no session load)."""
    try:
        from prismguard.config.loader import load_triage_config
        from prismguard.models.loader import resolve_artifact_dir

        domain = _domain_overlay()
        # law_pilot / security_bench imply law when domain unset
        profile = _default_profile()
        if domain is None and profile in ("law_pilot", "security_bench", "low_latency"):
            domain = "law"
        cfg = load_triage_config(domain=domain)
        artifact_id = os.environ.get("PRISMGUARD_ARTIFACT_ID", "").strip()
        artifact_path = os.environ.get("PRISMGUARD_GUARD_MODEL_PATH", "").strip()
        gm = cfg.guard_model
        updates: dict[str, str] = {}
        if artifact_id:
            updates["artifact_id"] = artifact_id
        if artifact_path:
            updates["artifact_path"] = artifact_path
        if updates:
            gm = gm.model_copy(update=updates)
        root = resolve_artifact_dir(gm)
        onnx = Path(root) / "model.onnx"
        if onnx.is_file():
            return True, str(root)
        return False, f"model.onnx missing under {root} (run: prismguard-model download)"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def _tenant_lexicon_status() -> tuple[bool, str]:
    path = os.environ.get("PRISMGUARD_TENANT_LEXICON_PATH", "").strip()
    if not path:
        return False, "unset"
    if Path(path).is_file():
        return True, path
    return False, f"path not found: {path}"


def guard_capabilities(
    *,
    profile: str | AppProfile | None = None,
    probe_onnx: bool = True,
) -> dict[str, Any]:
    """
    Return a truth table of Guard capabilities for the current env + profile.

    Use this (or ``prismguard caps``) before claiming scorecard / learn-from-seed parity.
    """
    from prismguard.taxonomy.mapping import has_prismrag

    requested = (profile or _default_profile()).strip().lower()
    prof = normalize_app_profile(requested)
    tax_ok, tax_reason = _taxonomy_status(prof)
    onnx_ready, onnx_detail = (False, "skipped")
    if probe_onnx:
        onnx_ready, onnx_detail = _onnx_artifact_ready()

    storage = os.environ.get("PRISMGUARD_STORAGE_BACKEND", "memory").strip() or "memory"
    persistent = storage.lower() not in ("memory", "")
    feedback = env_flag("PRISMGUARD_FEEDBACK_PERSIST", default=False)
    domain = _domain_overlay()
    if domain is None and prof in ("law_pilot", "security_bench", "low_latency"):
        domain = "law"
    lex_ok, lex_detail = _tenant_lexicon_status()

    env_mode = os.environ.get("PRISMGUARD_CLASSIFIER_MODE", "").strip().lower()
    classifier_mode = env_mode or _PROFILE_CLASSIFIER_MODE.get(prof) or "yaml_default(first)"

    notes: list[str] = []
    if not tax_ok:
        notes.append(
            "Without taxonomy, seed overlay text may be stored but word-graph / prismrag "
            f"taxonomy is skipped ({tax_reason})."
        )
    if not onnx_ready and (
        onnx_opt_in() or prof in ("security_bench", "law_pilot", "low_latency")
    ):
        notes.append("ONNX weights not ready — scorecard-class injection needs prismguard-model download.")
    if persistent:
        notes.append("Persistent storage backends require Team+ license (PRISMGUARD_LICENSE_FILE).")
    if not feedback:
        notes.append("Feedback queue off — set PRISMGUARD_FEEDBACK_PERSIST=1 for export→train loop.")
    if prof == "security_bench":
        notes.append(
            "HEAVY ONNX (security_bench): classifier_mode=first — max coverage / scorecard; "
            "~350–500ms floor. Switch to light for production latency."
        )
    if prof == "low_latency":
        notes.append(
            "LIGHT ONNX (low_latency): classifier_mode=hybrid — rules/structural first; "
            "ONNX only when needed. Switch to heavy for scorecard-class always-on coverage."
        )
    if classifier_mode == "first" and prof not in ("security_bench",):
        notes.append(
            "classifier_mode=first runs ONNX on nearly every request (~350–500ms floor). "
            "Use create_checker_for_app('light') for hybrid, or 'heavy' intentionally."
        )

    learn_ready = tax_ok and bool(domain) and (onnx_ready or onnx_opt_in())
    scorecard_ready = onnx_ready and bool(domain)

    onnx_tier = (
        "heavy"
        if prof == "security_bench"
        else "light"
        if prof == "low_latency"
        else "off"
        if prof in ("web_chat", "rules_only")
        else "configurable"
    )

    return {
        "profile": prof,
        "profile_requested": requested,
        "onnx_tier": onnx_tier,
        "onnx_opt_in": onnx_opt_in() or prof in ("security_bench", "low_latency"),
        "onnx_ready": onnx_ready,
        "onnx_detail": onnx_detail,
        "classifier_mode": classifier_mode,
        "prismrag_available": has_prismrag(),
        "prismrag_taxonomy": tax_ok,
        "taxonomy_skip_reason": "" if tax_ok else tax_reason,
        "feedback_persist": feedback,
        "storage_backend": storage,
        "storage_persistent": persistent,
        "storage_tier": "Team+" if persistent else "OSS (memory)",
        "domain_overlay": domain or "",
        "tenant_lexicon": lex_ok,
        "tenant_lexicon_detail": lex_detail,
        "scorecard_path_ready": scorecard_ready,
        "learn_from_seed_ready": learn_ready and feedback,
        "hash_only_profile": prof in _HASH_ONLY_PROFILES,
        "notes": notes,
    }


def format_capabilities(caps: dict[str, Any]) -> str:
    """Human-readable one-screen capability report."""
    lines = [
        "PrismGuard capabilities",
        f"  profile:              {caps['profile']}"
        + (
            f"  (requested: {caps['profile_requested']})"
            if caps.get("profile_requested") and caps.get("profile_requested") != caps["profile"]
            else ""
        ),
        f"  onnx_tier:            {caps.get('onnx_tier')}  (heavy=always-on, light=hybrid)",
        f"  classifier_mode:      {caps.get('classifier_mode')}",
        f"  onnx_ready:           {caps['onnx_ready']}  ({caps['onnx_detail']})",
        f"  onnx_opt_in:          {caps['onnx_opt_in']}",
        f"  prismrag_available:   {caps['prismrag_available']}",
        f"  prismrag_taxonomy:    {caps['prismrag_taxonomy']}"
        + (f"  ({caps['taxonomy_skip_reason']})" if caps.get("taxonomy_skip_reason") else ""),
        f"  feedback_persist:     {caps['feedback_persist']}",
        f"  storage_backend:      {caps['storage_backend']}  [{caps['storage_tier']}]",
        f"  domain_overlay:       {caps['domain_overlay'] or '(none)'}",
        f"  tenant_lexicon:       {caps['tenant_lexicon']}  ({caps['tenant_lexicon_detail']})",
        f"  scorecard_path_ready: {caps['scorecard_path_ready']}",
        f"  learn_from_seed_ready:{caps['learn_from_seed_ready']}",
    ]
    for note in caps.get("notes") or []:
        lines.append(f"  note: {note}")
    return "\n".join(lines)
