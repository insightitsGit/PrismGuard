# Handoff QA-001 — Fix `/v1/scan-output` resolution_gate contract

**ID:** HO-PrismGaurd-001  
**Director / QA:** Senior QA (workspace `C:\code\QA`)  
**To:** dev-agent  
**Priority:** P0  
**Status:** Ready for QA  
**Date issued:** 2026-07-09  
**Source path:** this repo (`C:\code\PrismGaurd`)  
**QA mirror:** `C:\code\QA\projects\PrismGaurd\handoffs\2026-07-09-fix-scan-output-http.md`  
**Bug:** `C:\code\QA\projects\PrismGaurd\bugs\BUG-PrismGaurd-001-scan-output-resolution-gate.md`  
**Review:** `C:\code\QA\projects\PrismGaurd\reviews\2026-07-09-full-codebase.md` (CR-001)

> **Dev:** set Status → `In Progress` while working. When done, write `handoffs/handoffbackQa001-scan-output.md` and set Status → `Ready for QA`. Do not close the QA bug — QA verifies.

---

## 0. Why

Business HTTP `POST /v1/scan-output` **always 500s**. The handler reads `scan.resolution_gate`, but `OutputScanResult` has no such field. Library tests call `scan_output()` directly and never hit the HTTP adapter, so CI stayed green.

---

## Objective

Make `POST /v1/scan-output` return a valid `ScanOutputResponse` for allow and block paths, with an auditable `resolution_gate` consistent with `/v1/check`.

---

## Background

- `scan_output()` in `prismguard/runtime/output_scan.py` returns `OutputScanResult(decision, matched_pattern, details)`.
- `prismguard/http/service.py` (~lines 162–167) builds:

```python
return ScanOutputResponse(
    decision=scan.decision,
    resolution_gate=scan.resolution_gate,  # AttributeError — field missing
    matched_pattern=scan.matched_pattern,
    details=scan.details,
    latency_ms=...,
)
```

- `OutputScanResult` (`output_scan.py:11-14`) only has `decision`, `matched_pattern`, `details`.

---

## Tasks

### T1 — Add `resolution_gate` to `OutputScanResult` (preferred)

**Files:** `prismguard/runtime/output_scan.py`

- On **block**: e.g. `"output_pattern"`
- On **allow**: e.g. `"output_allow"`
- Set the field in every `OutputScanResult(...)` construction path inside `scan_output()`.

**Exit:** dataclass includes `resolution_gate: str`; library callers get a stable audit gate.

### T2 — Confirm HTTP handler mapping

**Files:** `prismguard/http/service.py`

- Keep mapping `resolution_gate=scan.resolution_gate` once T1 lands (or map explicitly if you choose not to extend the dataclass — T1 preferred).
- Do not change `/v1/check` response shape unless required for consistency.

**Exit:** no `AttributeError`; response matches `ScanOutputResponse`.

### T3 — HTTP regression tests

**Files:** `tests/test_http_service.py` (new); update `tests/test_phases_complete.py` if the dataclass grows

- Use FastAPI `TestClient` against `create_app()`.
- License: existing fixture pattern in `tests/test_licensing.py` / `tests/support/license_fixture.py`, or `PRISMGUARD_DEV_UNRESTRICTED=1`.
- Cases: **allow** (benign text) and **block** (exfil-like sample already used in `test_phases_complete.py`).

**Exit:** a test that would have failed on current code (500 / AttributeError) and passes after the fix.

---

## Constraints

- Keep OSS `scan_output()` usable without FastAPI installed.
- Do not weaken existing passing tests to make new ones pass.
- Full relevant pytest green after the change.
- Commit/push only when the Director asks.
- Prefer adding the field on the dataclass so CLI/future callers share the same audit vocabulary as HTTP.

---

## Files to touch

| File | Action |
|------|--------|
| `prismguard/runtime/output_scan.py` | Modify — add gate field |
| `prismguard/http/service.py` | Modify only if mapping needed |
| `tests/test_http_service.py` | Create — TestClient |
| `tests/test_phases_complete.py` | Modify — assert new field if needed |

---

## Acceptance criteria

- [ ] `POST /v1/scan-output` returns **200** for benign and exfil-like samples
- [ ] `resolution_gate` present and stable (`output_allow` / `output_pattern` or equivalent)
- [ ] Existing `scan_output` unit tests updated and pass
- [ ] No regression in `/v1/check`

---

## Verification steps

1. `pip install -e ".[serve,enterprise,dev]"`
2. `PRISMGUARD_DEV_UNRESTRICTED=1 pytest tests/test_http_service.py tests/test_phases_complete.py -q`
3. Optional manual: start `prismguard-serve`, curl allow + block payloads to `/v1/scan-output`

---

## Hand back

Write **`handoffs/handoffbackQa001-scan-output.md`** with:

- Status: Ready for QA (or Blocked + question)
- Files changed
- Commands run + results
- Deviations from this handoff
- Suggested QA checks

QA will verify from the QA workspace and close BUG-001 / this handoff, or issue a follow-up.
