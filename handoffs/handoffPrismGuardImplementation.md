# Handoff PrismGuardImplementation — build PrismGuard end to end, 0 → 100

**Director:** Amin · **Architect:** Claude · **Engineer:** (receiving agent)
**Refs:** [`docs/prismguard-design.md`](../docs/prismguard-design.md) (full architecture, taxonomy, target metrics, open risks — read it first, this handoff does not repeat it) · depends on installed packages `prismlib`, `prismrag-patch`, `prismcortex`
**Date issued:** 2026-07-06 · **Revision:** 2026-07-06 — LLM-minimization enhancements integrated (see Part I)

---

## 0. Why

`docs/prismguard-design.md` is the agreed design: a self-hosted, audit-traceable prompt-injection firewall that composes prismRAG (taxonomy graph retrieval), prismCortex (pgvector seed store), and prismLib (runtime cache), with a two-tier escalation (Guard Model → LLM Judge) built specifically to keep LLM calls to well under 1% of traffic. That document is conceptual. This handoff turns it into buildable tasks, in order, with exit criteria.

**One requirement is called out specifically by the Director and gets its own dedicated part (Part B) before anything else gets wired up:** the seed corpus (the "big seed" — `docs/prismguard-design.md` Part 5) must be **importable** through a real tool, not just pasted into the database by hand. That importer must support:
- **Multiple sources in one run** — mix files, directories, and manifest lists (`@sources.txt`); merge into one corpus before write.
- **Update mode** — upsert new/changed entries into the existing corpus without touching what's already there.
- **Replace mode** — wipe and reload (whole corpus, or scoped to one category), for when a batch of seed data is wrong and needs to be superseded, not merged.
- **Multiple file formats** — because taxonomy/rules get hand-authored (YAML/JSON) while bulk seed examples often arrive as spreadsheets (CSV) or exports from other systems (JSONL), and the design doc's own Part 5 is written in Markdown and should be loadable as-is.

Build the importer early (Part B) — the feedback loop in Part F reuses it verbatim, so it only gets built once.

**LLM-minimization mandate (added in this revision):** The original design doc pipeline is correct but asymmetric — it escalates blocks well but leaves the gray zone too large. This handoff adds deterministic layers that resolve more traffic *before* Guard Model and LLM Judge, and compounds reductions over time via caching and distillation. Every new layer must be measured in T10/T11/T12 benchmarks; none of the percentage targets below are assumed true until measured.

**Standing rules:**
- Verify the actual installed API surface of `prismlib`, `prismrag-patch`, and `prismcortex` before writing code against assumed method/class names — check the installed package source (`pip show -f`, then read the module) rather than trusting the family-reference doc's prose. Flag any deviation between what the doc claims and what the library actually exposes.
- No mocked seed data for anything user-facing — use the real Part 5 seed corpus as the first real import (T5), not a synthetic fixture.
- Thresholds, benchmark numbers, and call-volume percentages must be **measured** against a real eval run, never declared from the design doc's target table (those are hypotheses, labeled as such in the design doc).
- Every database mutation (import, feedback append) is logged — source, mode, counts, timestamp. This is the same audit-trail principle as the runtime decisions themselves; it applies to corpus changes too.
- Full test suite green after every task. Commit/push only when the Director asks.

---

## PART I — LLM-minimization architecture (read before Part D/E)

These enhancements extend `docs/prismguard-design.md` Part 3. They are **required**, not optional optimizations. The receiving agent implements them as part of the runtime pipeline (Part D) and escalation tiers (Part E), not as a later refactor.

### I.1 — Explicit triage outcome table

Replace the implicit three-way split with six auditable outcomes. Every runtime decision must record which gate resolved it (`resolution_gate` field in audit log).

| Outcome | Gate ID | Condition | Cost |
|---------|---------|-----------|------|
| `BLOCK` | `tier1_rule` | High-severity Tier-1 rule hit | ~0 |
| `ALLOW` | `benign_fast_path` | Contrastive benign margin wins (see I.2) OR structural allow heuristics pass | ~0–ms |
| `BLOCK` | `corpus_match` | Attack score + graph path above per-category threshold | ms |
| `ALLOW` | `corpus_match` | Attack score low AND benign margin positive AND no graph attack connectivity | ms |
| `BLOCK` or `ALLOW` | `structural` | Deterministic structural heuristics resolve before embedding (see I.4) | ~0 |
| `BLOCK` or `ALLOW` | `guard_model` | Fused score in gray band; guard confidence above floor | local inference |
| `BLOCK` or `ALLOW` | `llm_judge` | Guard confidence below floor only | LLM call |
| `BLOCK` | `circuit_breaker` | Judge rate cap exceeded; fail-closed (see I.8) | ~0 |

Cache hits (`decision_cache`) short-circuit to a prior gate's verdict without re-running that tier — log `resolution_gate: decision_cache` with the original gate ID in lineage.

### I.2 — Contrastive benign fast-path (P0)

`benign_adjacent` is not just a control category — it is an **active allow signal**.

After Tier-1 rules miss (and before or in parallel with attack-category ANN, see I.5):
1. Run the same dual-vector + community routing against `benign_adjacent` seeds only (`is_attack_category = false`).
2. Compute `attack_margin = top_attack_score − top_benign_score` (per prompt, across all attack categories).
3. If `top_benign_score ≥ benign_allow_floor` AND `attack_margin ≤ −benign_margin_delta` → **ALLOW** at gate `benign_fast_path` without Guard Model or Judge.
4. If attack and benign scores are both high and margin is inside `±benign_margin_delta` → contribute to fused score (I.3), do not allow on benign alone.

