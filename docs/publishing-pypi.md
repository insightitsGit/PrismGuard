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

## Publish ONNX model asset (required once; reuse across patch releases)

The ONNX file (~705 MB) **cannot** ship in the PyPI wheel (100 MB limit). It is hosted as a GitHub Release asset. Current download URL (used by `artifact_fetch.py`):

```text
https://github.com/insightitsGit/PrismGuard/releases/download/v0.1.2/prism-pi-v1-model.onnx
```

Patch releases (e.g. `0.1.4`) that do not change model weights **reuse** that asset — no new ONNX upload required.

If you ever ship new weights, create a new GitHub release asset and update the default URL in `prismguard/models/artifact_fetch.py`.

Verify download URL works:

```powershell
Invoke-WebRequest -Method Head `
  "https://github.com/insightitsGit/PrismGuard/releases/download/v0.1.2/prism-pi-v1-model.onnx"
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
twine upload dist/prismguard-0.1.4-py3-none-any.whl
twine upload dist/prismguard-0.1.4.tar.gz
```

Upload the **wheel first**; it is smaller and validates packaging.

## What ships in 0.1.4

| Item | Included |
|------|----------|
| `prismguard check` CLI | yes |
| `prismguard eval self-check` | yes |
| Base install (zero extras) CLI entry points | yes — Buglib1 fix |
| `POST /v1/scan-output` `resolution_gate` | yes — QA-001 fix |
| Signed license validator (`enterprise` extra) | yes |
| HTTP serve + `/metrics` (`serve` extra) | yes |
| ONNX metadata (tokenizer, model card, calibration) | yes (in wheel) |
| ONNX `model.onnx` weights | **no** — `prismguard-model download` or auto-fetch on first use |
| `prism-pi-v2` artifacts | **no** (repo dev only) |
| `benchmark/` harness | **no** |

## Post-publish

1. Confirm package live: `pip install "prismguard==0.1.4"` then `prismguard --help` and `prismguard doctor` (no numpy crash).
2. Confirm with extras: `pip install "prismguard[guard-model]==0.1.4" && prismguard-model download`
3. Yank broken `0.1.3` on PyPI (Director go-ahead): reason e.g. `Base install crashes without numpy; use 0.1.4`
4. Tag: `git tag v0.1.4 && git push origin v0.1.4`

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
