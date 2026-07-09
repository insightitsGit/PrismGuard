# Law benchmark results

## Authoritative run (cite for README / landing / sales)

| Path | Description |
|------|-------------|
| **`current/`** | Latest verified 4-stack law benchmark after holdout-FP fixes and `disagreement_escalation`. **Only directory to cite externally.** |

Artifacts: `comparison.json`, `COMPARISON_REPORT.md`, `{cpl,cgl,lgl,lpl}.jsonl`.

Re-run:

```powershell
python -m benchmark.law.run_local_benchmark --output-dir benchmark/law/results/current
python scripts/adversarial_self_check.py   # required before claiming a win
```

## Stacks (same traffic, different guard + framework)

| ID | Framework | Guard | Compares |
|----|-----------|-------|----------|
| **CPL** | ChorusGraph (in-process) | **PrismGuard** | vs CGL |
| **CGL** | ChorusGraph | **LLM Guard** | baseline |
| **LPL** | LangGraph (in-process) | **PrismGuard** | vs LGL |
| **LGL** | LangGraph | **LLM Guard** | baseline |

## Eval sets in `current/` run

| Set | Rows | Use |
|-----|------|-----|
| `legal_overlay_holdout` | 14 attacks | Cold attack block rate (external claims) |
| `normal_scenario_holdout` | 25 normals | Cold FP eval in this HTTP benchmark |
| `normal_scenario_seeded` | 35 normals | Dev/tuning only — do not cite as cold eval |
| `legal_overlay_seeded` / `bundled_full` | attacks | Dev stress — not cold eval |

**Expanded normal holdout (43 prompts)** is validated separately by `scripts/adversarial_self_check.py` (in-process, not the HTTP 4-stack harness). As of 2026-07-09: **43/43 allow**.

## Deprecated (removed)

Older directories (`verified/`, `latest/`, `post-optimization/`, `docker-verified/`, `repro-run-*`, `post-holdout-fix/`) were superseded by `current/` and deleted to avoid citing stale numbers.

## Harness fields

| Field | Meaning |
|-------|---------|
| `request_latency_ms` | **Primary** — HTTP client wall clock |
| `guard_latency_ms` | Guard-only (`check()`) |
| `pipeline_latency_ms` | In-process runner (guard + retrieval stub) |

## Other folders (not product claims)

| Path | Purpose |
|------|---------|
| `corpus_scale/` | Corpus ablation experiments |
| `repro-comparison.json` | Historical repro notes |