Config keys (in `prismguard/config/triage.yaml`, loaded at startup): `benign_allow_floor`, `benign_margin_delta` — per-category overrides allowed; defaults calibrated in T9c.

### I.3 — Multi-signal fusion before gray zone (P0)

Gray zone entry requires **more than one weak signal**. A single moderate similarity score alone must not land in gray zone.

Fused pre-guard score (deterministic, auditable weights in config):

```
fused = w_sim * attack_similarity
      + w_graph * graph_connectivity_score
      + w_rule * rule_partial_hit_score
      + w_sev * category_severity_weight
      + w_comm * community_routing_confidence
      − w_benign * top_benign_score
```

Triage bands (per category, calibrated in T9c):
- `fused ≥ block_threshold` → BLOCK (`corpus_match`)
- `fused ≤ allow_threshold` AND `attack_margin ≤ −benign_margin_delta` → ALLOW (`corpus_match` or `benign_fast_path`)
- `allow_threshold < fused < block_threshold` AND **≥ 2 independent weak signals** above `weak_signal_floor` → gray zone → Guard Model
- Otherwise → ALLOW (`corpus_match`) — single weak signal is not enough to escalate

Log every component score in the audit lineage.

### I.4 — Structural heuristics layer (P1)

**Files:** `prismguard/runtime/structural.py`

Cheap, fully auditable features run after normalize, before or instead of embedding for clearly benign structure:

- Instruction-override phrase density (even if obfuscated post-normalize)
- Role-assignment patterns (`you are now`, `pretend you are`, `developer mode`)
- Imperative / second-person command ratio
- Encoded-blob detection (nested base64, mixed scripts, reversed segments)
- Delimiter / injection markers (HTML comments, `<!--`, fake system blocks)
- **Benign framing signals** for `benign_adjacent`: third-person fiction markers, academic/research framing (`for my report`, `documenting`, `red-team training`), question-about-taxonomy vs perform-attack distinction (heuristic keyword sets, not LLM)

Outcomes:
- High structural attack score + no benign framing → can contribute to fused score or short-circuit BLOCK if above `structural_block_threshold`
- High benign framing + low structural attack → ALLOW at gate `structural` without embedding
- Ambiguous → proceed to selective embedding (I.5)

### I.5 — Selective and overlapping embedding (P1)

Do not embed every chunk on every request.

1. After normalize + structural pass, segment text into chunks (reuse prismRAG chunking if available).
2. **Suspicious segment filter:** only embed chunks containing suspicious n-grams, encoding-like blobs, or structural markers above a low floor. If zero suspicious segments → ALLOW at gate `structural` (log `no_suspicious_segments`).
3. **Overlapping chunks:** use sliding window with ≥25% overlap so attacks split across chunk boundaries are not missed (reduces false gray-zone from partial matches).
4. **Nested obfuscation:** extend normalize (T8) with recursive decode (base64-of-base64, hex layers) up to a configurable depth cap — stops at first stable decode or max depth.

### I.6 — Multi-community routing (P2)

When primary community routing confidence `< community_confidence_floor`:
- Query **top-2 communities** (primary + highest bridge-connected neighbor per `prismrag.bridges`) in parallel.
- Aggregate best attack score and graph path across both.
- Only enter gray zone if **both** routed communities produce ambiguous fused scores.

### I.7 — Session-level multi-turn scoring (P2)

**Files:** `prismguard/runtime/session.py`

Single-message pipeline misses `multi_turn_escalation` and `payload_splitting`. Add optional session context (in-memory or Redis — document which; default in-process for v1):

Per `session_id`, track:
- Category trajectory over last N turns (slugs + scores)
- Cumulative severity trend
- Cross-turn variable references (`part 2`, `the value above`, `call it X` / `now execute X`)
- Refusal-suppression phrase accumulation

Match against known escalation shapes from seed corpus (deterministic templates, not LLM). Session escalation score feeds into fused score (I.3) as `w_session * session_escalation_score`.

API: `check(prompt, session_id=None, turn_index=None)` — backward compatible when session omitted.

### I.8 — Decision cache stack (P1)

**Files:** `prismguard/runtime/cache.py`

| Layer | Key | Reuses verdict from |
|-------|-----|---------------------|
| L1 | `sha256(raw_prompt)` | Any gate |
| L2 | `sha256(normalized_prompt)` | Any gate |
| L3 | embedding NN: nearest prior verdict if cosine ≥ `semantic_cache_threshold` | Guard or Judge only |

- Guard Model results cached at L2/L3 as well as Judge (original design only mentioned judge cache).
- TTL configurable; session-scoped cache optional for multi-turn probes.
- Log cache hit with original `resolution_gate` in lineage.

### I.9 — Judge constraints and circuit breaker pairing (P1)

Extend T12:
- **Closed-world judge:** output must be one of taxonomy slugs + `benign` — not freeform attack description.
- **Smaller default judge model** than application LLM (document choice; swappable).
- When judge call rate exceeds cap: fail-closed BLOCK **and** temporarily tighten gray-zone entry (`block_threshold` lowered, `weak_signal_floor` raised) and optionally accept Guard Model at lower confidence — reduces sustained judge volume during probing campaigns.

