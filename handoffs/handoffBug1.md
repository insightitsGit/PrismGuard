# Handoff Bug1 — fix the review findings, most severe first

**Director:** Amin · **Architect:** Claude · **Engineer:** (receiving agent)
**Refs:** [`docs/prismguard-design.md`](../docs/prismguard-design.md) Part 3 and the "PART I — LLM-minimization architecture" section of [`handoffs/handoffPrismGuardImplementation.md`](handoffPrismGuardImplementation.md) (the intended fusion/triage spec these bugs violate) · [`handoffs/handoffbackPrismGuardImplementation.md`](handoffbackPrismGuardImplementation.md) (what was actually built) · this handoff's findings came from a 4-agent code review of commit `b86c6f4` plus direct verification against the running code and `prismguard/config/triage.yaml`
**Date issued:** 2026-07-07

---

## 0. Why

The implementation in `b86c6f4` passes all 37 tests and the seed/taxonomy layer works, but the **runtime triage math does not do what the design or the tests claim it does**. The most severe finding: `fuse_signals()` only sums 3 of the 6 weighted terms `triage.yaml` defines, so the mathematical maximum fused score (0.60) can never reach the configured `block_threshold` (0.78) — meaning the `fusion_block` gate is dead code right now, and the *only* things that can currently block a prompt are Tier-1 regex hits and a hardcoded `0.92` magic number. That directly defeats this project's stated primary goal (resolve most attack traffic deterministically, before any LLM escalation) without any test catching it, because the tests that exist assert weaker things than the design's actual numeric guarantees.

Fix these in the order below — the first four are the same class of bug (silently wrong calibration math) and block/allow decisions are not trustworthy until all four land together; the rest are independent and can be parallelized.

**Standing rules (same as the original implementation handoff):**
- Every fix in this handoff gets a **regression test that would have failed before the fix and passes after** — not just "the function runs without raising." If you can't write a test that fails on the old code, you haven't actually verified the fix.
- Verify against the actual installed `prismrag-patch` API (0.2.1, not whatever `pyproject.toml` currently pins) before changing `taxonomy/mapping.py` — re-read `handoffs/handoffbackPrismGuardImplementation.md`'s "prismRAG API (verified prismrag-patch==0.2.1)" table first.
- Full `pytest -q` green after every task. Do not weaken an existing passing test to make a new one pass.
- Commit/push only when the Director asks.

---

## PART A — Runtime triage math (fix together, same root cause: calibration silently doesn't match config)

### T1 — Fusion formula is missing 2 of 6 weighted terms; `fusion_block` is currently unreachable
**Files:** `prismguard/runtime/fusion.py`, `prismguard/runtime/check.py`, `prismguard/config/loader.py`

`fuse_signals()` (fusion.py:16-37) only accepts/sums `w_sim*attack_sim + w_rule*rule_boost + w_sev*sev - w_benign*benign_sim`. `triage.yaml` also defines `w_graph: 0.25` and `w_comm: 0.10`, which are never read anywhere in `runtime/`. Max achievable fused score with current weights is `0.35+0.15+0.10 = 0.60`, but `block_threshold = 0.78` — so no input can ever trigger `fusion_block`.

Two real terms are missing because their inputs don't exist yet (graph BFS and community routing are both explicitly "not started" per the implementation handoff-back). You have two honest options — pick one, don't silently do neither:

