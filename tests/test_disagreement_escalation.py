"""Structural allow + classifier disagree → Judge escalation (not veto block)."""

from __future__ import annotations

from dataclasses import dataclass, field

from prismguard.config.loader import GuardModelConfig, TriageConfig
from prismguard.runtime.check import RuntimeChecker
from prismguard.runtime.guard_model import GuardModelVerdict
from prismguard.runtime.llm_judge import HeuristicLLMJudge
from prismguard.storage import create_storage
from prismguard.taxonomy.embedder import HashEmbedder

pytest = __import__("pytest")
pytest.importorskip("prismrag_patch")


@dataclass
class StubGuardModel:
    model_id: str = "stub"
    verdict: GuardModelVerdict = field(
        default_factory=lambda: GuardModelVerdict(decision="block", confidence=0.95, latency_ms=1.0)
    )
    calls: int = 0

    @property
    def call_count(self) -> int:
        return self.calls

    def check(self, text: str, *, context: dict | None = None) -> GuardModelVerdict:
        _ = context
        self.calls += 1
        return self.verdict


def _checker(*, guard: StubGuardModel, judge=None, disagreement_escalation: bool = True) -> RuntimeChecker:
    from prismguard.seed import load_bundled_seed
    from prismguard.taxonomy.mapping import build_mapping_from_parsed_seed

    storage = create_storage("memory")
    engine = build_mapping_from_parsed_seed(load_bundled_seed(profile="authored"))
    cfg = TriageConfig(
        gray_zone_policy="escalate",
        embedding={"corpus_path_enabled": False},
        guard_model=GuardModelConfig(
            classifier_mode="first",
            disagreement_escalation=disagreement_escalation,
            veto_enabled=True,
            veto_threshold=0.65,
            classifier_first_block_threshold=0.85,
        ),
    )
    return RuntimeChecker(
        storage,
        engine,
        embedder=HashEmbedder(),
        config=cfg,
        guard_model=guard,
        llm_judge=judge,
    )


def test_structural_allow_classifier_block_escalates_to_judge() -> None:
    guard = StubGuardModel(
        verdict=GuardModelVerdict(decision="block", confidence=0.95, latency_ms=1.0)
    )
    judge = HeuristicLLMJudge()
    checker = _checker(guard=guard, judge=judge)
    text = "Cure period before a lease default triggers eviction"
    result = checker.check(text)
    assert result.decision == "allow"
    assert result.resolution_gate == "llm_judge"
    assert "structural_allow→classifier_disagree→llm_judge" in result.details.get("decision_source", "")
    assert judge.call_count >= 1


def test_structural_allow_classifier_block_wins_without_judge() -> None:
    guard = StubGuardModel(
        verdict=GuardModelVerdict(decision="block", confidence=0.95, latency_ms=1.0)
    )
    checker = _checker(guard=guard, judge=None)
    text = "Right of first refusal in a commercial lease"
    result = checker.check(text)
    assert result.decision == "allow"
    assert result.resolution_gate == "structural"
    assert "structural_wins" in result.details.get("decision_source", "")


def test_structural_continue_classifier_block_still_unilateral() -> None:
    guard = StubGuardModel(
        verdict=GuardModelVerdict(decision="block", confidence=0.90, latency_ms=1.0)
    )
    checker = _checker(guard=guard, judge=None)
    text = "How do I write a Python function to sort a list?"
    result = checker.check(text)
    assert result.decision == "block"
    assert result.resolution_gate == "guard_model_first"


def test_classifier_disagrees_with_structural_allow() -> None:
    guard = StubGuardModel()
    checker = _checker(guard=guard, judge=None)
    assert checker._classifier_disagrees_with_structural_allow(
        GuardModelVerdict(decision="block", confidence=0.90)
    )
    assert checker._classifier_disagrees_with_structural_allow(
        GuardModelVerdict(decision="uncertain", confidence=0.50)
    )
    assert not checker._classifier_disagrees_with_structural_allow(
        GuardModelVerdict(decision="allow", confidence=0.10)
    )
    assert not checker._classifier_disagrees_with_structural_allow(
        GuardModelVerdict(decision="block", confidence=0.50)
    )
