# Optional starter ONNX defaults

## Product rule

1. **Agnostic path (preferred):** train on **your** labeled feedback/DB → `prism-pi-<slug>-v1` → `domain_pilot` + that artifact.  
2. **Starter defaults (optional):** law / finance / healthcare downloads if you have **no** DB yet.  
3. **Defaults do not guarantee accuracy** on your production traffic.

## Starters

| Domain | Artifact id | Status |
|--------|-------------|--------|
| law | `prism-pi-v1` | Published (GitHub Release `v0.1.2`) |
| finance | `prism-pi-finance-v1` | Local train ready; Release asset `v0.1.10` |
| healthcare | `prism-pi-healthcare-v1` | Train + Release asset `v0.1.10` |

```bash
prismguard-model download --list
prismguard-model download --domain finance
```

PyPI never ships `model.onnx` (~705 MB). Metadata ships in the wheel; weights download separately.

## Publish Release assets (maintainers)

After local `model.onnx` exists and gates are recorded:

```powershell
# Hash
Get-FileHash prismguard\models\artifacts\prism-pi-finance-v1\model.onnx -Algorithm SHA256
Get-FileHash prismguard\models\artifacts\prism-pi-healthcare-v1\model.onnx -Algorithm SHA256

# Copy for Release naming
Copy-Item prismguard\models\artifacts\prism-pi-finance-v1\model.onnx .\prism-pi-finance-v1-model.onnx
Copy-Item prismguard\models\artifacts\prism-pi-healthcare-v1\model.onnx .\prism-pi-healthcare-v1-model.onnx

# Requires Director approval to push / create Release
gh release create v0.1.10 `
  prism-pi-finance-v1-model.onnx `
  prism-pi-healthcare-v1-model.onnx `
  --title "v0.1.10 starter domain ONNX" `
  --notes "Optional finance + healthcare starter weights. No accuracy guarantee — train on your DB for production."
```

Update `sha256` in `prismguard/models/artifact_fetch.py` if the file changes before upload.

## Runtime

```python
create_checker_for_app("domain_pilot", domain="finance", use_onnx=True)
# PRISMGUARD_ARTIFACT_ID=prism-pi-finance-v1
```
