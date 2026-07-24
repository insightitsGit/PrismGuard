"""Application-oriented RuntimeChecker factories (dogfood-safe defaults)."""

from __future__ import annotations

import os
import threading
from typing import Any, Literal

AppProfile = Literal[
    "web_chat",
    "domain_pilot",
    "law_pilot",  # deprecated alias → domain_pilot + domain=law
    "sidecar",
    "rules_only",
    "security_bench",
    "low_latency",
    "heavy",  # alias → security_bench (always-on ONNX)
    "light",  # alias → low_latency (hybrid / selective ONNX)
]

ClassifierMode = Literal["first", "parallel", "gray_only", "hybrid"]
_VALID_CLASSIFIER_MODES = frozenset({"first", "parallel", "gray_only", "hybrid"})

# Canonical names for the two ONNX intensity options (both worlds).
_PROFILE_ALIASES: dict[str, AppProfile] = {
    "heavy": "security_bench",
    "light": "low_latency",
    # Friendly synonyms
    "onnx_heavy": "security_bench",
    "onnx_light": "low_latency",
    "onnx_first": "security_bench",
    "onnx_hybrid": "low_latency",
    # Deprecated: law_pilot → domain_pilot (domain defaults to law)
    "law_pilot": "domain_pilot",
}

_TAXONOMY_PROFILES = frozenset({"domain_pilot"})

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


def create_checker_rules_only(
    *,
    seed_profile: str | None = None,
    domain: str | None = None,
) -> Any:
    """Fast offline checker: memory storage, authored seed, HashEmbedder, no ONNX, no HF.

    Optional ``domain`` (or ``PRISMGUARD_DOMAIN``) loads that pack's overlay — any slug.
    """
    from prismguard.config.loader import TriageConfig, load_triage_config
    from prismguard.runtime.check import RuntimeChecker
    from prismguard.seed import import_bundled_seed, load_bundled_seed
    from prismguard.storage import create_storage
    from prismguard.taxonomy.embedder import HashEmbedder

    profile = seed_profile or os.environ.get("PRISMGUARD_SEED_PROFILE", "authored")
    resolved = domain if domain is not None else _default_domain()
    storage = create_storage("memory")
    parsed = load_bundled_seed(profile=profile)  # type: ignore[arg-type]
    import_bundled_seed(storage, profile=profile, skip_taxonomy=True)  # type: ignore[arg-type]
    if resolved:
        from prismguard.domains.registry import get_domain_pack
        from prismguard.seed import import_seeds
        from prismguard.seed.parse import parse_seed_file

        overlay_path = get_domain_pack(resolved).overlay_path
        import_seeds(
            storage,
            parse_seed_file(overlay_path),
            mode="update",
            skip_taxonomy=True,
        )

    try:
        cfg = load_triage_config(domain=resolved)
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
    checker = RuntimeChecker.from_storage(
        storage,
        parsed,
        embedder=HashEmbedder(),
        config=cfg,
        guard_model=None,
        llm_judge=None,
    )
    checker._domain = resolved  # noqa: SLF001
    return checker


def resolve_classifier_mode(
    explicit: ClassifierMode | str | None = None,
    *,
    profile_default: ClassifierMode | None = None,
) -> ClassifierMode | None:
    """
    Resolve classifier_mode override.

    Precedence: explicit arg → ``PRISMGUARD_CLASSIFIER_MODE`` → profile_default → None (YAML).
    """
    for candidate in (explicit, os.environ.get("PRISMGUARD_CLASSIFIER_MODE", "").strip(), profile_default):
        if not candidate:
            continue
        mode = str(candidate).strip().lower()
        if mode in _VALID_CLASSIFIER_MODES:
            return mode  # type: ignore[return-value]
        raise ValueError(
            f"Invalid classifier_mode {candidate!r}. "
            f"Expected one of: {', '.join(sorted(_VALID_CLASSIFIER_MODES))}"
        )
    return None


def normalize_app_profile(profile: str) -> AppProfile:
    """Map aliases (``heavy`` / ``light`` / ``law_pilot``) to canonical profile names."""
    key = (profile or "").strip().lower()
    return _PROFILE_ALIASES.get(key, key)  # type: ignore[return-value]


