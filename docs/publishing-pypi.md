# PyPI publish checklist (maintainers)

## Pre-flight

1. `python scripts/adversarial_self_check.py` — exit 0
2. `pytest tests/` — green
3. `prismguard eval self-check` — VERIFY_OK: yes (with guard-model extra)
4. Version bumped in `pyproject.toml`
5. README links and install snippet current
6. PyPI name `prismguard` available (or use TestPyPI first)

## Build

```bash
pip install build twine
python -m build
twine check dist/*
```

## Upload (requires PyPI token — do not commit)

```bash
twine upload dist/*
```

## What ships in the wheel

- `prismguard` package + bundled seed + ONNX artifacts (`package-data` in pyproject)
- **Not** included: `benchmark/` harness (repo-only; run from source checkout)
- CLI: `prismguard`, `prismguard-seed`, `prismguard-model`, `prismguard-serve`
- Extras: `guard-model`, `serve`, `pgvector`, `enterprise` (cryptography for signed licenses)

## Post-publish

- Tag release on GitHub
- Update InsightitsAIAgent catalog PyPI URL when live
- Run `handoffs/handoffLandingPage.md` Part B landing page tasks

## Customer install (document in README)

```bash
pip install "prismguard[guard-model]"
prismguard init --domain law
prismguard eval self-check
```

Business HTTP:

```bash
pip install "prismguard[serve,enterprise,guard-model]"
export PRISMGUARD_LICENSE_FILE=/path/to/license.json
export PRISMGUARD_DEV_UNRESTRICTED=0
prismguard-serve
```
