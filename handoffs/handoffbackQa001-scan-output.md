# Handback QA-001 — Fix `/v1/scan-output` resolution_gate contract

**ID:** HO-PrismGaurd-001  
**From:** dev-agent  
**To:** Senior QA  
**Status:** Ready for QA  
**Date:** 2026-07-09  
**Handoff:** `handoffs/handoffQa001-scan-output.md`

---

## Summary

`OutputScanResult` now carries `resolution_gate`, set on every `scan_output()` return path. The HTTP adapter already mapped `scan.resolution_gate`; with the field present, `POST /v1/scan-output` returns 200 with a valid `ScanOutputResponse` for allow and block.

---

## Files changed

| File | Action |
|------|--------|
| `prismguard/runtime/output_scan.py` | Added `resolution_gate: str` to `OutputScanResult`; set `"output_pattern"` on block, `"output_allow"` on allow (including empty/whitespace) |
| `prismguard/http/service.py` | No change — existing mapping is correct |
| `tests/test_http_service.py` | Created — TestClient allow + block cases for `/v1/scan-output` |
| `tests/test_phases_complete.py` | Assert `resolution_gate` on library allow/block paths |
| `handoffs/handoffQa001-scan-output.md` | Status → Ready for QA |

---

## Commands run + results

```text
pip install -e ".[serve,enterprise,dev]" -q
$env:PRISMGUARD_DEV_UNRESTRICTED="1"
pytest tests/test_http_service.py tests/test_phases_complete.py -q
```

**Result:** `8 passed` in ~0.9s (after trimming an optional `/v1/check` smoke that pulled ML deps and hit a local Windows pyarrow access violation unrelated to this bug).

---

## Deviations

- Did not modify `prismguard/http/service.py` (T2 mapping already correct).
- Did not add a `/v1/check` HTTP regression in `test_http_service.py` — handoff acceptance focuses on `/v1/scan-output`; `/v1/check` shape unchanged. Existing licensing/metrics HTTP tests remain.

---

## Suggested QA checks

1. Re-run: `PRISMGUARD_DEV_UNRESTRICTED=1 pytest tests/test_http_service.py tests/test_phases_complete.py -q`
2. Confirm allow body: `decision=allow`, `resolution_gate=output_allow`
3. Confirm block body: `decision=block`, `resolution_gate=output_pattern`, `matched_pattern=suspicious_url` for the attacker URL sample
4. Optional: curl `POST /v1/scan-output` against a running `prismguard-serve` for both payloads
5. Spot-check `/v1/check` still 200 with its own `resolution_gate` vocabulary (no contract change expected)

QA owns closing BUG-001 / this handoff.
