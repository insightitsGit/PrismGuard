# Handoff Back — TestHandoff1 (4-stack + attacker law benchmark)

**Date:** 2026-07-07  
**Prerequisite:** `handoffs/handoffbackBug1.md` present — runtime triage exercised post-fix (`RuntimeChecker`, fusion to `block_threshold=0.78`).  
**Tests:** `pytest -q` → **56 passed** (includes `tests/test_law_benchmark.py`).

---

## Summary

Built the full **CPL / CRL / LNL / LPL / ATK** law-domain benchmark scaffold under `benchmark/law/`, with shared corpus, guards, measurement harness, Docker Compose, and Azure script stubs. **Local end-to-end measurement completed** via in-process FastAPI `TestClient` (all four stacks + legal attack overlay). **Docker Compose build was not validated** — Docker Desktop daemon was not running on the engineer machine (`npipe:////./pipe/dockerDesktopLinuxEngine` missing). **Azure was not provisioned** (per handoff: Director confirmation required).

---

## Part A — Legal task & corpus (T1, T2)

| Item | Files | Exit | Result |
|------|-------|------|--------|
| T1 KB + queries | `benchmark/law/data/kb_documents.yaml`, `queries.yaml`, `SAMPLE_DATA.md` | 15–20 cases, 3 categories | **PASS** — 17 docs (`contracts`, `case_law`, `compliance`), 18 legitimate queries with `must_cite` rubrics |
| T2 attack overlay | `benchmark/law/data/legal_attacks.yaml` | 15–20 legal-flavored attacks | **PASS** — 18 entries (incl. `benign_adjacent`), taxonomy-aligned categories |
| Shared loaders | `benchmark/law/shared/{kb,cases,rubric}.py` | KB retrievable, rubric scores answers | **PASS** — `tests/test_law_benchmark.py` |

Import path for overlay:

```bash
prismguard-seed import benchmark/law/data/legal_attacks.yaml --mode update
```

---

## Part B — Four stacks (T3–T6)

| Stack | Path | Guard | Framework pipeline | Exit |
|-------|------|-------|-------------------|------|
| **CPL** | `benchmark/law/cpl/app.py` | PrismGuard `RuntimeChecker` + authored seed + legal overlay | `run_chorus_pipeline` | **PASS** |
| **CRL** | `benchmark/law/crl/app.py` | Rebuff `detect_injection` | same Chorus pipeline | **PARTIAL** — unconfigured without `REBUFF_API_TOKEN` (or OpenAI+Pinecone SDK path) |
| **LNL** | `benchmark/law/lnl/app.py` | NeMo Guardrails (`lnl/config/`) | `run_langgraph_pipeline` | **PARTIAL** — `nemoguardrails` init fails without full LLM/rails setup; returns `nemo_unconfigured` gray |
| **LPL** | `benchmark/law/lpl/app.py` | PrismGuard | same LangGraph pipeline | **PASS** |

**Cross-check (benign task success):** All four stacks report **identical `task_success_rate: 0.8333`** (5/6 smoke queries) on the same KB/queries — guard/framework wiring does not skew benign baseline.

