# Handoff Buglib1 — fix the published PyPI package before pointing anyone at it

**Director:** Amin · **Architect:** Claude · **Engineer:** (receiving agent)
**Refs:** [`https://pypi.org/project/prismguard/0.1.3/`](https://pypi.org/project/prismguard/0.1.3/) (the broken release) · [`docs/enterprise-product-model.md`](../docs/enterprise-product-model.md) · [`prismguard/licensing/keys.py`](../prismguard/licensing/keys.py), [`validator.py`](../prismguard/licensing/validator.py)
**Date issued:** 2026-07-09

---

## 0. Why

Verified directly against the real, published wheel (`pip download prismguard==0.1.3`, installed in a clean venv, not read from source) — not from a claim, from actually running it. Two findings:

1. **Critical, ships-broken bug:** `pip install prismguard` (the exact command in the README's own "Quick install") crashes on every command, including `prismguard --help` and `prismguard doctor`, with `ModuleNotFoundError: No module named 'numpy'`. Root cause: `prismguard/models/onnx_classifier.py` does `import numpy as np` unconditionally at module load time. That module gets pulled in by the base import chain (`prismguard.runtime` → `runtime.check` → `runtime.guard_model` → `models.loader` → `models.onnx_classifier`) regardless of whether the caller ever touches the classifier — and since `classifier_mode: first` is the shipped default, this path is *always* imported. `numpy`/`onnxruntime` are correctly declared under the `[guard-model]` extra in `pyproject.toml`, but the import isn't lazy, so declaring them as optional doesn't actually make them optional. Confirmed the fix path directly: `pip install "prismguard[guard-model]"` resolves it completely — `doctor` then passes with `"guard_model": {"ok": true, "artifact_id": "prism-pi-v1"}`.

2. **Non-urgent, self-disclosed readiness gap:** license validation runs against a dev/CI Ed25519 key explicitly shared with ChorusGraph (`keys.py`'s own comment: *"replace with production public key for customer licenses"*). Not a leaked secret — it's the public half, correctly public. But real Business/Enterprise licenses must not be issued against this key.

**No overwriting 0.1.3.** PyPI doesn't allow re-uploading a version; ship the fix as a new version and yank the broken one only once the new one is confirmed working — yanking is a public, external action, get the Director's explicit go-ahead before doing it (T2 below), don't do it as a side effect of landing the code fix.

**Standing rules:**
- **Test against the actual built wheel installed in a clean venv, not against the source tree.** The bug that prompted this handoff was invisible from source (imports look fine reading the file in isolation) and only showed up on a real `pip install` with nothing else in the environment. `pytest` passing in the dev environment (which already has numpy/onnxruntime installed from other extras) does not prove the base package works.
- **Audit the entire import chain for the same class of bug**, not just the one file found. Anything gated behind an `extra =` in `pyproject.toml` must be imported lazily (inside the function that uses it), never at module top level, or the extra isn't actually optional.
- Full test suite green after every task. Commit/push only when the Director asks. **Do not yank or re-release anything on PyPI without the Director's explicit go-ahead**, even after the fix is confirmed — that's an external, public action, not an internal one.

---

## PART A — Fix the crash

### T1 — Make the numpy/onnxruntime import lazy
**Files:** `prismguard/models/onnx_classifier.py`, `prismguard/models/loader.py`

Move `import numpy as np` (and any `onnxruntime` import in the same chain) out of module scope and into the function that actually needs it (e.g., inside `get_or_load_classifier()`), so `import prismguard` and CLI commands that don't invoke the classifier never require the ML stack.

Where the classifier genuinely is needed (e.g., `classifier_mode: first` at runtime with no `[guard-model]` extra installed), raise a clear, actionable error — not a bare `ModuleNotFoundError` — e.g. `"classifier_mode='first' requires the guard-model extra: pip install prismguard[guard-model]"`. This is the same discipline `validator.py` already uses for the `cryptography` import (see its `except ImportError` block) — match that pattern.

**Exit:** in a **fresh venv**, `pip install` the locally-built wheel (not the dev environment) with **no extras**, then run `prismguard --help` and `prismguard doctor` — both must succeed. `doctor`'s `guard_model` check should report `ok: false` with a clear, actionable message (not crash) when the extra isn't installed.

### T2 — Audit the rest of the package for the same bug class
**Files:** whole `prismguard/` import graph

Grep every `extra = "..."` in `pyproject.toml`, then trace each corresponding module's imports to confirm none of them are pulled in eagerly by something in the base import chain. Specifically check the `[serve]` (fastapi/uvicorn), `[seed]` (pyarrow), and `[enterprise]`/licensing (`cryptography`) paths the same way T1 checked `[guard-model]`.

**Exit:** a fresh-venv, no-extras install successfully runs `prismguard --help`, `prismguard doctor`, `prismguard-seed --help`, `prismguard-model --help`, `prismguard-profile --help` — every entry point, not just the main one. Document which commands correctly degrade (report "extra not installed") vs. which are expected to hard-require an extra (e.g., `prismguard-serve` genuinely needs `[serve]` to do anything — that's fine, as long as it fails with a clear message, not a raw traceback).

### T3 — Add this as a standing CI check, not just a one-time fix
**Files:** CI workflow (`.github/workflows/ci.yml` per the README's badge)

Add a job that builds the wheel, installs it in a clean environment with **zero extras**, and runs the base entry points from T1/T2. This is the regression test that would have caught this before it shipped — without it, the same class of bug (an extra declared but not actually lazy) can silently ship again.

**Exit:** CI job exists, passes on the fixed code, and — as a sanity check — fails if you temporarily revert T1's fix locally (prove the gate actually catches the bug, don't just assume it would).

---

## PART B — License key readiness (no code change required yet, just don't skip this)

### T4 — Gate real paid licensing on a real production key
**Files:** `docs/enterprise-product-model.md`, `prismguard/licensing/keys.py`

Document explicitly (if not already) that Business/Enterprise licenses cannot be issued until a production Ed25519 keypair is generated, the private half held securely (not shared with ChorusGraph's dev/CI key), and `_LICENSE_PUBLIC_KEY_B64` in `keys.py` is updated to the production public key. This is a business-process gate, not a code task — the code already supports swapping it in (`license_public_key_bytes()`), it just hasn't been done.

**Exit:** a clear, written statement in `enterprise-product-model.md` that no real customer license gets issued against the current dev/CI key, and who/how the production key gets generated when it's actually time to sell.

---

## Order & effort

T1 first (the actual crash). T2 can run in parallel once T1's pattern is established — same fix, applied everywhere. T3 depends on T1/T2 being done, since it's the regression test for both. T4 is a documentation/process task, independent of the others, do it whenever.

Rough estimate: T1: 2-3h · T2: 2-3h (mostly verification, the fix pattern is already known from T1) · T3: 1-2h · T4: 30min.

## Return format (`handoffbackBuglib1.md`)

Per task: files changed · exit criteria pass/fail with **actual fresh-venv install output pasted**, not summarized · for T2, the full list of entry points tested and their pass/fail · for T3, proof the CI gate actually fails without the fix (not just that it passes with it) · confirmation no PyPI action (yank, new release) was taken without the Director's explicit go-ahead · anything blocked, stated plainly. No commits unless the Director asks.

---
*Buglib1 · the base `pip install prismguard` must work with zero extras, since that's the exact command advertised in the README · fix is a lazy-import pattern, applied consistently, with a CI gate so it can't silently regress · license-key production-readiness is a documented business gate, not a code fix, and isn't urgent unless a real sale is imminent.*
