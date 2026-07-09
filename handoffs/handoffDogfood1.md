# Handoff Dogfood1 — vNext from insightits.com dogfood

**ID:** HO-Dogfood1  
**Director:** Amin  
**Status:** Ready for QA  
**Date:** 2026-07-09  
**Source:** Website Hub / Dashboard Hub dogfood report (insightits.com)  
**Handback:** [`handoffbackDogfood1.md`](handoffbackDogfood1.md)

---

## Locked decisions

1. ONNX off in prod until hub calibration; library adds **shadow ONNX** (rules enforce, ONNX logged).
2. Harden Tier-1 / structural for DAN / disregard / fake SYSTEM in this repo.
3. HF cold start is a PrismGuard P0 — guarantee offline rules-only path.
4. Default domain is not law; law pack opt-in; `web_chat` profile for hubs.
5. Full dogfood success: hub FAQ FP &lt;0.5% on ≥200 prompts + warm rules p95 &lt;50ms before ONNX enforce.

## Phases

- **A (P0):** offline init, `create_checker_for_app`, `PRISMGUARD_USE_ONNX` opt-in, hub FAQ gate, docs honesty
- **B (P1):** stronger Tier-1/structural; domain default / matrix
- **C (P2):** metrics_snapshot, shadow ONNX, ChorusGraph hub example

## Acceptance

- Rules-only / offline: no HF Hub log; no numpy required for CLI help/doctor
- `PRISMGUARD_USE_ONNX` unset → no ONNX load in `create_checker_from_env`
- Hub benign suite exists; docs state `prism-pi-v1` is law-oriented
- DAN / disregard-rules / SYSTEM: override blocked on rules-only path
- `checker.metrics_snapshot()` + shadow details available

## Hand back

`handoffs/handoffbackDogfood1.md` when Ready for QA.
