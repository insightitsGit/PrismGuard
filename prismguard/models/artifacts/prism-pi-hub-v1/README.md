# prism-pi-hub-v1

Hub/general ONNX artifact directory (opt-in).

**Not shipped by default.** Train locally:

```bash
python scripts/train_prism_pi_hub.py
# or smoke:
python scripts/train_prism_pi_hub.py --max-train-examples 4000
```

Publish `model.onnx` to a GitHub Release only after:

```bash
prismguard-model eval --domain general --artifact-path prismguard/models/artifacts/prism-pi-hub-v1 \
  --normal-txt benchmark/hub/benign_faq.txt
```

Runtime (after gates):

```bash
export PRISMGUARD_USE_ONNX=1
export PRISMGUARD_ARTIFACT_ID=prism-pi-hub-v1
# or: export PRISMGUARD_GUARD_MODEL_PATH=/path/to/prism-pi-hub-v1
```

Default production remains ONNX **off**; default artifact id when ONNX is on remains **prism-pi-v1** (law proof).
