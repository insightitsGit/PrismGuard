"""Human-readable `prismguard check` output for CLI and README examples."""

from __future__ import annotations

import os
from typing import Any

from prismguard.runtime.check import CheckResult, RuntimeChecker


def _checker() -> RuntimeChecker:
    from prismguard.config.loader import load_triage_config
    from prismguard.runtime.guard_model import create_guard_model
    from prismguard.runtime.llm_judge import create_llm_judge
    from prismguard.seed import import_bundled_seed, load_bundled_seed
    from prismguard.storage import create_storage
    from prismguard.taxonomy.embedder import create_embedder_from_config

    domain = os.environ.get("PRISMGUARD_DOMAIN", "law")
    storage = create_storage("memory")
    parsed = load_bundled_seed(profile=os.environ.get("PRISMGUARD_SEED_PROFILE", "authored"))
    import_bundled_seed(storage, profile=os.environ.get("PRISMGUARD_SEED_PROFILE", "authored"))
    cfg = load_triage_config(domain=domain)
    embedder = create_embedder_from_config(cfg)
    guard_model = create_guard_model(cfg.guard_model) if cfg.guard_model.enabled else None
    llm_judge = None
    if cfg.gray_zone_policy == "escalate" and guard_model is not None:
        llm_judge = create_llm_judge(
            prefer_openai=False,
            rate_cap_per_minute=cfg.judge.rate_cap_per_minute,
            embedder=embedder,
            cache_similarity_threshold=cfg.cache.semantic_cache_threshold,
        )
    return RuntimeChecker.from_storage(
        storage,
        parsed,
        embedder=embedder,
        config=cfg,
        guard_model=guard_model,
        llm_judge=llm_judge,
    )


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
    return "\n".join(lines)


def run_check(text: str) -> CheckResult:
    checker = _checker()
    try:
        return checker.check(text)
    finally:
        checker._storage.close()  # noqa: SLF001