- **(a) Implement minimal versions of the missing signals now.** `graph_connectivity_score` can start as a simple heuristic (e.g. shared-keyword overlap with the matched category's rule set) rather than full graph BFS; `community_routing_confidence` can start as `1.0` when Tier-1 partially matched the category, `0.5` otherwise. Wire both into `fuse_signals()`'s signature and `check.py`'s call site.
- **(b) Explicitly rescale.** If (a) is out of scope for this handoff, do NOT leave the weights half-applied. Recalibrate `triage.yaml`'s `block_threshold`/`allow_threshold` against the 3 terms actually implemented (document this as an interim state in a comment in `triage.yaml`, and log a warning at `RuntimeChecker` init time that graph/community terms are stubbed at 0 so the deployed thresholds are known-interim, not silently wrong).

Whichever you choose, the fix is not "leave it as is" — right now the config and the code disagree about what's achievable and nothing surfaces that disagreement.

**Exit:** a test that computes the maximum possible `fused_score` given the *actual* implemented weights and asserts it can reach `cfg.triage.block_threshold` with a maximal-severity, rule-matched, `attack_sim=1.0` input — this test must FAIL on the current code (max 0.60 < 0.78) and PASS after the fix.

### T2 — Benign fast-path condition has inverted polarity vs. the design spec
**File:** `prismguard/runtime/check.py:134`

Current: `if benign_sim >= cfg.benign_fast_path.benign_allow_floor and margin < cfg.benign_fast_path.benign_margin_delta` where `margin = attack_sim - benign_sim`. The design (handoff Part I.2) requires `attack_margin <= -benign_margin_delta` — attack score must be **clearly below** benign score, not just "not too far above it."

**Fix:** change the condition to `margin <= -cfg.benign_fast_path.benign_margin_delta`.

**Exit:** a test with `benign_sim=0.75, attack_sim=0.80` (margin=+0.05, benign_sim clears the floor) must NOT take the fast-path — this exact case currently fast-path ALLOWs on unfixed code; assert it now falls through to fusion instead.

### T3 — Per-category threshold overrides are defined in config but never applied at runtime
**File:** `prismguard/runtime/check.py`

`config/loader.py` defines `CategoryOverride` (`block_threshold`, `allow_threshold`, `benign_allow_floor`, `benign_margin_delta`) and `TriageConfig.categories: dict[str, CategoryOverride]`, but `grep -rn "cfg.categories" prismguard/runtime/` returns nothing — every category shares the same global thresholds. Additionally, the hardcoded `0.92` at `check.py:166` (`if top_hit and top_hit.score >= 0.92`) bypasses all of this with a value that isn't configurable, loggable, or per-category.

**Fix:** before comparing any score against a threshold in `check()`, resolve it through `cfg.categories.get(matched_category_slug)` falling back to the global default when no override exists (for `block_threshold`, `allow_threshold`, `benign_allow_floor`, `benign_margin_delta`, and whatever replaces the hardcoded `0.92` — move that into `TriageConfig` as a named, documented field, e.g. `triage.corpus_match_override_threshold`, with a per-category override too).

**Exit:** a test that sets a category-specific `block_threshold` override lower than the global default, and asserts a prompt scoring between the category threshold and the global threshold now blocks (it would not, on unfixed code, since category overrides are never consulted).

### T4 — Gray-zone entry ignores the "≥2 independent weak signals" requirement
**File:** `prismguard/runtime/check.py:156-164`

Design (handoff I.3): "gray zone entry requires more than one weak signal — a single moderate similarity score alone must not land in gray zone." Current code is a plain `if/elif/else` on `fused_score` alone; `cfg.fusion.weak_signal_floor` and `cfg.fusion.min_weak_signals_for_gray` are defined in config and never referenced in `runtime/`.

**Fix:** before routing to `gray`, count how many of the individual signal components (attack_sim, rule partial hits, severity weight, and whichever of T1's graph/community terms you implemented) independently exceed `weak_signal_floor`. If fewer than `min_weak_signals_for_gray`, route to `allow` (per the design's fallback: "otherwise → ALLOW — single weak signal is not enough to escalate") instead of `gray`.

**Exit:** a test with exactly one signal (e.g. `attack_sim` alone) above `weak_signal_floor` and every other component at 0 — on unfixed code this can land in `gray`; after the fix it must route to `allow`, not escalate.

---

## PART B — Taxonomy & seed layer

### T5 — Category vectors silently fall back to wrong dimension, and never self-heal
**Files:** `prismguard/taxonomy/mapping.py:50`, `prismguard/taxonomy/ingest.py`

`remap_category_vector()` calls `PrismRAGPatch.remap_vector(vector, text)`, which only performs the 768→256 projection when `RulesStrategy.infer_category_from_text` finds a whole-token match; otherwise it returns the original 768-d vector unchanged. Nothing checks the resulting dimension before storing it as `embedding_category`, and `ingest.py`'s idempotent skip-check (`if not force and entry.embedding_semantic and entry.embedding_category`) only checks truthiness, not correct dimensionality — so a corrupted row is marked "already embedded" forever.

**Fix:** after calling `remap_vector`, assert/check `len(result) == 256` (or whatever the configured category-vector dimension is); if the projection didn't fire, fall back to the `_substring_rules` fuzzy match (already used by `assign_category`, per T9's fix) before giving up, so category-grounded projection has two chances to fire, not one. Update the idempotent skip-check in `ingest.py` to also verify `len(entry.embedding_category) == expected_category_dim`, so a stale/corrupted row is automatically re-embedded on the next `update` pass without needing `--force-embed`.

