"""Application-oriented RuntimeChecker factories (dogfood-safe defaults)."""

from __future__ import annotations

import os
import threading
from typing import Any, Literal

AppProfile = Literal["web_chat", "law_pilot", "sidecar", "rules_only"]

_SINGLETONS: dict[str, Any] = {}
_SINGLETON_LOCK = threading.Lock()


def env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def offline_mode() -> bool:
    return env_flag("PRISMGUARD_OFFLINE", default=False)


def onnx_opt_in() -> bool:
    """ONNX loads only when explicitly enabled (never surprise-enable for hubs)."""
    return env_flag("PRISMGUARD_USE_ONNX", default=False)


def create_checker_rules_only(*, seed_profile: str | None = None) -> Any:
    """Fast offline checker: memory storage, authored seed, HashEmbedder, no ONNX, no HF."""
    from prismguard.config.loader import TriageConfig, load_triage_config
    from prismguard.runtime.check import RuntimeChecker
    from prismguard.seed import import_bundled_seed, load_bundled_seed
    from prismguard.storage import create_storage
    from prismguard.taxonomy.embedder import HashEmbedder

    profile = seed_profile or os.environ.get("PRISMGUARD_SEED_PROFILE", "authored")
    storage = create_storage("memory")
    parsed = load_bundled_seed(profile=profile)  # type: ignore[arg-type]
    import_bundled_seed(storage, profile=profile, skip_taxonomy=True)  # type: ignore[arg-type]

    try:
        cfg = load_triage_config(domain=None)
    except Exception:
        cfg = TriageConfig()
    cfg = cfg.model_copy(
        update={
            "gray_zone_policy": "fail_open",
            "embedding": cfg.embedding.model_copy(
                update={"corpus_path_enabled": False, "prefer_transformer": False}
            ),
            "guard_model": cfg.guard_model.model_copy(update={"enabled": False}),
        }
    )
    return RuntimeChecker.from_storage(
        storage,
        parsed,
        embedder=HashEmbedder(),
        config=cfg,
        guard_model=None,
        llm_judge=None,
    )


def create_checker_for_app(
    profile: AppProfile = "web_chat",
    *,
    use_onnx: bool | None = None,
    domain: str | None = None,
    seed_profile: str | None = None,
    shadow_onnx: bool | None = None,
) -> Any:
    """
    First-class factory for product integrations.

    Profiles
    --------
    web_chat / rules_only
        ONNX off by default, HashEmbedder, no corpus ANN, fail_open gray policy.
    law_pilot
        Law domain pack + ONNX when ``PRISMGUARD_USE_ONNX=1`` or ``use_onnx=True``.
    sidecar
        Same as env-driven HTTP defaults; ONNX still requires explicit opt-in.
    """
    if profile in ("web_chat", "rules_only"):
        checker = create_checker_rules_only(seed_profile=seed_profile)
        if shadow_onnx or (shadow_onnx is None and env_flag("PRISMGUARD_SHADOW_ONNX")):
            return _wrap_shadow_onnx(checker, domain=domain or "law")
        if use_onnx is True or (use_onnx is None and onnx_opt_in()):
            # Explicit opt-in on web_chat still allowed for experiments.
            return _rebuild_with_onnx(checker, domain=domain, seed_profile=seed_profile, shadow=False)
        return checker

    return _build_full_checker(
        domain=domain if domain is not None else ("law" if profile == "law_pilot" else _default_domain()),
        seed_profile=seed_profile,
        use_onnx=use_onnx,
        shadow_onnx=bool(shadow_onnx) if shadow_onnx is not None else env_flag("PRISMGUARD_SHADOW_ONNX"),
        force_hash_embedder=offline_mode() or profile != "law_pilot",
    )


def create_checker_from_env() -> Any:
    """
    Build RuntimeChecker from environment.

    Breaking change (Dogfood1): ONNX loads only when ``PRISMGUARD_USE_ONNX=1``.
    Domain defaults to empty/core (no law overlay) unless ``PRISMGUARD_DOMAIN`` is set.

    Default (no ``PRISMGUARD_APP_PROFILE``): dogfood ``web_chat`` / rules-first path so
    ``prismguard check`` works on a bare ``pip install prismguard`` without ``[prism]``.
    Set ``PRISMGUARD_APP_PROFILE=sidecar`` or ``law_pilot`` for the full stack.
    """
    profile = os.environ.get("PRISMGUARD_APP_PROFILE", "").strip().lower()
    if not profile:
        # Base install / CLI headline path — rules-first, no surprise prismrag hard-fail.
        profile = "web_chat"
    if profile in ("web_chat", "rules_only", "law_pilot", "sidecar"):
        return get_or_create_checker(profile)  # type: ignore[arg-type]
    return _build_full_checker(
        domain=_default_domain(),
        seed_profile=os.environ.get("PRISMGUARD_SEED_PROFILE", "authored"),
        use_onnx=None,
        shadow_onnx=env_flag("PRISMGUARD_SHADOW_ONNX"),
        force_hash_embedder=offline_mode(),
    )


