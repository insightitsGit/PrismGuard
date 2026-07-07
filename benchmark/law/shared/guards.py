from __future__ import annotations

import time
from typing import Protocol

from benchmark.law.shared.types import GuardOutcome


class GuardGate(Protocol):
    name: str

    def check(self, text: str) -> GuardOutcome: ...


class PrismGuardGate:
    name = "prismguard"

    def __init__(self) -> None:
        from prismguard.runtime.check import RuntimeChecker
        from prismguard.seed import import_bundled_seed, load_bundled_seed
        from prismguard.storage import create_storage
        from prismguard.taxonomy.embedder import HashEmbedder

        self._storage = create_storage("memory")
        parsed = load_bundled_seed(profile="authored")
        import_bundled_seed(self._storage, profile="authored")
        overlay = __import__("pathlib").Path(__file__).resolve().parents[1] / "data" / "legal_attacks.yaml"
        from prismguard.seed.parse import parse_seed_file
        from prismguard.seed import import_seeds

        import_seeds(self._storage, parse_seed_file(overlay), mode="update")
        self._checker = RuntimeChecker.from_storage(
            self._storage, parsed, embedder=HashEmbedder()
        )

    def check(self, text: str) -> GuardOutcome:
        start = time.perf_counter()
        result = self._checker.check(text)
        elapsed = (time.perf_counter() - start) * 1000
        return GuardOutcome(
            decision=result.decision,
            resolution_gate=result.resolution_gate,
            guardrail=self.name,
            guard_llm_calls=0,
            latency_ms=elapsed,
            mapped_category=result.matched_category,
            details=result.details,
        )


class RebuffGate:
    name = "rebuff"

    def __init__(self) -> None:
        import os

        self._client = None
        api_token = os.environ.get("REBUFF_API_TOKEN")
        api_url = os.environ.get("REBUFF_API_URL", "https://playground.rebuff.ai")
        if api_token:
            from rebuff import Rebuff

            self._client = Rebuff(api_token=api_token, api_url=api_url)
            return
        # Self-hosted SDK path when OpenAI + Pinecone env vars present
        openai_key = os.environ.get("OPENAI_API_KEY")
        pinecone_key = os.environ.get("PINECONE_API_KEY")
        pinecone_index = os.environ.get("PINECONE_INDEX")
        if openai_key and pinecone_key and pinecone_index:
            from rebuff import RebuffSdk

            self._client = RebuffSdk(openai_key, pinecone_key, pinecone_index)

    def check(self, text: str) -> GuardOutcome:
        start = time.perf_counter()
        if self._client is None:
            return GuardOutcome(
                decision="gray",
                resolution_gate="rebuff_unconfigured",
                guardrail=self.name,
                latency_ms=(time.perf_counter() - start) * 1000,
                details={"error": "Set REBUFF_API_TOKEN or OPENAI+PINECONE for real Rebuff"},
            )
        elapsed = (time.perf_counter() - start) * 1000
        if hasattr(self._client, "detect_injection"):
            metrics, is_injection = self._client.detect_injection(text)
            _ = metrics
            decision = "block" if is_injection else "allow"
            return GuardOutcome(
                decision=decision,
                resolution_gate="rebuff_detect",
                guardrail=self.name,
                guard_llm_calls=1,
                latency_ms=elapsed,
                mapped_category="direct_instruction_override" if is_injection else "benign_adjacent",
            )
        result = self._client.detect_injection(text)
        is_injection = bool(getattr(result, "injection_detected", False))
        return GuardOutcome(
            decision="block" if is_injection else "allow",
            resolution_gate="rebuff_sdk",
            guardrail=self.name,
            guard_llm_calls=1,
            latency_ms=elapsed,
            mapped_category="direct_instruction_override" if is_injection else "benign_adjacent",
        )


class NemoGuardrailsGate:
    name = "nemo_guardrails"

    def __init__(self) -> None:
        self._rails = None
        config_path = __import__("pathlib").Path(__file__).resolve().parents[2] / "lnl" / "config"
        try:
            from nemoguardrails import RailsConfig
            from nemoguardrails.rails.llm.llmrails import LLMRails

            config = RailsConfig.from_path(str(config_path))
            self._rails = LLMRails(config)
        except Exception as exc:  # pragma: no cover - optional heavy dep
            self._init_error = str(exc)

    def check(self, text: str) -> GuardOutcome:
        start = time.perf_counter()
        if self._rails is None:
            return GuardOutcome(
                decision="gray",
                resolution_gate="nemo_unconfigured",
                guardrail=self.name,
                latency_ms=(time.perf_counter() - start) * 1000,
                details={"error": getattr(self, "_init_error", "nemoguardrails not installed")},
            )
        try:
            result = self._rails.generate(messages=[{"role": "user", "content": text}])
            blocked = result.get("blocked", False) or "blocked" in str(result).lower()
        except Exception as exc:
            return GuardOutcome(
                decision="gray",
                resolution_gate="nemo_error",
                guardrail=self.name,
                latency_ms=(time.perf_counter() - start) * 1000,
                details={"error": str(exc)},
            )
        return GuardOutcome(
            decision="block" if blocked else "allow",
            resolution_gate="nemo_rails",
            guardrail=self.name,
            guard_llm_calls=1 if blocked else 0,
            latency_ms=(time.perf_counter() - start) * 1000,
            mapped_category="direct_instruction_override" if blocked else "benign_adjacent",
        )
