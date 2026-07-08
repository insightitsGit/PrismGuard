# Law benchmark results layout

## Authoritative (use these)

| Path | Description |
|------|-------------|
| **`verified/`** | First run with fixed client latency instrumentation (`request_latency_ms`). **Cite this for product decisions.** |
| `repro-comparison.json` | Back-to-back repro: run-a vs run-b decision stability |
| `verified-vs-repro-b.json` | Verified vs repro-run-b (same harness) |

## Reproducibility check (2026-07-08)

Two back-to-back law runs (`repro-run-a`, `repro-run-b`), same code path, bundled-limit 100:

- **Decisions: 100% stable** — 0 decision mismatches, 0 gate mismatches across all 4 stacks (189 requests each).
- **Latency: run-to-run variance is high** (CPL mean abs delta ~461–679 ms between runs) due to cold model load, CPU contention, and fresh gate init per stack — **not** decision flapping.

Conclusion: **Non-determinism is in timing, not in block/allow outcomes.** Earlier Docker vs local disagreements were environment/config mismatch, not random decisions.

## Deprecated / do not cite

| Path | Why |
|------|-----|
| `latest/` (pre-2026-07-08) | Used pipeline-internal `latency_ms` as headline; mixed with Docker `atk_combined.jsonl` |
| `repro-run-a/` | Pre-harness-fix latency fields (decisions still valid) |

## Harness latency fields (post-fix)

| Field | Meaning |
|-------|---------|
| `request_latency_ms` | **Primary** — HTTP client wall clock (TestClient or atk runner) |
| `guard_latency_ms` | Guard-only (`guard.check()`) |
| `pipeline_latency_ms` | In-process runner (guard + retrieval) |
| `latency_ms` | Alias for `request_latency_ms` in jsonl output |

Run: `python -m benchmark.law.run_local_benchmark --output-dir benchmark/law/results/verified`

Compare runs: `python scripts/compare_repro_runs.py run-a run-b`
