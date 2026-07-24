# PrismGuard 0.1.10

**Date:** 2026-07-23  
**Theme:** `domain_pilot` (any domain) + train-first accuracy path + finance starter ONNX

## Highlights

- **`domain_pilot`** — canonical taxonomy/learn profile for **any** domain (`domain=` or `PRISMGUARD_DOMAIN`). Not law-only.
- **`law_pilot` deprecated** — alias for `domain_pilot` + `domain=law` only. Env `PRISMGUARD_DOMAIN` cannot hijack the alias.
- **Train first, then pilot** — docs + train CLI steer: label → `prismguard-model train` → gate → `domain_pilot` + matching `PRISMGUARD_ARTIFACT_ID`.
- **Optional starter downloads** — `prismguard-model download --domain law|finance|healthcare` (no accuracy guarantee on your traffic).
- **Finance structural PI** — Tier-1 / structural hardening for finance mid holdouts on hub path (no Judge required for that claim).
- **Custom domains** — any slug; bundled packs optional; `PRISMGUARD_DOMAIN_ROOT` / auto-scaffold supported.
- **Caps exit code** — `domain_pilot` / `law_pilot` without ONNX ready return non-zero (honest half-stack signal).

## Install

```bash
pip install -U "prismguard[guard-model,prism]==0.1.10"
prismguard-model download --domain finance   # optional starter
export PRISMGUARD_DOMAIN=finance
export PRISMGUARD_ARTIFACT_ID=prism-pi-finance-v1
export PRISMGUARD_USE_ONNX=1
prismguard caps --profile domain_pilot
```

## Accuracy path (copy this)

```text
1. Train (or starter download) for YOUR domain
2. Point PRISMGUARD_ARTIFACT_ID + PRISMGUARD_DOMAIN
3. create_checker_for_app("domain_pilot", domain="<domain>", use_onnx=True)
```

Do **not** invent `finance_pilot` / `healthcare_pilot`.

## Artifacts

| Artifact | PyPI wheel | GitHub Release | Notes |
|----------|------------|----------------|-------|
| `prism-pi-v1` (law) | metadata only | reuse `v0.1.2` asset | unchanged |
| `prism-pi-finance-v1` | metadata only | **upload with `v0.1.10`** | preserve-retrain sha registered in `artifact_fetch.py` |
| `prism-pi-healthcare-v1` | metadata only | **upload with `v0.1.10`** | sha registered in `artifact_fetch.py` |

`model.onnx` never ships in the wheel.

## Breaking / migration

- Prefer `domain_pilot` + `domain=…` over `law_pilot` for new code.
- `create_checker_for_app("law_pilot")` always uses **law**, even if `PRISMGUARD_DOMAIN` is set to another vertical.
- Bare `domain_pilot` without domain raises (no silent law default).

## Test status (pre-publish)

- `pytest tests/` — green (**244** passed, 2 skipped on maintainer machine)
- Hub FAQ gate — green
- Wheel build — **4.05 MB**, no `model.onnx`; `twine check` PASSED
- Base / rules check — `prismguard check "hello there"` → ALLOW
- Finance mid local rescore (`web_chat`, ONNX off, no Judge): **20/20** attack block, **10/10** benign allow
- Healthcare starter trained locally (`prism-pi-healthcare-v1`); Release asset upload required before `download --domain healthcare` works for customers
