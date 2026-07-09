# Contributing to PrismGuard

Thanks for helping improve PrismGuard — a self-hosted, audit-traceable prompt-injection firewall.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- Report bugs and request features via [GitHub Issues](https://github.com/insightitsGit/PrismGuard/issues)
- Improve docs under `docs/`
- Fix bugs or add tests under `tests/`
- Propose carefully scoped runtime improvements (prefer small PRs)

## Development setup

Requires **Python 3.11+**.

```bash
git clone https://github.com/insightitsGit/PrismGuard.git
cd PrismGuard
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install -e ".[guard-model,serve,enterprise,dev]"
```

Optional ONNX weights (not in the PyPI wheel):

```bash
prismguard-model download
```

Verify:

```bash
prismguard doctor
pytest tests/ -q
```

## Pull request process

1. Open an issue first for large changes (API, licensing, detection behavior).
2. Create a branch from `main`.
3. Keep PRs focused — one concern per PR when possible.
4. Add or update tests for behavior changes.
5. Run locally before pushing:

   ```bash
   pytest tests/ -q
   ```

6. Fill out the PR template.
7. Do not commit secrets, license private keys, large ONNX binaries, or local virtualenvs (`.venv*`).

### Claim discipline

Do **not** add marketing claims about healthcare/finance readiness or “beats all scanners” unless backed by checked-in benchmark evidence under `benchmark/law/results/current/`.

## Code style

- Match existing module patterns and typing style.
- Prefer lazy imports for optional extras (`[guard-model]`, `[serve]`, `[enterprise]`, etc.) so the base package stays installable without ML stacks.
- Public HTTP / CLI contracts should stay backward compatible unless the PR clearly documents a break.

## Security

Do **not** open public issues for undisclosed vulnerabilities. See [SECURITY.md](SECURITY.md).

## License

Contributions are accepted under the [Apache License 2.0](LICENSE). Team / Business product features may remain license-gated; that does not change the OSS license for contributed code in this repository.

## Questions

- Product / enterprise: see [docs/enterprise-product-model.md](docs/enterprise-product-model.md)
- Integration: see [docs/integration-guide.md](docs/integration-guide.md)
- Contact: info@insightits.com
