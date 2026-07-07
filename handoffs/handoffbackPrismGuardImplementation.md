# PrismGuard Implementation Handoff Back

**Date:** 2026-07-07 (updated)  
**Repo:** `c:\code\PrismGaurd`  
**Branch state:** Uncommitted work beyond initial push (`0f78440`)  
**Tests:** `pytest -q` → **37 passed**

---

## Executive summary

PrismGuard runs a **post-seed prismRAG taxonomy pipeline** that wires categories/rules into `prismrag-patch`, embeds dual vectors (768-d semantic + 256-d category-grounded via `PrismRAGPatch.remap_vector`), and exposes a **deterministic runtime check** (no Guard Model, no LLM Judge) designed to resolve the majority of traffic before any LLM escalation.

**Taxonomy runs automatically after every successful seed import** (`update` and `replace`, any scope). No separate ingest step required.

**CLI:**

```bash
pip install -e ".[dev]"          # includes prismrag-patch via [prism]
prismguard-seed import --bundled --profile authored
prismguard-seed import --bundled --profile full    # ~22k rows
prismguard-seed import --bundled --skip-taxonomy   # opt out
prismguard-seed import --bundled --force-embed     # re-embed all rows
pytest -q
```

---

## Extras — auto-taxonomy integration (latest)

These behaviors were added after the initial handoff-back and are now documented in `handoffPrismGuardImplementation.md` under **Extras — auto-taxonomy after import**.

### Import → taxonomy flow

```
import_seeds() / import_bundled_seed()
  └─ SeedImporter.import_parsed()
       ├─ validate
       ├─ write categories, rules, entries  (update | replace)
       ├─ append import_log
       └─ run_post_seed_pipeline()         ← automatic unless skip_taxonomy or dry_run
            ├─ build_mapping_after_import(storage, parsed)
            ├─ ingest_seed_vectors()       ← dual 768-d + 256-d
            └─ coverage + LLM reduction report
```

### API surface

| Symbol | Change |
|--------|--------|
| `ImportReport.taxonomy` | `PostSeedReport \| None` — populated after every real import |
| `ImportOptions.skip_taxonomy` | Default `False` — set `True` to skip post-import embed |
| `ImportOptions.force_embed` | Re-embed all rows even if vectors exist |
| `import_seeds(..., skip_taxonomy=, force_embed=)` | Public kwargs on import function |
| `import_bundled_seed(..., skip_taxonomy=, force_embed=)` | Same on bundled path |
| `build_mapping_after_import(storage, parsed)` | Mapping from **storage** rules/categories + parsed bridges |

### Behavioral details

- **`update` mode:** new/changed entries get embedded; unchanged entries skip embed (idempotent).
- **`replace` mode:** truncated or replaced entries have empty vectors → re-embedded on taxonomy pass.
- **Content change:** if `chunk_text` changes, embeddings cleared before upsert → taxonomy re-embeds that row.
- **`dry_run`:** no storage writes, no taxonomy.
- **CLI:** `--skip-taxonomy` opt-out; `--force-embed` force re-embed. Removed opt-in `--ingest-taxonomy` (taxonomy is default).

### prismRAG API (verified `prismrag-patch==0.2.1`)

| Handoff assumed | Actual | Impact |
|-----------------|--------|--------|
| `from prismrag_patch.mapping import Mapping, remap_vector` | `PrismRAGPatch` + `RulesStrategy` + `MappingConfig` | Rewired `taxonomy/mapping.py` |
| `Mapping.assign_category(text)` substring match | `RulesStrategy.infer_category_from_text` — whole-token only | `_substring_rules` fallback added |
| `remap_vector(vector, slug, mapping, alpha)` | `PrismRAGPatch.remap_vector(vector, text)` | 768-d → 256-d via `project_sem_to_personal` |
| License key required | OSS 0.2.1 ignores license key | No gate in dev/CI |
| `prismcortex` graph ingest | Not wired | Graph BFS (T9) still blocked |

Local `PrismRagLib` v1.0.0 layout (`mapping.py` module) **differs** from PyPI 0.2.1. Implementation targets PyPI.

---

## Task status

### Part A — Scaffold & config ✅

| Task | Status | Files | Exit criteria |
|------|--------|-------|---------------|
| T1 Package scaffold | **PASS** | `pyproject.toml`, `prismguard/` | `pip install -e ".[dev]"` works |
| T3 Config loader | **PASS** | `prismguard/config/loader.py`, `triage.yaml` | `load_triage_config()` tested |

### Part B — Seed import ✅

| Task | Status | Files | Exit criteria |
|------|--------|-------|---------------|
| T3 Parsers | **PASS** | `prismguard/seed/formats/*` | YAML, JSONL, CSV, MD, S-Labs, yanismiraoui, neuralchemy parquet |
| T4 Importer | **PASS** | `prismguard/seed/importer.py` | Idempotent re-import; **auto-taxonomy after write** |
| T5 Bundled corpus | **PASS** | `prismguard/seed/corpus/` | Ships via `package-data` |
| Multi-source merge | **PASS** | `merge.py`, `validate.py` | Full profile ~22,410 deduped entries |

