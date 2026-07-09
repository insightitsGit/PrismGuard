# PrismGuard Roadmap (law-first)

**Status:** Law pilot must pass `scripts/adversarial_self_check.py` before any other work.

See **[law-pilot-readiness.md](law-pilot-readiness.md)** for the authoritative checklist, positioning, and feature freeze.

## Frozen until law is solid

- Healthcare / finance domain benchmarks
- Tenant context production path
- General-domain product expansion
- New advertisement suites beyond law cold holdout

## Honest product claim

**Cheaper + audited** guardrail for compliance-focused legal AI — not "beats LLM Guard on every paraphrase."

Every decision exposes a `resolution_gate` suitable for compliance logs. ONNX-first path targets ~200ms vs multi-second generative scanners.

## Completed recently

- `disagreement_escalation` — structural allow + classifier disagree → Judge, not veto
- Cold benign holdout discipline (`normal_scenarios_holdout.yaml`)
- Phrasing diversity enforcement (`benchmark/shared/holdout_quality.py`)
- Adversarial self-check gate (`scripts/adversarial_self_check.py`)

## Open blockers

1. **structural=continue + classifier FP** — training hard negatives + retrain (not architecture)
2. **Customer discovery** — talk to one real buyer after self-check passes

## General product (deferred)

Previous general-domain plans remain in git history but are **explicitly deferred** until law pilot is ship-ready. Do not grow `benchmark/general/` holdouts or wire general benchmarks into CI until law passes adversarial self-check.
