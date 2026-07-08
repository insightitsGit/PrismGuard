from __future__ import annotations

import time
from typing import Literal, Protocol

from benchmark.law.shared.types import GuardOutcome

SeedProfile = Literal["authored", "full"]
GrayPolicy = Literal["escalate", "fail_open", "fail_closed"]


class GuardGate(Protocol):
    name: str

    def check(self, text: str) -> GuardOutcome: ...


def _outcome_from_check_result(result, *, elapsed: float, name: str) -> GuardOutcome:
    classifier_calls = 0
    if result.resolution_gate in ("guard_model", "guard_model_first", "guard_model_veto"):
        classifier_calls = 1
    elif result.details.get("classifier_fused"):
        classifier_calls = 1
    generative_calls = 1 if result.resolution_gate == "llm_judge" else 0
    if result.resolution_gate == "guard_model":
        tier = "classifier_escalation"
    elif result.resolution_gate == "guard_model_first":
        tier = "classifier_first"
    elif result.resolution_gate == "guard_model_veto":
        tier = "classifier_parallel_fusion"
    elif result.resolution_gate == "llm_judge":
        tier = "generative_judge"
    elif result.details.get("classifier_fused"):
        tier = "classifier_parallel_fusion"
    elif result.resolution_gate in ("fusion_gray_fail_closed", "fusion_gray_fail_open"):
        tier = "policy_resolved"
    elif result.resolution_gate in ("tier1_rule", "tenant_context_rule", "corpus_match", "fusion_block", "fusion_allow", "benign_fast_path"):
        tier = "fusion_fast_path"
    else:
        tier = "fusion_only"
    return GuardOutcome(
        decision=result.decision,
        resolution_gate=result.resolution_gate,
        guardrail=name,
        guard_classifier_calls=classifier_calls,
        guard_generative_llm_calls=generative_calls,
        guard_model_tier=tier,
        latency_ms=elapsed,
        mapped_category=result.matched_category,
        details=result.details,
    )


class PrismGuardGate:
    name = "prismguard"

    def __init__(
        self,
        *,
        seed_profile: SeedProfile = "authored",
        gray_zone_policy: GrayPolicy = "escalate",
        enable_guard_model: bool = True,
        enable_llm_judge: bool = True,
        import_legal_overlay: bool = True,
    ) -> None:
        from prismguard.config.loader import load_triage_config
        from prismguard.feedback.review import FeedbackReviewService
        from prismguard.runtime.check import RuntimeChecker
        from prismguard.runtime.guard_model import create_guard_model
        from prismguard.runtime.llm_judge import create_llm_judge
        from prismguard.seed import import_bundled_seed, import_seeds, load_bundled_seed
        from prismguard.seed.parse import parse_seed_file
        from prismguard.storage import create_storage
        from prismguard.taxonomy.embedder import create_embedder_from_config

        domain = __import__("os").environ.get("PRISMGUARD_DOMAIN", "law")
        config = load_triage_config(domain=domain).model_copy(update={"gray_zone_policy": gray_zone_policy})
        embedder = create_embedder_from_config(config)
        guard_model = None
        llm_judge = None
        if gray_zone_policy == "escalate":
            if enable_guard_model:
                guard_model = create_guard_model()
            if guard_model is None:
                config = config.model_copy(update={"gray_zone_policy": "fail_closed"})
            elif enable_llm_judge:
                llm_judge = create_llm_judge(
                    prefer_openai=False,
                    rate_cap_per_minute=config.judge.rate_cap_per_minute,
                    embedder=embedder,
                    cache_similarity_threshold=config.cache.semantic_cache_threshold,
                )

        self._storage = create_storage("memory")
        self._feedback = FeedbackReviewService(self._storage)
        parsed = load_bundled_seed(profile=seed_profile)
        import_bundled_seed(self._storage, profile=seed_profile)
        if import_legal_overlay:
            overlay = __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "legal_attacks.yaml"
            import_seeds(self._storage, parse_seed_file(overlay), mode="update")
        self._checker = RuntimeChecker.from_storage(
            self._storage,
            parsed,
            embedder=embedder,
            config=config,
            guard_model=guard_model,
            llm_judge=llm_judge,
            feedback_review=self._feedback,
        )

    def check(self, text: str) -> GuardOutcome:
        start = time.perf_counter()
        result = self._checker.check(text)
        elapsed = (time.perf_counter() - start) * 1000
        return _outcome_from_check_result(result, elapsed=elapsed, name=self.name)


class PrismGuardCorpusScaleGate(PrismGuardGate):
    """Phase-1-only corpus scale experiment: full seed, terminal gray, no guard model."""

    def __init__(self) -> None:
        from prismguard.config.loader import load_triage_config

        config = load_triage_config().model_copy(update={"gray_terminal": True})
        super().__init__(
            seed_profile="full",
            gray_zone_policy="fail_closed",
            enable_guard_model=False,
            enable_llm_judge=False,
            import_legal_overlay=True,
        )
        self._checker._config = config  # noqa: SLF001


class PrismGuardPhase1Gate(PrismGuardGate):
    """Bug2-equivalent Phase 1 gate: authored seed, terminal gray, no guard model."""

    def __init__(self) -> None:
        from prismguard.config.loader import load_triage_config

        super().__init__(
            seed_profile="authored",
            gray_zone_policy="fail_closed",
            enable_guard_model=False,
            enable_llm_judge=False,
            import_legal_overlay=True,
        )
        self._checker._config = load_triage_config().model_copy(update={"gray_terminal": True})  # noqa: SLF001


class LLMGuardGate:
    name = "llm_guard"

    def __init__(self) -> None:
        self._scanner = None
        self._init_error = "llm-guard not installed"
        try:
            from llm_guard.input_scanners import PromptInjection

            self._scanner = PromptInjection()
            self._init_error = ""
        except Exception as exc:  # pragma: no cover - optional heavy dep
            self._init_error = str(exc)

    def check(self, text: str) -> GuardOutcome:
        start = time.perf_counter()
        if self._scanner is None:
            return GuardOutcome(
                decision="gray",
                resolution_gate="llm_guard_unconfigured",
                guardrail=self.name,
                guard_classifier_calls=0,
                guard_generative_llm_calls=0,
                guard_model_tier="unconfigured",
                latency_ms=(time.perf_counter() - start) * 1000,
                details={"error": self._init_error},
            )
        sanitized, is_valid, risk_score = self._scanner.scan(text)
        elapsed = (time.perf_counter() - start) * 1000
        return GuardOutcome(
            decision="allow" if is_valid else "block",
            resolution_gate="llm_guard_prompt_injection",
            guardrail=self.name,
            guard_classifier_calls=1,
            guard_generative_llm_calls=0,
            guard_model_tier="classifier",
            latency_ms=elapsed,
            mapped_category="direct_instruction_override" if not is_valid else "benign_adjacent",
            details={"is_valid": is_valid, "risk_score": risk_score, "sanitized_len": len(sanitized or "")},
        )
