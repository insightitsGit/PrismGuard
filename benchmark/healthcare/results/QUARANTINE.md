# Quarantined — do not use for product decisions

**Date:** 2026-07-08  
**Status:** INVALID / MISLABELED

The run in `quarantine-2026-07-08-mislabeled/` is **not** a valid healthcare benchmark.

## Why it was quarantined

1. **Wrong domain content** — Used law benign queries and law normal scenarios with only a 4-prompt healthcare holdout and 3-prompt seeded overlay.
2. **No healthcare containers or KB** — Same law RAG pipeline; only `PRISMGUARD_DOMAIN=healthcare` triage/overlay changed.
3. **Misleading comparison** — Report implied healthcare product readiness; holdout n=4 and 11/35 false blocks on law normals.

## Authoritative law results

Use `benchmark/law/results/current/` for reproducibility checks.

Do **not** cite `healthcare_holdout` numbers from the quarantined run in docs or pitch materials.

## To build healthcare for real (future)

- Healthcare-specific KB and query set
- Healthcare normal scenarios (HIPAA/PHI benign stress test)
- Holdout set ≥14 prompts, overlap-verified
- Dedicated benchmark harness path (not law traffic + domain flag)
