# Hub benign FAQ suite

Release gate for **general / web_chat** dogfood before enabling ONNX enforce.

## Purpose

`prism-pi-v1` is **law-bench-oriented**. Product hubs (pricing, install, “Hi”) must not turn on `PRISMGUARD_USE_ONNX=1` until:

1. Rules-only path allows the benign FAQ set (this folder + `tests/test_hub_benign_faq.py`).
2. With ONNX + `classifier_mode: first`, FP rate on ≥200 benign prompts is **&lt;0.5%** (CI starts stricter: any block on the core FAQ set fails until calibrated).
3. Warm rules-path p95 check **&lt;50ms** (document separately from cold first-import).

## Files

| File | Role |
|------|------|
| `benign_faq.txt` | One prompt per line (≥200) |
| `../tests/test_hub_benign_faq.py` | Pytest gate |

## Run

```bash
pytest tests/test_hub_benign_faq.py -q
# Optional ONNX FP probe (skipped if artifact missing):
PRISMGUARD_HUB_ONNX_GATE=1 pytest tests/test_hub_benign_faq.py -q -k onnx
```
