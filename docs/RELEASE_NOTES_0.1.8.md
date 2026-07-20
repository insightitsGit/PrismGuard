# PrismGuard 0.1.8

**Date:** 2026-07-20  
**Theme:** DX path labeling + light/heavy ONNX + performance/docs for integrators

## Highlights

- **`light` / `heavy` profiles** (aliases `low_latency` / `security_bench`) — pick selective hybrid ONNX vs always-on scorecard ONNX
- **`prismguard caps`** + `guard_capabilities()` — capability truth table (`onnx_tier`, taxonomy, feedback, storage, …)
- **ORT providers** — auto CUDA/Dml/CoreML/CPU; `PRISMGUARD_ORT_PROVIDERS` override
- **Hybrid short-circuit** — cancel orphaned classifier futures on tier1/structural wins under `first`
- **Stack jailbreak rules** — Tier-1 + structural patterns (jailbreak mode, system-prompt exfil, from-now-on, …)
- **Docs** — README feature picker (#1–#13), measured light vs heavy table, examples, best practices
- **Scripts** — `compare_profiles.py`, `latency_by_gate.py`, `s1_miss_analysis.py`

## Install

```bash
pip install "prismguard[guard-model]==0.1.8"
prismguard-model download
```

```python
from prismguard.runtime.factory import create_checker_for_app

checker = create_checker_for_app("light")   # production
# checker = create_checker_for_app("heavy")  # scorecard
```

## Verify

```bash
prismguard caps --profile light
python scripts/compare_profiles.py   # from git checkout
prismguard eval self-check
```

## Notes

- ONNX weights still download separately (`prism-pi-v1` from GitHub Release v0.1.2) — unchanged
- `light`/`heavy` skip taxonomy; learn-from-seed still needs `law_pilot` + `[prism]` + feedback
- Law artifact may FP on short hub greetings — keep FAQ on `web_chat`