def get_or_create_checker(profile: AppProfile = "web_chat") -> Any:
    """Thread-safe process singleton for app workers."""
    key = f"{profile}:{os.environ.get('PRISMGUARD_DOMAIN', '')}:{onnx_opt_in()}:{offline_mode()}"
    with _SINGLETON_LOCK:
        existing = _SINGLETONS.get(key)
        if existing is not None:
            return existing
        checker = create_checker_for_app(profile)
        _SINGLETONS[key] = checker
        return checker


def clear_checker_singletons() -> None:
    with _SINGLETON_LOCK:
        _SINGLETONS.clear()


def _default_domain() -> str | None:
    raw = os.environ.get("PRISMGUARD_DOMAIN", "").strip()
    if not raw or raw.lower() in ("none", "general", "core", "-"):
        return None
    return raw


def _build_full_checker(
    *,
    domain: str | None,
    seed_profile: str | None,
    use_onnx: bool | None,
    shadow_onnx: bool,
    force_hash_embedder: bool,
) -> Any:
    from prismguard.config.loader import load_triage_config
    from prismguard.runtime.check import RuntimeChecker
    from prismguard.runtime.guard_model import create_guard_model
    from prismguard.runtime.llm_judge import create_llm_judge
    from prismguard.seed import import_bundled_seed, load_bundled_seed
    from prismguard.storage import create_storage_from_env
    from prismguard.taxonomy.embedder import HashEmbedder, create_embedder_from_config

    from prismguard.taxonomy.mapping import has_prismrag

    profile = seed_profile or os.environ.get("PRISMGUARD_SEED_PROFILE", "authored")
    storage = create_storage_from_env()
    parsed = load_bundled_seed(profile=profile)  # type: ignore[arg-type]
    # Skip heavy post-seed pipeline when offline/hash-only, or when [prism] is absent
    # (rules-only TaxonomyEngine is still built later in RuntimeChecker.from_storage).
    skip_tax = force_hash_embedder or offline_mode() or not has_prismrag()
    import_bundled_seed(storage, profile=profile, skip_taxonomy=skip_tax)  # type: ignore[arg-type]
    if domain:
        from prismguard.domains.registry import get_domain_pack
        from prismguard.seed import import_seeds
        from prismguard.seed.parse import parse_seed_file

        overlay_path = get_domain_pack(domain).overlay_path
        import_seeds(
            storage,
            parse_seed_file(overlay_path),
            mode="update",
            skip_taxonomy=skip_tax,
        )

    cfg = load_triage_config(domain=domain)
    if force_hash_embedder or offline_mode() or not cfg.embedding.corpus_path_enabled:
        cfg = cfg.model_copy(
            update={
                "embedding": cfg.embedding.model_copy(
                    update={"corpus_path_enabled": False, "prefer_transformer": False}
                )
            }
        )
        embedder = HashEmbedder()
    else:
        embedder = create_embedder_from_config(cfg)

    want_onnx = onnx_opt_in() if use_onnx is None else use_onnx
    guard_model = None
    if want_onnx and cfg.guard_model.enabled:
        # Opt-in artifact selection (default remains triage.yaml / prism-pi-v1).
        # Set PRISMGUARD_ARTIFACT_ID=prism-pi-hub-v1 (or customer id) after gates pass.
        artifact_id = os.environ.get("PRISMGUARD_ARTIFACT_ID", "").strip()
        artifact_path = os.environ.get("PRISMGUARD_GUARD_MODEL_PATH", "").strip()
        gm_cfg = cfg.guard_model
        updates: dict[str, str] = {}
        if artifact_id:
            updates["artifact_id"] = artifact_id
        if artifact_path:
            updates["artifact_path"] = artifact_path
        if updates:
            gm_cfg = gm_cfg.model_copy(update=updates)
            cfg = cfg.model_copy(update={"guard_model": gm_cfg})
        guard_model = create_guard_model(gm_cfg)
    elif not want_onnx:
        # Prevent RuntimeChecker.from_storage from surprise-loading ONNX.
        cfg = cfg.model_copy(
            update={
                "guard_model": cfg.guard_model.model_copy(update={"enabled": False}),
            }
        )

    # Without ONNX, escalate policy cannot be satisfied — fail open for dogfood safety.
    if guard_model is None and cfg.gray_zone_policy == "escalate":
        cfg = cfg.model_copy(update={"gray_zone_policy": "fail_open"})

    llm_judge = None
    if cfg.gray_zone_policy == "escalate" and guard_model is not None and not offline_mode():
        llm_judge = create_llm_judge(
            prefer_openai=False,
            rate_cap_per_minute=cfg.judge.rate_cap_per_minute,
            embedder=embedder,
            cache_similarity_threshold=cfg.cache.semantic_cache_threshold,
        )

    enforce_model = None if shadow_onnx else guard_model
    enforce_judge = None if shadow_onnx else llm_judge
    if shadow_onnx and cfg.gray_zone_policy == "escalate":
        cfg = cfg.model_copy(update={"gray_zone_policy": "fail_open"})

    feedback_review = None
    # Opt-in: PRISMGUARD_FEEDBACK_PERSIST=1 wires review queue (default off).
    if env_flag("PRISMGUARD_FEEDBACK_PERSIST", default=False):
        from prismguard.feedback.review import FeedbackReviewService

        feedback_review = FeedbackReviewService(storage)

    checker = RuntimeChecker.from_storage(
        storage,
        parsed,
        embedder=embedder,
        config=cfg,
        guard_model=enforce_model,
        llm_judge=enforce_judge,
        feedback_review=feedback_review,
    )
    if shadow_onnx and want_onnx:
        return _ShadowOnnxChecker(checker, domain=domain or "law")
    return checker