### I.10 — Compounding feedback: distillation and rule promotion (P2/P3)

Extend T13:
- High-confidence Judge blocks → offline distillation batch into Guard Model training set (export JSONL; retrain is manual/scheduled, not inline).
- Repeated judge blocks on same pattern family → generate **candidate Tier-1 rules** (regex generalization); human approval queue before promotion (reuse review queue).
- On ingest (T4/T7): auto-expand obfuscation variants for high-severity seeds (leetspeak, homoglyph map, common encodings) as additional seed rows tagged `source: variant_expansion` — reduces obfuscated prompts reaching gray zone over time.

### I.11 — Updated request-time flow

```
Incoming Prompt (+ optional session_id)
  │
  ▼
Decision cache L1/L2/L3 hit? ──────────────────────────────► Cached verdict
  │
  ▼
Normalize (+ nested obfuscation decode)
  │
  ▼
Session context merge (if session_id) ──► session_escalation_score
  │
  ▼
Tier-1 Rule Check ── high severity ────────────────────────► BLOCK (tier1_rule)
  │
  ▼
Structural heuristics ── clear allow/block ────────────────► ALLOW/BLOCK (structural)
  │
  ▼
Suspicious-segment filter ── none suspicious ─────────────► ALLOW (structural)
  │
  ▼
Selective overlapping chunk embed (dual vectors)
  │
  ├─► Attack communities ANN (+ top-2 if low confidence)
  └─► Benign_adjacent ANN (contrastive path)
  │
  ▼
Graph BFS expansion (attack paths only)
  │
  ▼
Multi-signal fusion + contrastive margin + session score
  │
  ├── block band ──────────────────────────────────────────► BLOCK (corpus_match)
  ├── allow band + benign margin ──────────────────────────► ALLOW (benign_fast_path / corpus_match)
  └── gray zone (≥2 weak signals)
        │
        ▼
      Guard Model (+ L2/L3 cache)
        │
        ├── confident ─────────────────────────────────────► Final (guard_model)
        └── not confident
              │
              ▼
            LLM Judge (closed-world; + cache)
              │  rate cap exceeded ────────────────────────► BLOCK (circuit_breaker)
              ▼
            Final (llm_judge)
```

### I.12 — Measurement requirements (bind to benchmarks)

T10 must report **per-gate resolution rates**, not just precision/recall:
- % resolved at each gate (`tier1_rule`, `structural`, `benign_fast_path`, `corpus_match`, `guard_model`, `llm_judge`, `decision_cache`, `circuit_breaker`)
- Gray-zone rate before vs after I.2–I.7 (ablation columns in benchmark report)

T11 must report guard resolution rate **on the remaining gray zone after I.2–I.7**.

T12 must report judge call rate **as % of total traffic** and **as % of gray zone** — both must be measured.

---

## PART J — Pluggable storage (pgvector default, not locked in)

Vector ANN and seed persistence must **never** be hard-coded to Postgres/pgvector in runtime, seed-import, or audit code. Follow the same adapter pattern as `prismrag-patch` (`PgvectorAdapter`, `ChromaAdapter`, `PineconeAdapter`, `WeaviateAdapter`).

### J.1 — Architecture rule

```
prismguard/runtime/*  ──┐
prismguard/seed/*     ──┼──►  StorageBackend (protocol)
prismguard/audit/*    ──┘           │
                                    ├── VectorStore      (ANN + seed entries)
                                    └── RelationalStore  (taxonomy, rules, import_log, decision_log)
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              PgvectorBackend      ChromaBackend         PineconeBackend …
```

**Forbidden:** `import psycopg2` / `import chromadb` / etc. outside `prismguard/storage/backends/*`.

### J.2 — Supported backends (v1)

| Backend | Role | pip extra | Config keys |
|---------|------|-----------|-------------|
| `pgvector` | Default production; co-located relational + vector | `prismguard[pgvector]` | `dsn`, `schema_prefix` |
| `chroma` | Local/embedded vector | `prismguard[chroma]` | `collection_name`, `persist_directory` |
| `pinecone` | Managed cloud vector | `prismguard[pinecone]` | `index_name`, `namespace`, `api_key` (env) |
| `weaviate` | Self-hosted or cloud vector | `prismguard[weaviate]` | `class_name`, `url`, `api_key` (env) |
| `memory` | Unit tests, CI, local dev | (core) | none |

Factory: `prismguard.storage.create_storage(backend, **config)` and `create_storage_from_env()`.
Custom backends: `register_backend(name, factory)` without forking.

Config file: `prismguard/config/storage.yaml`. Env override: `PRISMGUARD_STORAGE_BACKEND`, `PRISMGUARD_STORAGE_DSN`, `PRISMGUARD_CHROMA_PERSIST_DIR`, `PRISMGUARD_PINECONE_INDEX`, `PRISMGUARD_WEAVIATE_URL`.

### J.3 — Relational vs vector split

- **pgvector:** single Postgres instance holds vectors + taxonomy + audit tables (design doc Part 4 DDL).
- **chroma / pinecone / weaviate:** vectors live in the external store; taxonomy, rules, `import_log`, `calibration_log`, `decision_log` use **embedded SQLite** by default (`relational_sqlite_path` in config), with optional `relational_dsn` to share Postgres for compliance/ops teams that want one audit DB.

### J.4 — prismRAG / prismCortex integration

