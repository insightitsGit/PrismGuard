# Handoff DX-ScorecardPath1 — quick-start vs scorecard path

**ID:** HO-DX-ScorecardPath1  
**From:** PrismShine stack-suite (2026-07-20)  
**Status:** Ready for QA  
**Handback:** [`handoffbackDxScorecardPath1.md`](handoffbackDxScorecardPath1.md)  


## Problem

Integrators used `web_chat` / `rules_only`, compared results to the law scorecard, and concluded Guard is weak. Config mismatch, predictable DX failure.

## Ask

1. README above-the-fold path table (`web_chat` vs scorecard/`law_pilot`+ONNX)
2. Scorecard / COMPARISON_REPORT: do not expect those rates from `web_chat`
3. Optional: `security_bench` profile fails loudly if ONNX missing

## Acceptance

New integrator reading first screen of README knows which factory matches the scorecard.
