# Handback Buglib1 — base PyPI install must work with zero extras

**From:** engineer  
**To:** Director / Architect  
**Status:** Ready for review  
**Date:** 2026-07-09  
**Handoff:** `handoffs/handoffBuglib1.md`

---

## T1 — Lazy numpy/onnxruntime imports — PASS

**Files changed**
- `prismguard/models/deps.py` (new) — `require_numpy` / `require_onnxruntime` / `require_tokenizers_tokenizer` with actionable `ImportError` pointing at `pip install prismguard[guard-model]`
- `prismguard/models/onnx_classifier.py` — removed module-scope `import numpy`; ML imports via `deps`
- `prismguard/models/calibration.py` — lazy numpy in `fit_temperature`
- `prismguard/models/loader.py` — lazy import of `get_or_load_classifier`
- `prismguard/runtime/guard_model.py` — lazy import of loader helpers inside `PrismONNXGuardModel.__init__`
- `prismguard/app_cli.py` — `create_guard_model` imported only inside `cmd_doctor`; doctor reports actionable detail when not ready
- `prismguard/taxonomy/graph.py` — lazy numpy at use sites
- `prismguard/runtime/check.py` — `TaxonomyGraphEngine` / guard-model types deferred (TYPE_CHECKING + lazy init import)
- `prismguard/models/__init__.py` — lazy `__getattr__` re-exports
- `prismguard/http/service.py` — lazy `RuntimeChecker`; clear `[serve]` errors for `create_app` / `main`
- `prismguard/tools/profile_pipeline.py` — wheel-safe `--help` when `scripts/` is absent

**Fresh-venv install output (fixed wheel, zero extras, cwd=`%TEMP%` so repo does not shadow site-packages):**

```text
=== FIXED: prismguard --help ===
usage: prismguard [-h] {init,doctor,check,context,domains,eval} ...

PrismGuard setup and diagnostics

=== FIXED: doctor guard_model ===
      "name": "guard_model",
      "ok": false,
      "detail": "guard model not ready — install extras and download artifacts: pip install prismguard[guard-model] && prismguard-model download"

=== FIXED freeze ===
annotated-types==0.7.0
prismguard @ file:///C:/code/PrismGaurd/dist/prismguard-0.1.3-py3-none-any.whl#...
pydantic==2.13.4
pydantic_core==2.46.4
PyYAML==6.0.3
typing-inspection==0.4.2
typing_extensions==4.16.0
```

No `numpy` / `onnxruntime` in the freeze. `doctor` exits non-zero with `ok: false` (expected without extras/artifacts) but **does not crash**.

---

## T2 — Audit remaining extras — PASS

| Extra | Eager in base CLI chain? | Notes |
|-------|--------------------------|-------|
| `guard-model` (numpy/ort/tokenizers) | **Fixed** — lazy via `deps` / loader / guard_model | |
| `serve` (fastapi/uvicorn) | Already lazy; now clear `SystemExit`/`ImportError` | Hard-requires extra to run |
| `enterprise` (cryptography) | Already lazy in `validator.py` | |
| `seed` (pyarrow) | Lazy in parquet format reader | `--help` OK |
| `embeddings` / `prism` / vector DBs | Lazy or try/except at use | |
| `train` (`models/train.py` still has top-level numpy) | **OK** — only imported by train subcommands, not base CLI | |

**Entry points tested (fixed wheel, zero extras):**

| Entry point | Result |
|-------------|--------|
| `prismguard --help` | PASS |
| `prismguard doctor` | PASS (degrades: `guard_model ok: false` + install hint) |
| `prismguard-seed --help` | PASS |
| `prismguard-model --help` | PASS |
| `prismguard-profile --help` | PASS (wheel help; full profile needs source checkout) |
| `prismguard-serve` | PASS as hard-require: `prismguard-serve requires the serve extra: pip install prismguard[serve]` |

---

## T3 — CI base-install job — PASS (with fail-gate proof)

**Files changed:** `.github/workflows/ci.yml` — new job `base-install` builds the wheel, installs with zero extras, runs the entry points above.

**Proof the gate catches the bug** (mutated *installed* site-packages only, cwd=`%TEMP%`):

```text
=== PROOF (expect ModuleNotFoundError: numpy) ===
  File "...\site-packages\prismguard\app_cli.py", line 17, in <module>
    from prismguard.runtime.guard_model import create_guard_model
  ...
  File "...\site-packages\prismguard\models\onnx_classifier.py", line 3, in <module>
    import numpy as np
ModuleNotFoundError: No module named 'numpy'
exit=1
```

Same wheel without the mutation: `--help` / `doctor` succeed (see T1).

---

## T4 — Production license key gate — PASS (docs only)

**Files changed:** `docs/enterprise-product-model.md` — new section **Production license key gate (Business / Enterprise)** stating no real customer licenses against the current ChorusGraph-shared dev/CI public key; steps for Director to generate a production keypair and update `_LICENSE_PUBLIC_KEY_B64`.

No code change to `keys.py` (correct — swap is a business-process gate).

---

## Also covered from QA-001 (same session)

`POST /v1/scan-output` `resolution_gate` fix remains in tree (`OutputScanResult.resolution_gate`, HTTP tests). See `handoffs/handoffbackQa001-scan-output.md`.

---

## PyPI actions

**None taken.** No yank of `0.1.3`, no new upload. Awaiting Director go-ahead for a new version release + yank of broken `0.1.3`.

## Commits

**None** (Director did not ask).

## Blocked / open

- Release version bump + PyPI publish/yank still need Director explicit approval.
- `prismguard-profile` full run still requires a source checkout (`scripts/` not in wheel) — intentional; `--help` works from the wheel.
