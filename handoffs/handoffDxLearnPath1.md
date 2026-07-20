# Handoff DX-LearnPath1 — scorecard / learn-from-seed features invisible to integrators

**ID:** HO-DX-LearnPath1  
**From:** PrismShine insight-stack (2026-07-20)  
**Related:** HO-DX-ScorecardPath1 (factory vs scorecard labeling)  
**Status:** Ready for QA  
**Handback:** [`handoffbackDxLearnPath1.md`](handoffbackDxLearnPath1.md)  
**Severity:** High — docs caused under-configured production-shaped integration  

## Problem

Integrators follow README quick-start and ship a path that looks intentional but omits features Guard’s law scorecard and “learn from our words / DB” story depend on (`[prism]`, feedback persist, storage, lexicon, ChorusGraph helpers). APIs exist; docs hierarchy hides the full path.

## Ask

1. README three-row table: hub vs scorecard vs **learn-from-seed**
2. Scorecard page: extras/env checklist + latency note
3. Single “learn from seed / DB / words” recipe (OSS vs Team+)
4. ChorusGraph law/security wiring (not only `web_chat`)
5. `security_bench` warning: loud ONNX fail but **disables taxonomy**
6. Optional: capability readiness helper (`onnx_ready`, `prismrag_taxonomy`, …)

## Acceptance

- First screen distinguishes hub vs scorecard vs learn-from-seed
- Scorecard lists exact extras/env of cited run
- “Learns from DB/words” never without Team+ storage and/or seed+`[prism]`+feedback
- ChorusGraph example includes law wiring
- Scorecard methodology unchanged (labeling / discoverability; readiness helper OK)