def resolve_domain_pilot_domain(
    domain: str | None,
    *,
    requested_profile: str,
) -> str:
    """
    Domain for ``domain_pilot``.

    Order: ``law_pilot`` alias always → ``law``; else kwarg ``domain=`` →
    ``PRISMGUARD_DOMAIN`` → raise (no silent law default for bare domain_pilot).
    """
    if requested_profile.strip().lower() == "law_pilot":
        return "law"
    if domain is not None and str(domain).strip():
        key = str(domain).strip().lower()
        if key in ("none", "core", "-"):
            raise ValueError(
                "domain_pilot requires a concrete domain pack "
                f"(got {domain!r}). Pass domain='finance'|'law'|… "
                "or set PRISMGUARD_DOMAIN."
            )
        return key
    env = os.environ.get("PRISMGUARD_DOMAIN", "").strip()
    if env and env.lower() not in ("none", "core", "-"):
        # Accept "general" here — it is a real domain pack for domain_pilot.
        return env.lower()
    raise ValueError(
        "domain_pilot requires domain=... or PRISMGUARD_DOMAIN. "
        "Example: create_checker_for_app('domain_pilot', domain='finance', use_onnx=True). "
        "Legacy create_checker_for_app('law_pilot') defaults domain=law."
    )


def create_checker_for_app(
    profile: AppProfile = "web_chat",
    *,
    use_onnx: bool | None = None,
    domain: str | None = None,
    seed_profile: str | None = None,
    shadow_onnx: bool | None = None,
    classifier_mode: ClassifierMode | str | None = None,
) -> Any:
    """
    First-class factory for product integrations.

    Profiles
    --------
    web_chat / rules_only
        ONNX off by default, HashEmbedder, no corpus ANN, fail_open gray policy.
        Hub / FAQ path — do **not** compare to the published law scorecard.
    domain_pilot
        **Canonical learn-from-seed / taxonomy path for any domain after train.**
        Requires ``domain=`` or ``PRISMGUARD_DOMAIN``. Builds prismrag taxonomy when
        ``[prism]`` is installed and not offline. Pair with
        ``PRISMGUARD_ARTIFACT_ID=prism-pi-<domain>-v1`` + ``use_onnx=True``.
        Do **not** invent ``finance_pilot`` / ``healthcare_pilot``.
    law_pilot
        **Deprecated alias** for ``domain_pilot`` + ``domain=\"law\"`` (compat).
    heavy / security_bench
        **Heavy ONNX** — always-on classifier (``classifier_mode: first``).
        Max injection coverage / scorecard parity; ~350–500 ms floor.
        Raises if ``model.onnx`` missing. Skip taxonomy.
    light / low_latency
        **Light ONNX** — selective classifier (``classifier_mode: hybrid``).
        Rules/structural short-circuit first; ONNX only when needed.
        Best production/stack latency; raises if weights missing. Skip taxonomy.
    sidecar
        Same as env-driven HTTP defaults; ONNX still requires explicit opt-in.
        HashEmbedder by default (not taxonomy).

    See also: ``prismguard.runtime.capabilities.guard_capabilities`` / ``prismguard caps``.
    """
    requested = (profile or "").strip().lower()
    # Reject per-domain pilot inventions early (clearer than AppProfile type errors).
    if requested.endswith("_pilot") and requested not in ("domain_pilot", "law_pilot"):
        raise ValueError(
            f"Unknown profile {profile!r}. Use create_checker_for_app('domain_pilot', "
            "domain='<domain>', use_onnx=True) after train — do not invent "
            "finance_pilot / healthcare_pilot / per-vertical pilots."
        )
    canonical = normalize_app_profile(profile)

    if canonical in ("web_chat", "rules_only"):
        # Honor domain= / PRISMGUARD_DOMAIN for overlay + structural packs (any slug).
        resolved_hub = domain if domain is not None else _default_domain()
        checker = create_checker_rules_only(seed_profile=seed_profile, domain=resolved_hub)
        if shadow_onnx or (shadow_onnx is None and env_flag("PRISMGUARD_SHADOW_ONNX")):
            return _wrap_shadow_onnx(checker, domain=resolved_hub or "")
        if use_onnx is True or (use_onnx is None and onnx_opt_in()):
            # Explicit opt-in on web_chat still allowed for experiments.
            return _rebuild_with_onnx(
                checker,
                domain=domain,
                seed_profile=seed_profile,
                shadow=False,
                classifier_mode=classifier_mode,
            )
        return checker

    if canonical == "security_bench":
        return _create_security_bench_checker(
            domain=domain,
            seed_profile=seed_profile,
            classifier_mode=classifier_mode,
        )

    if canonical == "low_latency":
        return _create_low_latency_checker(
            domain=domain,
            seed_profile=seed_profile,
            classifier_mode=classifier_mode,
        )

    if canonical == "domain_pilot":
        resolved = resolve_domain_pilot_domain(domain, requested_profile=requested)
        # Ensure pack exists early (clearer error than mid-import).
        from prismguard.domains.registry import get_domain_pack

        get_domain_pack(resolved)
        return _build_full_checker(
            domain=resolved,
            seed_profile=seed_profile,
            use_onnx=use_onnx,
            shadow_onnx=bool(shadow_onnx) if shadow_onnx is not None else env_flag("PRISMGUARD_SHADOW_ONNX"),
            force_hash_embedder=offline_mode(),
            classifier_mode=resolve_classifier_mode(classifier_mode),
        )

    # sidecar / unknown full-stack profiles
    return _build_full_checker(
        domain=domain if domain is not None else _default_domain(),
        seed_profile=seed_profile,
        use_onnx=use_onnx,
        shadow_onnx=bool(shadow_onnx) if shadow_onnx is not None else env_flag("PRISMGUARD_SHADOW_ONNX"),
        force_hash_embedder=offline_mode() or canonical != "domain_pilot",
        classifier_mode=resolve_classifier_mode(classifier_mode),
    )