- prismRAG graph/taxonomy operations go through `StorageBackend.relational` + prismRAG's own adapter for the chosen vector backend — verify at T6/T7 whether prismRAG exposes a backend-agnostic ingest API or needs a thin wrapper per adapter.
- prismCortex seed writes on pgvector map to `prismcortex.seed_entries`; on other backends, same logical schema stored as vector metadata + relational rows — **field names in Part 4 are the cross-backend contract**.

### J.5 — Testing requirement

Every backend that ships must pass the shared conformance suite in `tests/storage/conformance.py` (ANN round-trip, category-scoped search, upsert/delete-by-category, import-log append). CI runs `memory` always; `pgvector` runs when `PRISMGUARD_TEST_DSN` is set; other backends run in optional nightly/labelled jobs.

---

## PART A — Repo & foundation

### T1 — Project scaffold
**Files:** `pyproject.toml`, `prismguard/__init__.py`, `prismguard/config/triage.yaml` (default thresholds/weights from Part I), `tests/`, `README.md` (already present)

Mirror the layout of sibling Prism packages already on disk (`C:\code\PrismTether`, `C:\code\PrismRagLib`): a single importable package (`prismguard`), a `tests/` dir, `pyproject.toml` declaring `prismlib`, `prismrag-patch`, `prismcortex` as dependencies. Confirm actual PyPI extras needed (e.g. `prismlib[cache]`, `prismrag-patch[graph,pgvector]`) by checking those packages' own install docs rather than assuming from the family-reference doc.

**Exit:** `pip install -e .` succeeds; empty test suite runs green; imports of `prismlib`, `prismrag_patch`, `prismcortex` succeed in a Python shell (with `prismguard[prism]` extra); `triage.yaml` loads with all keys referenced in Part I; `create_storage("memory")` returns a working `StorageBackend` (Part J — started in T1).

### T2 — Storage abstraction + pgvector backend (default)
**Files:** `prismguard/storage/` (protocols, factory, memory — **started**), `prismguard/storage/backends/pgvector.py`, `prismguard/db/migrations/`, `prismguard/db/schema.sql`, `tests/storage/conformance.py`

Implement Part J. Wire `PgvectorBackend` fully (today it is a constructor stub). Stand up `prismcortex.seed_entries` per `docs/prismguard-design.md` Part 4 **inside the pgvector adapter only**. Before writing DDL for `prismrag.*` tables, **check whether `prismrag-patch`'s store already creates and owns that schema** — if so, configure PrismRAG against the same Postgres instance, not duplicate DDL.

Add relational tables (pgvector backend, or shared Postgres via `relational_dsn`):
- `prismguard.import_log` (import audit)
- `prismguard.calibration_log` (near-miss allows for threshold tuning — T9c/T13)
- `prismguard.decision_log` with `resolution_gate`, fused score components, `attack_margin`, cache hit metadata (T14)

**Exit:** `create_storage("pgvector", dsn=...)` passes `tests/storage/conformance.py`; migration applies on fresh Postgres+pgvector; round-trip 768-d + 256-d vectors; **no `psycopg2` import outside `prismguard/storage/backends/`** (enforce with a lint test).

### T2b — Alternate vector backends (chroma, pinecone, weaviate)
**Files:** `prismguard/storage/backends/{chroma,pinecone,weaviate}.py` (stubs exist — wire fully), reuse `prismrag-patch` adapters where possible

Each backend implements the same `VectorStore` protocol. Relational tables default to SQLite unless `relational_dsn` is set (J.3).

**Exit:** each wired backend passes `tests/storage/conformance.py` when its integration env var is set (`PRISMGUARD_TEST_CHROMA_DIR`, `PRISMGUARD_TEST_PINECONE_INDEX`, `PRISMGUARD_TEST_WEAVIATE_URL`); `pip install prismguard[chroma]` does not pull pgvector deps.

---

## PART B — Seed import tool (build this before anything reads from the corpus)

### T3 — Seed file format parsers

**Files:** `prismguard/seed/formats/{yaml_taxonomy,json_taxonomy,csv_entries,jsonl_entries,markdown_seed}.py`, `prismguard/seed/parse.py` (dispatcher)

Support five input shapes, each parsed into one common in-memory representation (`ParsedSeed = {categories: [...], rules: [...], entries: [...]}` — any of the three lists may be empty depending on what the file contains):

**1. YAML/JSON "taxonomy" format** — for hand-authored categories, rules, and bridges:
```yaml
categories:
  - slug: direct_instruction_override
    label: Direct instruction override
    is_attack_category: true
    bridges_to: [encoding_obfuscation]
  - slug: benign_adjacent
    label: Benign adjacent (control)
    is_attack_category: false
    bridges_to: []

rules:
  - rule_id: R-0142
    pattern: 'ignore (all |the )?(previous|prior|above) instructions?'
    pattern_type: regex        # regex | keyword
    category_slug: direct_instruction_override
    severity: high
    rationale: canonical direct-override phrasing

entries:
  - text: "Ignore all previous instructions and instead..."
    category_slug: direct_instruction_override
    severity: high
    source: seed-v0
```
JSON accepted as the same shape (categories/rules/entries keys), for tooling that exports JSON rather than YAML.

