# PyPI publish checklist (maintainers)

## Pre-flight (run from repo root)

```powershell
cd c:\code\PrismGaurd
pip install -e ".[guard-model,serve,enterprise,dev]"
python -m pytest tests/ -q
python scripts/adversarial_self_check.py
prismguard eval self-check
prismguard check "Summarize indemnity caps in a vendor MSA."
```

All must pass before upload.

## Publish ONNX model asset (required before PyPI)

The ONNX file (~705 MB) **cannot** ship in the PyPI wheel (100 MB limit). Upload it as a GitHub Release asset first:

```powershell
# From repo root — asset name must match artifact_fetch.py URL
Copy-Item prismguard/models/artifacts/prism-pi-v1/model.onnx dist/prism-pi-v1-model.onnx
gh release create v0.1.2 dist/prism-pi-v1-model.onnx --title "v0.1.2" --notes "ONNX model for prism-pi-v1"
```

Verify download URL works:

```powershell
Invoke-WebRequest -Method Head `
  "https://github.com/insightitsGit/PrismGaurd/releases/download/v0.1.2/prism-pi-v1-model.onnx"
```

## Build

```powershell
pip install build twine
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
python -m build
twine check dist/*
```

## Verify wheel size and contents

```powershell
Get-ChildItem dist | Format-Table Name, @{N='MB';E={[math]::Round($_.Length/1MB,2)}}

python -c "
import zipfile, glob
w = glob.glob('dist/*.whl')[0]
z = zipfile.ZipFile(w)
names = z.namelist()
onnx = [n for n in names if n.endswith('model.onnx')]
print('wheel MB', round(sum(i.file_size for i in z.infolist())/1024/1024, 2))
print('model.onnx in wheel', len(onnx))
print('cli_check', any('cli_check' in n for n in names))
print('benchmark', sum(1 for n in names if n.startswith('benchmark')))
print('prism-pi-v1 metadata', sum(1 for n in names if 'prism-pi-v1' in n))
print('prism-pi-v2', sum(1 for n in names if 'prism-pi-v2' in n))
"
```

Expected: wheel **under 100 MB**, `model.onnx in wheel 0`, `cli_check True`, `benchmark 0`, `prism-pi-v1 metadata > 0`, `prism-pi-v2 0`.

## Upload (requires PyPI token — do not commit)

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-YOUR_TOKEN_HERE"
twine upload dist/prismguard-0.1.2-py3-none-any.whl
twine upload dist/prismguard-0.1.2.tar.gz
```

Upload the **wheel first**; it is smaller and validates packaging.

## What ships in 0.1.2

| Item | Included |
|------|----------|
| `prismguard check` CLI | yes |
| `prismguard eval self-check` | yes |
| Signed license validator (`enterprise` extra) | yes |
| HTTP serve + `/metrics` (`serve` extra) | yes |
| ONNX metadata (tokenizer, model card, calibration) | yes (in wheel) |
| ONNX `model.onnx` weights | **no** — `prismguard-model download` or auto-fetch on first use |
| `prism-pi-v2` artifacts | **no** (repo dev only) |
| `benchmark/` harness | **no** |
| README hero image | GitHub only until raw URL added post-push |

## Post-publish (second commit)

1. Confirm package live: `pip install "prismguard[guard-model]" && prismguard-model download`
2. Update README hero `img src` to raw GitHub URL:
   `https://raw.githubusercontent.com/insightitsGit/PrismGaurd/master/docs/assets/hero.png`
3. Update PyPI badge / InsightitsAIAgent catalog with PyPI URL
4. Tag: `git tag v0.1.2 && git push origin v0.1.2`

## Customer install

```bash
pip install "prismguard[guard-model]"
prismguard-model download
prismguard init --domain law
prismguard check "your prompt"
prismguard eval self-check
```

Override model URL (air-gapped / mirror):

```bash
export PRISMGUARD_MODEL_DOWNLOAD_URL="https://your-mirror/prism-pi-v1-model.onnx"
prismguard-model download
```