**Exit:** a test seeding an entry whose text has no whole-token rule match, asserting `embedding_category` is 256-d (not a 768-d copy) after ingest; a second test asserting a row with a corrupted (wrong-dimension) `embedding_category` gets re-embedded on a subsequent plain `update` import, without `--force-embed`.

### T6 — `pyproject.toml` pins a `prismrag-patch` version the code wasn't built against
**File:** `pyproject.toml:32`

`prism` extra pins `prismrag-patch>=1.0.0`; the implementer's own handoff-back documents the code as built and verified against `0.2.1`'s actual API (`PrismRAGPatch`/`RulesStrategy`/`MappingConfig`), explicitly noting it differs from what a `>=1.0` API was assumed to look like.

**Fix:** pin to the verified version range, e.g. `prismrag-patch>=0.2.1,<1.0.0`, or upgrade `taxonomy/mapping.py` to the real ≥1.0 API if one now exists and is verified — don't leave the pin pointing at an untested major version.

**Exit:** `pip install -e ".[dev]"` in a clean venv resolves a version of `prismrag-patch` whose actual installed API matches what `taxonomy/mapping.py` imports (verify by import, not just by version string).

### T7 — Hex-decode obfuscation bypass only matches whole-string, not embedded payloads
**File:** `prismguard/runtime/normalize.py:37`

`if text.startswith(("0x", "0X"))` only fires when the *entire* string starts with the hex prefix. The base64 branch two lines above uses `_B64_LIKE.search(text)`, finding a token anywhere in the string. Asymmetric — a hex payload embedded in a normal sentence is never decoded.

