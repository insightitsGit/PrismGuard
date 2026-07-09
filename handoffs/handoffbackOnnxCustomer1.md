# Handback — OnnxCustomer1

**Handoff:** HO-OnnxCustomer1  
**Status:** Ready for QA  
**Date:** 2026-07-09  

## Delivered

1. **`prismguard feedback export`** — opt-in CLI; default exports approved blocks only  
2. **`--domain-pack`** — opt-in; default train = bundled seed only; `--law-pack` alias  
3. **Domain-aware eval** — `general` holdout + `--normal-txt`; law normals remain default for `--domain law`  
4. **`prismguard-model corpus-plan`** — dry-run plan  
5. **Hub train pack** — `benchmark/hub/training/` + `scripts/train_prism_pi_hub.py`  
6. **Factory** — `PRISMGUARD_ARTIFACT_ID` / `PRISMGUARD_GUARD_MODEL_PATH`; feedback persist opt-in  
7. **Docs** — shadow → export → train → gate → enforce; defaults called out  

## Defaults (unchanged safety)

- Runtime: ONNX **off** unless `PRISMGUARD_USE_ONNX=1`  
- When ONNX on without override: **`prism-pi-v1`** (law proof)  
- Hub artifact: train via script; enforce only after gates + explicit `ARTIFACT_ID`/`PATH`  

## Train hub artifact (maintainer)

```bash
pip install -e ".[train,seed,guard-model]"
python scripts/train_prism_pi_hub.py
# Publish Release asset only if eval normal_allow ≈ 100% and holdout_block ≥ 95%
```

## QA checklist

- [ ] `prismguard feedback export -h` works  
- [ ] `prismguard-model corpus-plan` with no `--domain-pack` shows `domain_pack: null`  
- [ ] `prismguard-model corpus-plan --domain-pack general` includes hub files  
- [ ] Rules-only hub FAQ tests still green  
- [ ] Without hub `model.onnx`, ONNX hub gate test skips (opt-in)  
- [ ] Docs state seed ≠ weights; ONNX enforce is opt-in  

## Note on publishing ONNX

Full GPU train of `prism-pi-hub-v1` is a maintainer step. This cut unlocks the path and gates; do not force ONNX on Azure until the hub artifact exists and CI gate is green.
