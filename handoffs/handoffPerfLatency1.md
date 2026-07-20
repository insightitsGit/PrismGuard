# Handoff PerfLatency1 — stack latency floor + S1 quality track

**ID:** HO-PerfLatency1  
**Status:** Ready for QA  
**Handback:** [`handoffbackPerfLatency1.md`](handoffbackPerfLatency1.md)  
**Date:** 2026-07-20  

## Problem

Stack S1 with `classifier_mode: first` pays ~450–500 ms ONNX on nearly every request. Quality ~0.75 vs llm-guard 1.0. Latency is the clear product issue; injection accuracy is good-not-best.

## Deliverables

1. `low_latency` factory profile (`hybrid` + ONNX required)
2. `security_bench` keeps `classifier_mode: first` for scorecard parity
3. ORT provider selection (CUDA/Dml/CPU) + env knobs
4. Cancel orphaned classifier futures on short-circuit (`first` mode)
5. Tier-1 / structural patterns for common stack jailbreaks
6. `scripts/latency_by_gate.py` + `scripts/s1_miss_analysis.py`
7. Docs: latency path labeling + `prismguard caps` classifier_mode