def _rebuild_with_onnx(base: Any, *, domain: str | None, seed_profile: str | None, shadow: bool) -> Any:
    _ = base
    return _build_full_checker(
        domain=domain,
        seed_profile=seed_profile,
        use_onnx=True,
        shadow_onnx=shadow,
        force_hash_embedder=True,
    )


def _wrap_shadow_onnx(rules_checker: Any, *, domain: str) -> Any:
    return _ShadowOnnxChecker(rules_checker, domain=domain)


class _ShadowOnnxChecker:
    """Enforce rules checker; attach shadow ONNX verdict without enforcing it."""

    def __init__(self, enforce_checker: Any, *, domain: str) -> None:
        self._enforce = enforce_checker
        self._shadow = None
        self._domain = domain
        self._shadow_error = ""

    def _ensure_shadow(self) -> None:
        if self._shadow is not None or self._shadow_error:
            return
        try:
            from prismguard.runtime.guard_model import create_guard_model
            from prismguard.config.loader import load_triage_config

            cfg = load_triage_config(domain=self._domain)
            self._shadow = create_guard_model(cfg.guard_model)
            if self._shadow is None:
                self._shadow_error = "shadow ONNX not ready"
        except Exception as exc:  # pragma: no cover
            self._shadow_error = str(exc)

    def check(self, text: str, *, session_id: str | None = None) -> Any:
        result = self._enforce.check(text, session_id=session_id)
        self._ensure_shadow()
        details = dict(getattr(result, "details", {}) or {})
        if self._shadow is not None:
            try:
                verdict = self._shadow.check(text)
                details["shadow_onnx"] = {
                    "decision": verdict.decision,
                    "confidence": float(verdict.confidence),
                    "model_id": verdict.model_id,
                    "enforced": False,
                }
                if verdict.decision == "block" and hasattr(self._enforce, "_local_metrics"):
                    self._enforce._local_metrics["shadow_would_block"] += 1  # noqa: SLF001
            except Exception as exc:  # pragma: no cover
                details["shadow_onnx"] = {"error": str(exc), "enforced": False}
        elif self._shadow_error:
            details["shadow_onnx"] = {"error": self._shadow_error, "enforced": False}
        result.details = details
        return result

    def metrics_snapshot(self) -> dict[str, object]:
        if hasattr(self._enforce, "metrics_snapshot"):
            return self._enforce.metrics_snapshot()
        return {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._enforce, name)