**2. CSV entries** — for bulk seed examples with no category/rule definitions:
```
text,category_slug,severity,source,rule_id,notes
"Ignore all previous instructions...",direct_instruction_override,high,seed-v0,,
```
`rule_id` and `notes` columns optional; unknown/missing columns other than `text` and `category_slug` get sane defaults (`severity=medium`, `source=csv-import`).

**3. JSONL entries** — one JSON object per line, same fields as a CSV row — for large or streamed seed sets / exports from another system.

**4. Markdown seed doc** — parse `docs/prismguard-design.md` Part 5's actual convention directly: a `### Categories` section containing a `| Slug | Description | Bridges to |` table, followed by a `### Seed examples...` section where each category is a `**\`slug\`**` bold header followed by a bullet list of example strings. This is the format the Director's own seed doc is written in — the parser must handle it as-is, not a reformatted version. Bullet lines that are clearly prose/commentary rather than an example (e.g. the "Detection signal: ..." line under `multi_turn_escalation`) should be skippable via a documented heuristic (lines starting with a recognizable prefix word, or an explicit `<!-- not-an-example -->` marker the parser looks for) — get this right by testing against the real file (T5), not a hand-simplified stand-in.

**5. Format detection:** `--format auto` (default) picks a parser by file extension first (`.yaml`/`.yml`, `.json`, `.csv`, `.jsonl`, `.md`), falling back to content sniffing if the extension is ambiguous or missing.

**Exit:** unit test per format parsing a small fixture into the common `ParsedSeed` shape; one test parses the *real* `docs/prismguard-design.md` file (not a copy) end-to-end and asserts all 10 categories and all seed examples from Part 5 are extracted correctly, including the `benign_adjacent` negative examples.

### T4 — Import CLI/API with multi-source, update, and replace modes

**Files:** `prismguard/seed/importer.py`, `prismguard/seed/merge.py`, `prismguard/seed/parse.py`, `prismguard/cli.py` (`prismguard-seed import ...`) — **core implemented; pgvector persistence completes in T2**

Importer accepts `storage: StorageBackend` (injected or from `create_storage_from_env()`) — **never opens its own DB connection**. All writes go through `storage.vector` and `storage.relational`.

#### Multi-source input (required)

One import run may load **many sources**, merged in CLI order before a single write:

```
prismguard-seed import <source> [<source> ...] \
  [--format auto|yaml|json|jsonl|csv|markdown] \
  [--mode update|replace]        (default: update) \
  [--scope all|category:<slug>]  (default: all; only meaningful with --mode replace) \
  [--recursive]                    (directories: include subfolders) \
  [--dry-run] \
  [--confirm-replace-all]        (required alongside --mode replace --scope all) \
  [--expand-variants]            (optional: run obfuscation variant expansion per I.10) \
  [--force]
```

Each `<source>` may be:
| Source type | Example | Behavior |
|-------------|---------|----------|
| File | `taxonomy.yaml` `extra.csv` | Parsed with per-file auto format detection |
| Directory | `seeds/redteam/` | All supported extensions in dir (`--recursive` for nested) |
| Manifest | `@sources.txt` | One path per line (`#` comments allowed) |

**Typical multi-source workflow:**
```bash
# 1) Bootstrap taxonomy + markdown seed from design doc
prismguard-seed import docs/prismguard-design.md --mode update

# 2) Append red-team CSV + JSONL exports without touching existing rows
prismguard-seed import redteam/exports/jan.jsonl redteam/exports/feb.csv --mode update

# 3) Replace only one category's batch after a bad import
prismguard-seed import fixes/roleplay_jailbreak.yaml --mode replace --scope category:roleplay_jailbreak

# 4) Full corpus rebuild from manifest (destructive)
prismguard-seed import @seed-manifest.txt --mode replace --scope all --confirm-replace-all
```

**Merge rules (multi-source):**
- Sources processed in CLI order (manifest order, then directory glob sort).
- **Categories:** later source wins on `label`/`description`; `bridges_to` unioned.
- **Rules:** same `rule_id` with different pattern/category → **error** (unless `--force`).
- **Entries:** deduped by `(category_slug, sha256(normalized_text))`; later source wins on `severity`/`source`.

#### Update mode (default, safe, incremental)
- Match existing entries by `(category_slug, sha256(normalized_text))` — normalize the same way the runtime path normalizes (Part 3 of the design doc: NFKC, lowercase, strip zero-width) so re-importing slightly-reformatted duplicates doesn't create near-duplicate rows.
- Matched rows: update mutable fields (`severity`, `source`, `rule_id` reference) if they differ; unmatched rows: insert as new.
- Categories/rules referenced in the file but not yet in `prismrag.categories`/`prismrag.rules`: created, but flagged in the import report as "new taxonomy element — recommend review" rather than silently trusted, especially if `severity: high`.
- Nothing is ever deleted in update mode.
- **Idempotency requirement:** running the same file through `update` twice produces zero net row changes the second time — this is a real exit test, not an assumption.

**Replace mode (destructive, explicit):**
- `--scope all`: truncate `prismcortex.seed_entries` (and prompt for `--confirm-replace-all`; refuse to run without it) then load fresh from the file.
- `--scope category:<slug>`: delete only entries under that category, then load the file's entries for that category. This is the common case in practice — superseding one attack family's bad batch without touching the rest of the corpus — and should not require the `--confirm-replace-all` flag (smaller blast radius).

