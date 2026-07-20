# Handback — PerfLatency1

**Handoff:** HO-PerfLatency1  
**Status:** Ready for QA  
**Date:** 2026-07-20  

## Delivered

1. **`create_checker_for_app("low_latency")`** — ONNX required + `classifier_mode: hybrid` (rules/structural before ONNX)
2. **`security_bench`** keeps **`classifier_mode: first`** for scorecard parity
3. **`PRISMGUARD_CLASSIFIER_MODE`** + factory `classifier_mode=` override
4. ORT: auto provider pick (CUDA → Dml → CoreML → CPU), `PRISMGUARD_ORT_PROVIDERS`, sequential exec, dual warmup
5. Cancel orphaned classifier futures on short-circuit (`first` mode)
6. Tier-1 seed rules + structural patterns for stack jailbreaks (DAN/jailbreak mode/system-prompt exfil/from-now-on)
7. Scripts: `scripts/latency_by_gate.py`, `scripts/s1_miss_analysis.py`
8. Docs: README four-path table, integration-guide, scorecard, ai-overview, ChorusGraph example → `low_latency`
9. `prismguard caps` reports `classifier_mode`

## How PrismShine / stacks should wire

```python
checker = create_checker_for_app("low_latency")
```

```bash
python scripts/latency_by_gate.py --profile low_latency
python scripts/latency_by_gate.py --profile security_bench   # contrast always-on ONNX
python scripts/s1_miss_analysis.py --profile low_latency --attacks PATH_TO_S1
```

## Acceptance

- Production path no longer defaults integrators into always-on ONNX
- Scorecard path (`security_bench` / `first`) unchanged in methodology
- Measurable classifier_invoked_rate drop under hybrid on mixed prompts
- FN list from `s1_miss_analysis` drives next rules/retrain iteration