**Caveats (documented, not hidden):**
- Pipelines are **PrismGuard-local linear analogs** (`benchmark/law/shared/assistant.py`), not imports from `C:\code\ChorusGraph\benchmark\`. Same node order (guard → retrieve → answer) and shared `LawAssistant`, but not the full ChorusGraph graph runtime.
- **LangGraph bug fixed:** `LawGraphState` moved to module scope so `StateGraph` conditional routing works under LangGraph 0.2+.
- **CRL/LNL require real credentials** per handoff — no stubbed competitor decisions. Without keys, decisions are `gray` with `rebuff_unconfigured` / `nemo_unconfigured`.

**Docker:** `benchmark/law/Dockerfile.stack` (ARG `STACK`, `EXTRAS`), ports 8010–8013 in `docker-compose.yml`.

---

## Part C — ATK attacker (T7)

| Item | Files | Exit | Result |
|------|-------|------|--------|
| Attack runner | `benchmark/law/atk/attack_runner.py`, `atk/Dockerfile` | jsonl per stack + combined log | **PASS** (code); overlay path bug **fixed** (`parents[1]/data/legal_attacks.yaml`) |
| Compose wiring | `docker-compose.yml` `atk` service | depends on all four stacks | **PASS** (manifest) |
| Stretch: live paraphrase | — | LLM-generated variants | **NOT DONE** |

Replay sources: legal overlay + bundled seed profile (`authored` default, limit configurable) + benign law queries.

---

## Part D — Measurement (T8)

**Why not extend ChorusGraph `run_scenarios.py`:** That harness lives in the **ChorusGraph** repo (`C:\code\ChorusGraph\benchmark\`), not in PrismGuard. This repo had no `benchmark/run_scenarios.py`. Added law-specific tooling mirroring the same output shape:

| File | Role |
|------|------|
| `benchmark/law/compare_law.py` | Stack summaries + paired deltas → `comparison.json`, `COMPARISON_REPORT.md` |
| `benchmark/law/run_law_benchmark.py` | HTTP smoke (`--smoke`) or full attack replay against localhost:8010–8013 |

**Metrics tracked:** attack block rate (by category), false-positive rate on `benign_adjacent`, task success, guard LLM calls, latency mean/p95.

### Local run (real numbers)

Command: in-process 4-stack run (6 benign queries + 18 overlay attacks per stack). Artifacts: `benchmark/law/results/latest/{cpl,crl,lnl,lpl}.jsonl`, `comparison.json`, `COMPARISON_REPORT.md`.

| Stack | attack_block_rate | false_positive_rate | task_success_rate | guard_llm_calls_mean | latency_ms_mean |
|-------|-------------------|---------------------|-------------------|----------------------|-----------------|
| **CPL** | **1.0** | 0.0 | 0.8333 | 0 | 6.25 |
| **CRL** | **0.0** | 0.0 | 0.8333 | 0 | 0.02 |
| **LNL** | **0.0** | 0.0 | 0.8333 | 0 | 0.97 |
| **LPL** | **1.0** | 0.0 | 0.8333 | 0 | 7.06 |

CRL/LNL block rates are **0.0 because guards are unconfigured** (gray, not block) — not because Rebuff/NeMo allowed attacks.

### Paired comparisons (delta = right − left)

| Pair | Isolates | attack_block_rate_Δ | false_positive_rate_Δ | task_success_rate_Δ |
|------|----------|---------------------|----------------------|---------------------|
| **CPL vs CRL** | guard @ ChorusGraph | **−1.0** | 0.0 | 0.0 |
| **LPL vs LNL** | guard @ LangGraph | **−1.0** | 0.0 | 0.0 |
| **CPL vs LPL** | framework @ PrismGuard | **0.0** | 0.0 | 0.0 |

PrismGuard (CPL/LPL) blocks 100% of overlay attacks in this run with **zero guard LLM calls**. Framework choice (Chorus vs LangGraph) does not change outcomes when PrismGuard is held constant.

---

## Part E — Azure (T9)

| Item | Status |
|------|--------|
| `benchmark/law/azure/README.md` | **DONE** — documents `rg-prismguard-benchmark-law`, deploy/fetch/teardown flow |
| `deploy_and_run.ps1`, `fetch_results.ps1`, `teardown.ps1` | **STUB** — dry-run placeholders; **no `az` resources created** |
| Director cost confirmation | **NOT OBTAINED** |
| Teardown | N/A — nothing provisioned |

**Blocked for meaningful CRL/LNL Azure numbers:** `REBUFF_API_TOKEN` and NeMo LLM configuration must be supplied before cloud run.

---

## Package / deps

`pyproject.toml` updates:
- Optional extras: `benchmark-law`, `rebuff`, `nemo`
- Package discovery: `benchmark*` included alongside `prismguard*`

Install:

```bash
pip install -e ".[prism,seed,benchmark-law,rebuff,nemo]"
```

---

## Friction log

| Guardrail | Issue | Resolution |
|-----------|-------|------------|
| **Rebuff** | No `REBUFF_API_TOKEN` in dev env | Gate returns `gray` / `rebuff_unconfigured`; documented in compose env |
| **NeMo Guardrails** | Heavy dep + LLM models not configured in minimal `config.yml` | Gate returns `gray` / `nemo_unconfigured`; needs real rails + API keys for benchmark |
| **Docker** | Daemon not running locally | Compose manifests ready; smoke via `TestClient` + `run_law_benchmark.py --smoke` once Docker is up |
| **ChorusGraph import** | Separate repo | Used structural mirror, not direct import |

---

## How to validate locally (when Docker is available)

```bash
cd benchmark/law
docker compose up --build
# another shell:
python -m benchmark.law.run_law_benchmark --smoke --output-dir benchmark/law/results/latest
export REBUFF_API_TOKEN=...   # for meaningful CRL numbers
python -m benchmark.law.run_law_benchmark --output-dir benchmark/law/results/latest
```

---

## Not committed

Per standing rule — **no git commit** unless Director asks. Uncommitted work includes Bug1 fixes + full TestHandoff1 benchmark tree.

---

*TestHandoff1 handoff-back · local measurement complete · Docker/Azure pending environment/credentials · stretch paraphrase attacker not implemented.*
