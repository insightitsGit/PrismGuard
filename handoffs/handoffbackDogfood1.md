# Handback — Dogfood1 (vNext from insightits.com dogfood)

**Handoff:** HO-Dogfood1  
**Status:** Ready for QA  
**Date:** 2026-07-09  

## Summary

Implemented the dogfood vNext plan: offline/rules-only init, app factory with `PRISMGUARD_USE_ONNX` opt-in, hub FAQ gate, stronger Tier-1/structural, domain default away from law, metrics + shadow ONNX, ChorusGraph hub example.

## Locked decisions (implemented)

| Decision | Implementation |
|----------|----------------|
| ONNX off until hub calibration | `PRISMGUARD_USE_ONNX=1` required; `from_storage` no longer surprise-loads |
| Harden FNs | Seed rules R-0144–R-0146, R-0202 + structural DAN/disregard/SYSTEM |
| HF cold start P0 | `prefer_transformer: false`, offline skip taxonomy, HashEmbedder defaults |
| Domain ≠ law | Env unset → core; `general` pack; `web_chat` profile |
| Hub success criteria | `benchmark/hub/` + `tests/test_hub_benign_faq.py` |

## Key files

- `prismguard/runtime/factory.py` — `create_checker_rules_only`, `create_checker_for_app`, shadow wrapper
- `prismguard/runtime/check.py` — ONNX opt-in auto-load, `metrics_snapshot`, gray_only classifier-only fix
- `prismguard/cli_check.py`, `prismguard/http/service.py` — factory wiring
- `prismguard/domains/general/` — minimal general pack
- `benchmark/hub/benign_faq.txt` — ≥200 benign prompts
- `examples/chorusgraph_hub_guard.py` — hub graph sketch
- `docs/integration-guide.md`, `README.md` — honesty + env contract

## Acceptance evidence

```text
pytest tests/ -q
# 192 passed, 2 skipped
```

- Rules-only / offline: no HF required; `create_checker_rules_only()` uses HashEmbedder
- `PRISMGUARD_USE_ONNX` unset → `_guard_model is None` in `create_checker_from_env`
- Hub FAQ: core set allowed; full suite FP &lt;0.5% on rules-only
- DAN / disregard / SYSTEM: override blocked on rules-only
- `metrics_snapshot()` + `details["shadow_onnx"]` available

## Not in this cut

- Retrain/publish new ONNX artifact
- Force ONNX on insightits.com
- Remove site regex defense-in-depth

## QA checklist

- [ ] Clean venv: `PRISMGUARD_OFFLINE=1` + `create_checker_for_app("web_chat")` — no HF Hub log
- [ ] `Hi` / pricing FAQ allow on rules-only
- [ ] Jailbreak samples block without ONNX
- [ ] `PRISMGUARD_USE_ONNX` unset on CLI/HTTP — no ONNX load
- [ ] Docs: `prism-pi-v1` described as law-bench-oriented