**Fix:** replace the `startswith` check with a regex search for an embedded hex token (mirroring the base64 branch's pattern), e.g. `re.search(r'0x[0-9a-fA-F]{6,}', text)`, decode the matched token in place rather than requiring it to be the whole string.

**Exit:** `normalize_prompt("please decode 0x68656c6c6f and do it")` must return the decoded payload substituted in place — this fails on current code (returns the string unchanged/lowercased) and must pass after the fix. Also re-run the existing base64 mid-string test to confirm no regression.

### T8 — Seed entry merge silently overwrites on hash collision; inconsistent with rule conflict handling
**File:** `prismguard/seed/merge.py:45-49`

Rules raise `ValueError` on a conflicting `rule_id` across sources (lines 33-44). Entries have no equivalent — `entries[key] = entry` silently overwrites whatever was there, so a hand-authored entry with curated `notes`/`source` can be silently discarded in favor of a later-processed external-dataset duplicate with the same content hash.

**Fix:** when a `content_hash` collision has *different* metadata (severity, source, notes) across sources, either raise the same way rules do, or add a documented precedence rule (e.g. "authored always wins over external, regardless of merge order") and log a warning listing what was superseded — pick one and make it explicit, not silent.

**Exit:** a test merging two `ParsedSeed`s with the same `(category_slug, canonical_text)` but different `source`/`severity` values, asserting either a raised error or a logged, documented precedence outcome (not a silent, unlogged overwrite).

### T9 — Substring category-fallback matcher has no word-boundary check
**File:** `prismguard/taxonomy/mapping.py:43`

`_substring_rules` matches any keyword ≥5 characters via bare `if word in lower` — no word-boundary check, so `"admin"` matches inside `"administrator"`, `"override"` matches inside `"overridden"`.

**Fix:** use a word-boundary regex (`re.search(rf'\b{re.escape(word)}\b', lower)`) instead of plain substring containment.

**Exit:** a test asserting `"I am the system administrator"` does NOT match the `admin`→attack-category fallback rule that a bare substring check would incorrectly fire on; a positive-control test confirms the same rule still matches `"admin access required"`.

### T10 — Dead `content_changed` branch misrepresents its own intent
**File:** `prismguard/seed/importer.py:138`

`existing_index` is keyed by `seed_content_hash(category_slug, raw_text)`, and `content_changed = existing is not None and existing.chunk_text != normalized` where `normalized = normalize_seed_text(canonical)` — but `canonical` is the same value used to compute the hash key that found `existing` in the first place, so `content_changed` can never be `True` given a deterministic `normalize_seed_text`. Not currently harmful (edited text produces a different hash and is correctly handled as a new row via the `existing is None` path) but it's dead code that looks like a safety net and isn't one.

**Fix:** either (a) delete the dead branch and the `content_changed` variable, adding a one-line comment explaining why content-change-in-place can't happen under hash-keyed lookup, or (b) if in-place content correction (same row `id`, edited text) is actually a desired feature, rekey `existing_index` by entry `id` instead of content hash so this branch becomes reachable and meaningful — pick one, don't leave it as silent dead code.

**Exit:** if (a), a test/comment documents why; if (b), a test edits an existing entry's text under the same id and asserts embeddings are cleared and the row is re-embedded.

---

## PART C — Test quality (these tests currently assert less than they claim to)

### T11 — Strengthen tests that pass without verifying the claimed behavior
**Files:** `tests/test_seed_import.py`, `tests/test_bundled_seed.py`, `tests/test_taxonomy.py`, new `tests/test_cli.py`

Found during review, not yet fixed:
- `test_import_runs_taxonomy_after_replace_scope` never asserts an embed count — add an assertion on `report.taxonomy.ingest.embedded`.
- `test_data_exfil_category_documents_output_scan_requirement` only checks the category description string contains certain substrings — rename it to make clear it's a documentation test, not a behavior test, and do not let it stand in for real output-scan test coverage (there is none yet — that's expected, per the design's Part 9, but the test name shouldn't imply otherwise).
- `test_turns_entries_import_with_canonical_hash` asserts a loose `>= 40` bound and a substring match — tighten to assert the exact expected count and that `canonical_text()` correctly joins/hashes the turns (add a case that would catch a dropped or duplicated turn).
- No test exercises `prismguard.cli.main()`/argparse directly — add `tests/test_cli.py` invoking the CLI with `--skip-taxonomy`/`--force-embed` and asserting the underlying `import_seeds`/`import_bundled_seed` call actually received those kwargs (e.g. via a spy/monkeypatch), so a future argparse-wiring typo is caught at the CLI layer, not just the function layer.

**Exit:** each listed test asserts the specific behavior in its own name/docstring, not a weaker proxy for it.

---

## Order & effort

Part A (T1–T4) first, together — they're the same class of bug and block/allow decisions aren't trustworthy until all four land. Part B (T5–T10) can run in parallel, independent of each other and of Part A. Part C (T11) last, once the behaviors it's testing are actually fixed.

Rough estimate: T1: 1–2d (real work if option (a); half a day if option (b)) · T2: 1h · T3: 3–4h · T4: 3–4h · T5: 4–6h · T6: 1h · T7: 1–2h · T8: 2–3h · T9: 1h · T10: 1–2h · T11: 3–4h.

## Return format (`handoffbackBug1.md`)

Per task: the regression test added (name + the exact assertion) · confirmation it fails on the pre-fix code and passes post-fix (paste both `pytest` outputs, not just the final green run) · for T1, state explicitly which option (a or b) was chosen and why · for T6, the actual resolved `prismrag-patch` version after the pin fix and confirmation its real API matches `taxonomy/mapping.py`'s imports · full `pytest -q` output at the end · anything blocked, stated plainly. No commits unless the Director asks.

---
*Bug1 · Part A fixes the calibration math that currently makes fusion_block unreachable and the benign fast-path invertible — nothing else in this handoff matters if those four don't land together · Part B and C are independent and parallelizable.*
