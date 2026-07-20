# Handback — DX-ScorecardPath1

**Handoff:** HO-DX-ScorecardPath1  
**Status:** Ready for QA  
**Date:** 2026-07-20  

## Delivered

1. README above-the-fold **Which factory should I use?** table (`web_chat` vs `security_bench` / `law_pilot`+ONNX)
2. Scorecard + Benchmarks sections: **do not expect these rates from `web_chat` / `rules_only`**
3. `create_checker_for_app("security_bench")` — forces law+ONNX; **raises** if weights missing
4. `docs/scorecard.md` + `docs/integration-guide.md` path labeling
5. Tests for loud fail / ready path

## Acceptance

A new integrator reading the first screen of the README can tell which factory matches the scorecard. Scorecard methodology unchanged.
