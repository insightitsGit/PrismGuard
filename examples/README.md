# PrismGuard examples

Runnable sketches for each [feature row](../README.md#pick-your-features).  
Best-practice guidance: [`docs/best-practices.md`](../docs/best-practices.md).

| Script | Feature | Needs |
|--------|---------|-------|
| [`01_hub_web_chat.py`](01_hub_web_chat.py) | #1 Hub FAQ | `pip install prismguard` |
| [`02_light_onnx.py`](02_light_onnx.py) | #2 Light ONNX | `[guard-model]` + `prismguard-model download` |
| [`03_heavy_onnx.py`](03_heavy_onnx.py) | #3 Heavy ONNX | same |
| [`04_learn_from_seed.py`](04_learn_from_seed.py) | #5–#6 Learn loop | `[guard-model,prism]` + download + env |
| [`05_shadow_onnx.py`](05_shadow_onnx.py) | #7 Shadow ONNX | `[guard-model]` + download |
| [`06_output_scan.py`](06_output_scan.py) | #12 Output scan | `pip install prismguard` |
| [`chorusgraph_hub_guard.py`](chorusgraph_hub_guard.py) | #10 Hub graph | `web_chat` |
| [`chorusgraph_law_guard.py`](chorusgraph_law_guard.py) | #10 Stack graph | `light` (+ download) |

## Compare which profile is best on your machine

```bash
pip install "prismguard[guard-model]"
prismguard-model download
python scripts/compare_profiles.py
```

Measured results + recommendation are reflected in the README: [Which profile is best? (measured)](../README.md#which-profile-is-best-measured).  
Details / do-don’t: [`docs/best-practices.md`](../docs/best-practices.md#which-is-best).
