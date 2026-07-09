# Handoff OnnxCustomer1 — Customer/hub ONNX training path

**ID:** HO-OnnxCustomer1  
**Director:** Amin  
**Status:** Ready for QA  
**Date:** 2026-07-09  
**Related:** Dogfood1 · external handoff “ONNX must not stay law-only” · PyPI 0.1.5  
**Handback:** [`handoffbackOnnxCustomer1.md`](handoffbackOnnxCustomer1.md)

---

## Defaults vs opt-in

| Knob | Default | Opt-in |
|------|---------|--------|
| ONNX enforce | Off | `PRISMGUARD_USE_ONNX=1` |
| Artifact | `prism-pi-v1` (law) when ONNX on | `PRISMGUARD_ARTIFACT_ID` / `PRISMGUARD_GUARD_MODEL_PATH` |
| Domain pack in train | None (bundled seed only) | `--domain-pack law\|general\|…` |
| Feedback persist | Off | `PRISMGUARD_FEEDBACK_PERSIST=1` |
| Calibration allows in export | Off | `--include-calibration-allows` |

## Problem

`prism-pi-v1` is law-bench-oriented. Hub benigns (`Hi`, pricing) block under ONNX enforce. Seed import does not retrain weights. Customer/hub traffic must feed train/calibrate before `PRISMGUARD_USE_ONNX=1`.

## Locked loop

```
Rules enforce (+ optional shadow ONNX)
  → labeled feedback (blocks + calibration allows)
  → prismguard feedback export
  → prismguard-model train (--feedback-jsonl / --domain-pack / --normal-txt)
  → eval gates (attack holdout + normal/FAQ allow)
  → artifact (prism-pi-hub-v1 or customer-pi-v1)
  → PRISMGUARD_USE_ONNX=1 + PRISMGUARD_ARTIFACT_ID / GUARD_MODEL_PATH
```

Law cold-holdout remains **proof**, not the only training universe.

## Acceptance

1. `prismguard feedback export` CLI exists  
2. `--domain-pack` + `--normal-txt` + domain-aware eval (incl. `general`)  
3. Hub train pack + `scripts/train_prism_pi_hub.py`  
4. CI/hub gates: ONNX enforce allows core FAQ, blocks jailbreaks when artifact present  
5. Docs: shadow → export → train → gate → enforce  
6. Factory honors `PRISMGUARD_ARTIFACT_ID` / path (not silent law-only load)

## Hand back

`handoffs/handoffbackOnnxCustomer1.md` when Ready for QA.