def _require_onnx_ready(checker: Any, *, profile: str) -> Any:
    gm = getattr(checker, "_guard_model", None)
    if gm is None or not getattr(gm, "is_ready", False):
        raise RuntimeError(
            f"{profile} requires ONNX weights. "
            "Install extras and download the artifact, then retry:\n"
            '  pip install "prismguard[prism,guard-model]"\n'
            "  prismguard-model download\n"
            "  export PRISMGUARD_USE_ONNX=1\n"
            "Tip: use create_checker_for_app('light') for hybrid/faster ONNX, "
            "or 'heavy' for always-on ONNX (scorecard)."
        )
    return checker


def _resolve_onnx_profile_domain(domain: str | None) -> str | None:
    """Domain for light/heavy: kwarg → env → None (core, no overlay).

    Scorecard methodology historically used law; callers may still pass
    ``domain='law'`` or set ``PRISMGUARD_DOMAIN=law``. Custom domains are OK
    when the matching ``PRISMGUARD_ARTIFACT_ID`` is set.
    """
    if domain is not None and str(domain).strip():
        key = str(domain).strip().lower()
        if key not in ("none", "core", "-"):
            return key
    return _default_domain()


def _create_security_bench_checker(
    *,
    domain: str | None = None,
    seed_profile: str | None = None,
    classifier_mode: ClassifierMode | str | None = None,
) -> Any:
    """ONNX + classifier_mode first; fail loudly if weights missing.

    Domain defaults to env / unset (core). Pass ``domain='law'`` for the classic
    law scorecard path.
    """
    os.environ["PRISMGUARD_USE_ONNX"] = "1"
    mode = resolve_classifier_mode(classifier_mode, profile_default="first")
    checker = _build_full_checker(
        domain=_resolve_onnx_profile_domain(domain),
        seed_profile=seed_profile,
        use_onnx=True,
        shadow_onnx=False,
        force_hash_embedder=True,
        classifier_mode=mode or "first",
    )
    return _require_onnx_ready(checker, profile="security_bench")


def _create_low_latency_checker(
    *,
    domain: str | None = None,
    seed_profile: str | None = None,
    classifier_mode: ClassifierMode | str | None = None,
) -> Any:
    """ONNX + hybrid (skip ONNX on tier1/structural); fail loud if weights missing.

    Domain defaults to env / unset (core). Pass ``domain=`` for a vertical overlay.
    """
    os.environ["PRISMGUARD_USE_ONNX"] = "1"
    mode = resolve_classifier_mode(classifier_mode, profile_default="hybrid")
    checker = _build_full_checker(
        domain=_resolve_onnx_profile_domain(domain),
        seed_profile=seed_profile,
        use_onnx=True,
        shadow_onnx=False,
        force_hash_embedder=True,
        classifier_mode=mode or "hybrid",
    )
    return _require_onnx_ready(checker, profile="low_latency")