**T5 import counts (verified):**

| Profile | Entries parsed | Categories | Authored import `inserted` |
|---------|----------------|------------|----------------------------|
| `authored` | 40 examples + 12 categories + Tier-1 rules | 12 | **40** |
| `full` | **22,410** entries | 12 | `prismguard-seed import --bundled --profile full` |

### Part C — Taxonomy wiring (prismRAG) ✅

| Task | Status | Files | Exit criteria |
|------|--------|-------|---------------|
| T6 Mapping wire | **PASS** | `taxonomy/mapping.py` | Tier-1 regex match on `direct_instruction_override` |
| T7 Dual-vector ingest | **PASS** | `taxonomy/ingest.py`, `embedder.py`, `pipeline.py` | All authored entries embedded; idempotent skip on re-run |
| Auto post-import hook | **PASS** | `seed/importer.py`, `seed/bundled.py`, `cli.py` | Taxonomy on every `update`/`replace`; `--skip-taxonomy` opt-out |
| Coverage report | **PASS** | `taxonomy/report.py` | Per-category seed/stored/embedded counts |

**Authored import + taxonomy (default CLI, no extra flags):**

```
inserted: 40
taxonomy.ingest.embedded: 40
categories: 12
unembedded: 0
embedder: HashEmbedder (offline default)
```

Second `update` run: `inserted=0`, `taxonomy.ingest.embedded=0`, `skipped_already_embedded=40`.

### Part D — Runtime check (partial) 🟡

| Task | Status | Files | Notes |
|------|--------|-------|-------|
| T8 Normalize | **PARTIAL** | `runtime/normalize.py` | NFKC, zero-width, base64/hex; rot13 removed (false positives) |
| T8a Structural | **NOT STARTED** | — | — |
| T8b Session | **NOT STARTED** | — | `payload_splitting` needs T8b |
| T9 Full check | **PARTIAL** | `runtime/check.py`, `fusion.py` | Tier-1 → dual ANN → fusion; no cache/graph/session |
| T9c Calibration | **NOT STARTED** | — | — |
| T10 Benchmark | **NOT STARTED** | — | Hard gate before Guard Model |

### Part J — Pluggable storage 🟡

| Backend | Status |
|---------|--------|
| `memory` | **FULL** |
| `pgvector`, `chroma`, `pinecone`, `weaviate` | Stubs |

---

## LLM call reduction

| Gate | Est. traffic % | Status |
|------|----------------|--------|
| Tier-1 rules | 12% | Active |
| Structural heuristics | 8% | Not built |
| Benign fast-path | 35% | Active |
| Corpus ANN + fusion | 38% | Active |
| Guard model | 5% | Not built |
| **LLM judge** | **~2%** | Not built |

**Currently active:** tier-1, corpus ANN, benign fast-path, fusion — **0 LLM calls** on check path.

---

## Files added / changed

```
prismguard/seed/importer.py   # auto-taxonomy, ImportReport.taxonomy, embed clear on content change
prismguard/seed/bundled.py    # skip_taxonomy, force_embed passthrough
prismguard/taxonomy/
  mapping.py                  # build_mapping_after_import()
  ingest.py, embedder.py, pipeline.py, report.py
prismguard/runtime/           # normalize, fusion, check
prismguard/cli.py             # --skip-taxonomy, --force-embed (taxonomy default-on)
pyproject.toml                # dev extra includes [prism]
tests/test_seed_import.py     # auto-taxonomy on update/replace, opt-out
tests/test_taxonomy.py
tests/test_bundled_seed.py
handoffs/handoffPrismGuardImplementation.md  # Extras section added
```

---

## What's blocked

1. Graph BFS + multi-community routing (T9)
2. Output-side scan for `data_exfiltration_via_output`
3. Session-level `payload_splitting` (T8b)
4. pgvector production backend (T2)
5. T10 benchmark before Guard Model / LLM Judge
6. Production embedder (sentence-transformers / PrismLib)
7. Variant expansion on ingest (T7 I.10 — `variant_expansion.py` not built)
8. Git commit/push — not done

---

## Recommended next steps

1. `prismguard-seed import --bundled --profile full` on target storage (pgvector when T2 lands).
2. T8a structural + T8b session.
3. Decision cache (I.8).
4. T10 benchmark + T9c calibration.
5. Part E only after T10 gate.

---

## Test evidence

```
pytest -q
37 passed in ~2s
```

Coverage: auto-taxonomy on update/replace, dry-run skip, `--skip-taxonomy` opt-out, bundled idempotent embed, runtime block/allow, Tier-1 rule match.

---

*Handoff back per `handoffPrismGuardImplementation.md` return format. No commits made.*
