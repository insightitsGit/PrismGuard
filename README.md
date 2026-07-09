# PrismGuard

Self-hosted, **audit-traceable** prompt-injection firewall for LLM applications. Every decision returns a `resolution_gate` (e.g. `structural`, `guard_model_first`, `llm_judge`) suitable for compliance logs — not an opaque score.

Apache-2.0 open core · optional Team/Business licenses · law domain verified · PyPI `0.1.1` (alpha).

---

## Why PrismGuard

| | PrismGuard | Typical scanner (e.g. LLM Guard) |
|---|------------|----------------------------------|
| **Audit trail** | `resolution_gate` + `decision_source` on every check | Often classifier label only |
| **Deployment** | Self-hosted ONNX + rules; traffic stays on your infra | Often hosted API or bundled model |
| **Cost path** | ONNX ~200ms; LLM Judge &lt;8% escalation on law bench | Classifier per request; varies by config |
| **Positioning** | **Cheaper + audited** for compliance workflows | General-purpose guard library |

We optimize for **explainability and predictable cost** on legal/compliance workloads — not “wins every paraphrase on every domain.”

---

## Law benchmark vs LLM Guard (authoritative)

**Source:** [`benchmark/law/results/current/`](benchmark/law/results/current/) — 4-stack harness, same traffic, paired guardrails.  
**Gate:** `python scripts/adversarial_self_check.py` → SHIP_READY (2026-07-09).

### Cold holdout — attack block rate (`legal_overlay_holdout`, n=14)

| Stack | Guard | Block rate |
|-------|-------|------------|
| **CPL** | PrismGuard @ ChorusGraph | **14/14 (100%)** |
| CGL | LLM Guard @ ChorusGraph | 9/14 (64.3%) |
| **LPL** | PrismGuard @ LangGraph | **14/14 (100%)** |
| LGL | LLM Guard @ LangGraph | 9/14 (64.3%) |

PrismGuard blocks **+35.7 pp** more cold holdout attacks than LLM Guard on the same framework (CPL vs CGL, LPL vs LGL).

### Cold holdout — false positives (`normal_scenario_holdout`, n=25 in HTTP bench)

| Stack | Allow rate |
|-------|------------|
| CPL / CGL / LGL / LPL | **25/25 (100%)** |

Expanded **43-prompt** normal holdout (phrasing-diverse) is validated in-process: **43/43 allow** (`adversarial_self_check.py`, not merged into seed).

### Latency — mean `request_latency_ms` (full law traffic, n=214)

| Stack | Guard | Mean latency |
|-------|-------|--------------|
| **CPL** | PrismGuard | **211 ms** |
| CGL | LLM Guard | 353 ms |
| **LPL** | PrismGuard | **254 ms** |
| LGL | LLM Guard | 375 ms |

PrismGuard is **faster** than LLM Guard on both framework pairings in this run, while blocking more cold holdout attacks.

### Escalation (CPL / LPL only)

| Metric | CPL |
|--------|-----|
| Guard-model escalation | 22.4% |
| LLM Judge escalation | 7.0% |

Judge calls remain a small fraction of traffic; most decisions resolve via rules + ONNX.

### What we do **not** claim

- Healthcare / finance domains (overlays exist; no valid benchmark)
- “Beats LLM Guard on every attack category” (seeded `bundled_full` mix: CPL 84.4% vs CGL 75.3%)
- Holdout YAML is a runtime patch for customers (updates = pip + seed + model — see [`docs/user-updates.md`](docs/user-updates.md))

Full tables: [`benchmark/law/results/current/COMPARISON_REPORT.md`](benchmark/law/results/current/COMPARISON_REPORT.md)

---

## Quick start

```bash
pip install "prismguard[guard-model]"
prismguard init --domain law
prismguard doctor
prismguard eval self-check
```

Library usage:

```python
from prismguard.runtime.check import RuntimeChecker
from prismguard.seed import import_bundled_seed, load_bundled_seed
from prismguard.storage import create_storage

storage = create_storage("memory")
parsed = load_bundled_seed(profile="authored")
import_bundled_seed(storage, profile="authored")
checker = RuntimeChecker.from_storage(storage, parsed)

result = checker.check("Summarize indemnity caps in a vendor MSA.")
print(result.decision, result.resolution_gate)
```

HTTP sidecar (Business license):

```bash
pip install "prismguard[serve,enterprise,guard-model]"
export PRISMGUARD_LICENSE_FILE=/path/to/license.json
prismguard-serve   # POST /v1/check, GET /metrics
```

ChorusGraph node: `prismguard.integrations.chorusgraph.make_guard_handler()` — see [`docs/integration-guide.md`](docs/integration-guide.md).

---

## Architecture (short)

```
Input → normalize → Tier-1 rules → structural analysis → [optional ANN/fusion]
      → ONNX Guard Model (prism-pi-v1) → [rare LLM Judge] → allow | block
```

- **Owned classifier:** ONNX `prism-pi-v1` ships in the wheel (`prismguard[guard-model]`).
- **Disagreement escalation:** when structural says allow and classifier disagrees, escalate to Judge — no blind veto on benign legal phrasing.
- **Domain packs:** `prismguard init --domain law` (law verified; healthcare/finance frozen).
- **Storage:** `memory` default (OSS). pgvector/Chroma/Pinecone/Weaviate require Team license.

Details: [`docs/prismguard-design.md`](docs/prismguard-design.md)

---

## Install extras

| Extra | Purpose |
|-------|---------|
| `guard-model` | ONNX runtime + `prism-pi-v1` artifacts |
| `serve` | `prismguard-serve` FastAPI |
| `enterprise` | Signed license verification (`cryptography`) |
| `pgvector` / `chroma` / … | Persistent vector backends (Team) |
| `seed` | Import bundled corpus (`pyarrow`) |
| `benchmark-law` | Reproduce law 4-stack harness (dev checkout) |

---

## Product tiers (summary)

| SKU | Price (pre-validation) | Highlights |
|-----|------------------------|------------|
| `prismguard` | $0 | Library, ONNX, law pack, ChorusGraph guard node |
| `prismguard-team` | ~$199/mo | pgvector persistence, feedback exports |
| `prismguard-business` | ~$699/mo | HTTP API, tenant lexicon, `/metrics` |
| `prismguard-pilot` | ~$25k | Enterprise pilot, custom lexicon, SLA |

See [`docs/enterprise-product-model.md`](docs/enterprise-product-model.md).

---

## Reproduce benchmarks

From a source checkout (benchmark harness is **not** in the PyPI wheel):

```bash
pip install -e ".[benchmark-law,guard-model,llm-guard]"
python -m benchmark.law.run_local_benchmark --output-dir benchmark/law/results/current
python scripts/adversarial_self_check.py
```

---

## Documentation

| Doc | Topic |
|-----|-------|
| [`docs/prismguard-design.md`](docs/prismguard-design.md) | Full architecture |
| [`docs/law-pilot-readiness.md`](docs/law-pilot-readiness.md) | Ship gates, claim discipline |
| [`docs/user-updates.md`](docs/user-updates.md) | How customers get improvements |
| [`docs/integration-guide.md`](docs/integration-guide.md) | Library, HTTP, ChorusGraph |
| [`docs/publishing-pypi.md`](docs/publishing-pypi.md) | Maintainer publish checklist |
| [`benchmark/law/results/README.md`](benchmark/law/results/README.md) | Results layout |

---

## License

Apache-2.0. Team/Business features require a signed offline license (`PRISMGUARD_LICENSE_FILE`). Dev override: `PRISMGUARD_DEV_UNRESTRICTED=1` (local only).