def create_checker_from_env() -> Any:
    """
    Build RuntimeChecker from environment.

    Breaking change (Dogfood1): ONNX loads only when ``PRISMGUARD_USE_ONNX=1``.
    Domain defaults to empty/core (no law overlay) unless ``PRISMGUARD_DOMAIN`` is set.

    Default (no ``PRISMGUARD_APP_PROFILE``): dogfood ``web_chat`` / rules-first path so
    ``prismguard check`` works on a bare ``pip install prismguard`` without ``[prism]``.
    Set ``PRISMGUARD_APP_PROFILE=sidecar`` or ``domain_pilot`` for the full stack.
    """
    requested = os.environ.get("PRISMGUARD_APP_PROFILE", "").strip().lower()
    if not requested:
        # Base install / CLI headline path — rules-first, no surprise prismrag hard-fail.
        requested = "web_chat"
    canonical = normalize_app_profile(requested)
    if canonical in (
        "web_chat",
        "rules_only",
        "domain_pilot",
        "sidecar",
        "security_bench",
        "low_latency",
    ) or requested in ("law_pilot", "heavy", "light"):
        # Pass requested so law_pilot keeps domain=law default.
        return get_or_create_checker(requested)  # type: ignore[arg-type]
    return _build_full_checker(
        domain=_default_domain(),
        seed_profile=os.environ.get("PRISMGUARD_SEED_PROFILE", "authored"),
        use_onnx=None,
        shadow_onnx=env_flag("PRISMGUARD_SHADOW_ONNX"),
        force_hash_embedder=offline_mode(),
        classifier_mode=resolve_classifier_mode(None),
    )


def get_or_create_checker(profile: AppProfile = "web_chat") -> Any:
    """Thread-safe process singleton for app workers."""
    requested = (profile or "").strip().lower()
    profile = normalize_app_profile(profile)
    mode = os.environ.get("PRISMGUARD_CLASSIFIER_MODE", "")
    key = (
        f"{profile}:{requested}:{os.environ.get('PRISMGUARD_DOMAIN', '')}:"
        f"{onnx_opt_in()}:{offline_mode()}:{mode}"
    )
    with _SINGLETON_LOCK:
        existing = _SINGLETONS.get(key)
        if existing is not None:
            return existing
        # Preserve law_pilot request so domain defaults to law when env unset.
        checker = create_checker_for_app(requested if requested == "law_pilot" else profile)  # type: ignore[arg-type]
        _SINGLETONS[key] = checker
        return checker


def clear_checker_singletons() -> None:
    with _SINGLETON_LOCK:
        _SINGLETONS.clear()


def _default_domain() -> str | None:
    """Sidecar/env default domain. Empty/general/core → None (no overlay).

    ``domain_pilot`` uses :func:`resolve_domain_pilot_domain` instead (accepts
    ``general`` as a real pack when explicitly requested).
    """
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
    classifier_mode: ClassifierMode | None = None,
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
    mode = resolve_classifier_mode(classifier_mode)
    if mode is not None:
        cfg = cfg.model_copy(
            update={
                "guard_model": cfg.guard_model.model_copy(update={"classifier_mode": mode}),
            }
        )
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
        return _ShadowOnnxChecker(checker, domain=domain or "")
    # Stash active domain for structural pack gating (any custom slug).
    try:
        checker._domain = domain  # noqa: SLF001
    except Exception:
        pass
    return checker


def _rebuild_with_onnx(
    base: Any,
    *,
    domain: str | None,
    seed_profile: str | None,
    shadow: bool,
    classifier_mode: ClassifierMode | str | None = None,
) -> Any:
    _ = base
    return _build_full_checker(
        domain=domain,
        seed_profile=seed_profile,
        use_onnx=True,
        shadow_onnx=shadow,
        force_hash_embedder=True,
        classifier_mode=resolve_classifier_mode(classifier_mode),
    )


def _wrap_shadow_onnx(rules_checker: Any, *, domain: str) -> Any:
    return _ShadowOnnxChecker(rules_checker, domain=domain or "")


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

            cfg = load_triage_config(domain=self._domain or None)
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