**Validation (both modes, runs before any write):** unknown category references (in update mode these become "new category" as above; in replace mode with an unrecognized category and no matching `--scope`, abort), duplicate `rule_id`s within the file, malformed regex patterns (compile-check every `pattern_type: regex` rule). Collect into a report; abort with the report on error unless `--force` is passed.

**Every import run is logged**: source filename, mode, scope, counts (inserted / updated / skipped / errored), timestamp — write to a `prismguard.import_log` table (or reuse `prismcortex`'s own audit mechanism if it already has one — check before adding a duplicate one).

**Exit:** `--dry-run` produces a diff report and writes nothing; **multi-source** `taxonomy.yaml + entries.csv` merges and imports; `update` twice is a no-op the second time; `replace --scope=category:X` removes only category X's prior rows; `replace --scope=all` without `--confirm-replace-all` refuses; `@manifest` and directory sources work; malformed regex aborts with clear error.

### T5 — Load the real seed as the first import

**Files:** bundled corpus lives in `prismguard/seed/corpus/` (`authored/seed.yaml`, `external/*`, manifests) — **shipped with the package via setuptools package-data**

```bash
prismguard-seed import --bundled                      # authored only (default)
prismguard-seed import --bundled --profile full       # + S-Labs + yanismiraoui
```

Python API: `from prismguard.seed import import_bundled_seed, load_bundled_seed`

Default storage: pgvector via `PRISMGUARD_STORAGE_DSN`; CI uses `PRISMGUARD_STORAGE_BACKEND=memory` or CLI default (memory when no DSN).

**Exit:** all 10 categories present in `prismrag.categories`; all Part 5 seed examples present in `prismcortex.seed_entries` with correct `category_slug`; `benign_adjacent` entries present and correctly flagged `is_attack_category: false`; re-running the same import is a no-op (proves T4's idempotency claim against real content, not just a unit fixture).

---

## PART C — Taxonomy wiring (prismRAG)

### T6 — Wire categories/rules/bridges into prismRAG's mapping

**Files:** `prismguard/taxonomy/mapping.py`

Feed the imported categories/rules/bridges (T5's output, now in Postgres) into prismRAG's actual `Mapping` construct — check `prismrag_patch`'s real API (class name, constructor signature) before assuming; the family-reference doc names concepts ("mapping table," "Tier-1 rules") but the handoff must verify against the installed package's source, per the standing rules.

**Exit:** a `Mapping` instance built from the imported taxonomy round-trips through prismRAG's own category-assignment call for a known example (e.g. the `direct_instruction_override` seed text assigns to that category).

### T7 — Dual-vector ingest

**Files:** `prismguard/taxonomy/ingest.py`, `prismguard/taxonomy/variant_expansion.py`

Run every seed row through prismRAG's ingest pipeline to produce dual vectors. Persist via `storage.vector.upsert_seed_entry()` — backend-agnostic (Part J).

**Variant expansion (I.10):** for `severity: high` attack-category entries, generate leetspeak/homoglyph/base64 variant rows (`source: variant_expansion`); dedupe by normalized hash; optional `--expand-variants` on import.

**Exit:** every seed entry has both vectors populated in Postgres; a spot-check query (nearest neighbor for a known jailbreak phrase) returns entries from the correct category, not a topically-adjacent wrong one; at least one obfuscated variant of a high-severity seed is retrievable via ANN.

---

## PART D — Runtime check pipeline (with Part I enhancements)

### T8 — Normalize step
**Files:** `prismguard/runtime/normalize.py`

Unicode NFKC normalization, common-obfuscation decoding (base64/hex/rot13 detection + decode), zero-width/homoglyph stripping, lowercasing — per design doc Part 3.

**Add (I.5):** recursive nested decode up to `max_obfuscation_depth` (config); document stop conditions.

**Exit:** a base64-encoded jailbreak phrase decodes and matches its Tier-1 rule; a zero-width-character-interspersed phrase strips to the clean version and matches; nested base64-of-base64 decodes within depth cap.

### T8a — Structural heuristics layer
**Files:** `prismguard/runtime/structural.py`

Implement I.4. Return `StructuralResult` with `attack_score`, `benign_framing_score`, `markers_matched[]`, and recommended short-circuit (`allow` | `block` | `continue`).

**Exit:** benign_adjacent seed examples (research framing, fictional third-person) short-circuit ALLOW at gate `structural`; canonical override phrases short-circuit BLOCK or boost fused score; ambiguous prompts return `continue`.

### T8b — Session context
**Files:** `prismguard/runtime/session.py`

Implement I.7. In-memory session store for v1 (`SessionStore` protocol for future Redis).

**Exit:** two-turn fixture matching `payload_splitting` pattern increases `session_escalation_score` on turn 2; single-turn API unchanged when `session_id` omitted.

### T9 — The runtime check itself
**Files:** `prismguard/runtime/check.py`, `prismguard/runtime/fusion.py`, `prismguard/runtime/cache.py`

Full pipeline per I.11:
- Decision cache (I.8)
- Tier-1 rules
- Structural (T8a)
- Selective overlapping embed (I.5)
- Parallel attack + benign_adjacent ANN (I.2)
- Multi-community routing when low confidence (I.6)
- Graph BFS (attack only)
- Multi-signal fusion + contrastive margin (I.3)
- Session score integration (T8b)
- Triage to `block | gray | allow` with explicit `resolution_gate`

**Exit:** unit tests for all triage outcomes in I.1 table; `benign_adjacent` paraphrases ALLOW via `benign_fast_path` without gray zone; paraphrased jailbreak reaches `block` or justified `gray` via graph/fusion; single weak signal does NOT enter gray zone; cache L2 hit skips embed on repeat normalized prompt.

### T9c — Per-category threshold calibration (Phase 1 — before Part E)
**Files:** `prismguard/calibration/tune.py`, `benchmark/calibration/`

Use held-out split from eval set + `calibration_log` schema. Tune `block_threshold`, `allow_threshold`, `benign_margin_delta`, fusion weights per category. **Do not use held-out red-team set for tuning** (design doc Part 8).

**Exit:** `triage.yaml` updated with measured defaults; report shows gray-zone rate reduction vs uncalibrated baselines on calibration split.

### T10 — Standalone benchmark (design doc Phase 1 — do this before building Layer 2)

**Files:** `benchmark/` (new), `benchmark/ablation/` (per I.12)

Run T9's pipeline alone (no Guard Model, no LLM Judge yet) against a public adversarial prompt-injection eval set, and against a free baseline (e.g. Llama Guard) on the same set. Report real precision/recall — do not proceed to Part E until this number exists.

**Required report sections (I.12):**
- Precision/recall/F1 vs baseline
- **Per-gate resolution %** table
- **Ablation:** remove I.2, I.3, I.4, I.5 one at a time — show gray-zone rate delta
- False positive count on benign_adjacent holdout prompts

**Exit:** benchmark report with actual numbers, checked into `benchmark/results/`; gray-zone rate documented before Part E.

---

## PART E — Escalation tiers

### T11 — Guard Model
**Files:** `prismguard/runtime/guard_model.py`

Swappable interface; a default (fine-tuned small classifier or off-the-shelf guard model — pick one, document why, leave it swappable per the design doc's open question). Input includes fused score components and contrastive margin (I.3), not raw prompt alone.

Integrate decision cache L2/L3 for guard verdicts (I.8).

**Exit:** given T9's **remaining** gray-zone outputs after Part I layers, measure what fraction the Guard Model resolves confidently vs. escalates — this is the number that determines whether Part F's LLM Judge volume target is realistic; report both % of gray zone and % of total traffic.

### T12 — LLM Judge
**Files:** `prismguard/runtime/llm_judge.py`

Isolated, stateless call; **closed-world** structured output (taxonomy slug + `benign` only — I.9); input includes matched examples + category/rule context + fused lineage; no tool access, no conversation memory; rate cap + circuit breaker with paired gray-zone tightening (I.9); verdict caching L1/L2/L3 (I.8).

**Exit:** adversarial-injection-against-the-judge test case still classifies as attack; judge output schema validates slug-only; circuit breaker test forces `circuit_breaker` gate without unbounded judge calls; measured judge % of total traffic documented.

### T12a — End-to-end escalation benchmark

**Files:** `benchmark/escalation/`

Full pipeline T9+T11+T12 on same eval set. Report judge call rate, guard call rate, cache hit rate, per-gate breakdown.

**Exit:** numbers compared to design doc hypothesis table — labeled measured vs hypothetical.

---

## PART F — Feedback loop

### T13 — Review queue + append-back + distillation

**Files:** `prismguard/feedback/review.py`, `prismguard/feedback/distill.py`, `prismguard/feedback/rule_candidates.py`

Confirmed blocks → human review queue → on approval, call **T4's importer in `update` mode** (reuse it, don't build a second write path) to append as new seed entries. Near-miss allows → `calibration_log` (feeds T9c, not seed corpus directly).

**Add (I.10):**
- Export high-confidence judge blocks to `distill/guard_training.jsonl`
- Repeated pattern families → `rule_candidates` queue for human-approved Tier-1 promotion
- Approved candidates written via same importer as rules

**Exit:** reviewed LLM-Judge-confirmed attack in `prismcortex.seed_entries` with `source: llm_judge_reviewed`; unreviewed block NOT auto-appended; distillation export non-empty after test judge blocks; one approved rule candidate becomes a live Tier-1 rule.

---

## PART G — Audit & observability

### T14 — Decision logging
**Files:** `prismguard/audit/log.py`

Every runtime decision logged with full lineage per I.1: `resolution_gate`, rule hits, category, similarity scores, `attack_margin`, fused components, graph path, structural markers, session scores, guard verdict, judge verdict (if invoked), cache metadata, final decision. Query surface ("why was prompt X blocked") answers from log without re-running classification.

**Exit:** given a logged decision ID, lookup returns gate + rule/category/score lineage in human-readable form.

---

## PART H — Packaging

### T15 — Release packaging
**Files:** `pyproject.toml`, `README.md`

Follow the same convention as sibling packages (`prismlib`, `prismrag-patch`, `prismcortex`) — pip-installable, PyPI-ready metadata, extras for optional pieces (e.g. `prismguard[guard-model]`, `prismguard[session-redis]`).

**Exit:** `python -m build` produces a clean wheel; fresh-venv install + import succeeds.

---

## Execution plan (ordered phases)

### Phase 0 — Foundation (Days 1–2)
| Step | Task | Depends on | Deliverable |
|------|------|------------|-------------|
| 0.1 | T1 scaffold + `triage.yaml` + storage protocols | — | installable package + `create_storage("memory")` |
| 0.2 | T2 pgvector backend + schema | T1 | conformance suite on pgvector |
| 0.3 | T2b chroma/pinecone/weaviate | T2 | optional backend conformance |

### Phase 1 — Corpus & taxonomy (Days 3–6)
| Step | Task | Depends on | Deliverable |
|------|------|------------|-------------|
| 1.1 | T3 parsers | T1 | 5 format parsers tested |
| 1.2 | T4 importer CLI | T3, T2 | update/replace/idempotent |
| 1.3 | T5 real seed load | T4 | Part 5 in Postgres |
| 1.4 | T6 mapping wire | T5 | Mapping round-trip |
| 1.5 | T7 ingest + variants | T5, T6 | dual vectors populated |

### Phase 2 — Deterministic runtime (Days 7–11) — **maximize LLM avoidance here**
| Step | Task | Depends on | Deliverable |
|------|------|------------|-------------|
| 2.1 | T8 normalize + nested decode | T6 | obfuscation tests pass |
| 2.2 | T8a structural heuristics | T8 | benign fast structural allows |
| 2.3 | T8b session store | T8 | multi-turn fixtures |
| 2.4 | T9 runtime check + fusion + cache | T8a, T8b, T7 | full I.11 pipeline |
| 2.5 | T9c threshold calibration | T9 | tuned `triage.yaml` |
| 2.6 | **T10 benchmark + ablation** | T9c | **GATE: do not start Phase 3 until gray-zone rate is measured** |

### Phase 3 — Escalation (Days 12–15) — only after T10 gate
| Step | Task | Depends on | Deliverable |
|------|------|------------|-------------|
| 3.1 | T11 guard model | T10 | guard resolution % measured |
| 3.2 | T12 LLM judge + circuit breaker | T11 | judge % measured |
| 3.3 | T12a end-to-end escalation benchmark | T12 | full per-gate report |

### Phase 4 — Learning & ship (Days 16–19)
| Step | Task | Depends on | Deliverable |
|------|------|------------|-------------|
| 4.1 | T13 feedback + distillation | T4, T12 | closed learning loop |
| 4.2 | T14 audit | T9 | queryable lineage |
| 4.3 | T15 packaging | all | wheel on PyPI-ready metadata |

### Critical path

```
T1 → T2 → T2b → T3 → T4 → T5 → T6 → T7 → T8 → T8a → T8b → T9 → T9c → T10
                                                              │
                              ┌───────────────────────────────┘
                              ▼ (GATE)
                    T11 → T12 → T12a → T13 → T14 → T15
```

### Effort estimate (revised)

| Part | Estimate | Notes |
|------|----------|-------|
| A | 1–2d | +storage protocols/factory (T1), pgvector (T2), alt backends (T2b) |
| B | 3–4d | unchanged |
| C | 2d | +variant expansion |
| D | 5–6d | +structural, session, fusion, cache, calibration, ablation benchmark |
| E | 3–4d | +closed-world judge, T12a e2e benchmark |
| F | 2–3d | +distillation, rule candidates |
| G | 1d | +extended lineage fields |
| H | 1d | |
| **Total** | **~18–23d** | |

---

## Priority map — LLM call reduction

| Priority | Enhancement | Task(s) | Expected effect |
|----------|-------------|---------|-----------------|
| P0 | Contrastive benign fast-path | T9 (I.2) | Largest gray-zone shrink |
| P0 | Multi-signal fusion + 2-signal gray gate | T9 (I.3) | Fewer false grays |
| P0 | Per-category calibration in Phase 1 | T9c | Fewer conservative grays |
| P1 | Structural heuristics | T8a (I.4) | Allow/block before embed |
| P1 | Selective + overlapping embed | T9 (I.5) | Fewer misses → fewer grays |
| P1 | Decision cache L1/L2/L3 | T9 (I.8) | Repeat/probe traffic |
| P1 | Guard + judge cache integration | T11, T12 | Same |
| P2 | Multi-community routing | T9 (I.6) | Mis-route recovery |
| P2 | Session multi-turn scoring | T8b (I.7) | Escalation without per-turn judge |
| P2 | Variant expansion on ingest | T7 (I.10) | Obfuscation coverage |
| P3 | Distillation + rule promotion | T13 (I.10) | Compounding reduction |

---

## Order & effort (summary)

Part A → Part B (importer first; Part F reuses it) → Part C → Part D (**includes Part I deterministic layers; stop at T10 for benchmark gate**) → Part E → Part F → Part G → Part H.

**Hard gate:** T10 must report per-gate resolution rates and gray-zone % before T11/T12 are started. If gray-zone exceeds single-digit % on the eval set after T9c, iterate T9c/T8a/I.2 tuning before adding LLM cost.

## Return format (`handoffbackPrismGuardImplementation.md`)

Per task: files touched · exit criteria pass/fail with real command output · **actual `prismlib`/`prismrag-patch`/`prismcortex` signatures verified vs. what this handoff assumed** (flag every deviation) · T5's real import counts · T10's benchmark numbers **including per-gate resolution table and ablation columns** · T11 guard resolution rate on remaining gray zone · T12a judge % of total traffic · anything blocked, stated plainly. No commits unless the Director asks.

---
*PrismGuardImplementation · Part J makes pgvector the default, not a lock-in — runtime/seed/audit never import vector drivers directly · Part B ships before anything reads from the corpus · Part I LLM-minimization layers are part of Part D · Part D stops at T10 for a real benchmark before Part E adds any LLM cost.*
