# Handoff Back — Bug1 (runtime triage + taxonomy fixes)

**Date:** 2026-07-07  
**Base commit reviewed:** `b86c6f4`  
**Tests:** `pytest -q` → **50 passed**

---

## T1 — Fusion formula missing terms (option **a** chosen)

**Choice:** Implemented minimal `graph_connectivity_score` (keyword overlap with category rules) and `community_routing_confidence` (1.0 when rule-matched category, 0.5 otherwise) and wired all six `triage.yaml` weights into `fuse_signals()`.

**Why not (b):** Option (a) keeps configured `block_threshold=0.78` meaningful without interim rescaling; graph/community stubs can be replaced by real BFS/routing later.

**Regression test:** `tests/test_bug1_runtime.py::test_fusion_max_score_can_reach_block_threshold`  
**Assertion:** `fuse_signals(attack_sim=1.0, rule_matched=True, severity="critical", graph_score=1.0, community_confidence=1.0, benign_sim=0.0).fused_score >= cfg.triage.block_threshold` (0.78)  
**Pre-fix:** max ~0.60 < 0.78 → would fail.

---

## T2 — Benign fast-path polarity

**Fix:** `margin <= -benign_margin_delta` (was `margin < benign_margin_delta`).

**Regression test:** `tests/test_bug1_runtime.py::test_benign_fast_path_requires_attack_below_benign`  
**Assertion:** with `benign_sim=0.75, attack_sim=0.80`, fast-path condition is false.

---

## T3 — Per-category threshold overrides

**Fix:** `resolve_thresholds()` in `prismguard/runtime/thresholds.py`; `check()` uses per-category `block_threshold`, `allow_threshold`, `benign_*`, and `corpus_match_override_threshold`. Hardcoded `0.92` removed — now `triage.corpus_match_override_threshold` in config.

**Regression test:** `tests/test_bug1_runtime.py::test_category_block_threshold_override_applied`  
**Assertion:** `fused_score=0.60` blocks when category `block_threshold=0.55` but global is `0.90`.

---

## T4 — Gray zone weak-signal gate

**Fix:** `route_fusion_decision()` requires `weak_signal_count >= min_weak_signals_for_gray` for gray; otherwise falls through to `allow`.

**Regression test:** `tests/test_bug1_runtime.py::test_single_weak_signal_routes_allow_not_gray`  
**Assertion:** `fused_score=0.55, weak_signal_count=1` → `allow` / `fusion_allow` (old code would gray).

---

## T5 — Category vector dimension + re-embed

**Fix:** `remap_category_vector()` falls back through augmented text → `project_sem_to_personal` → dim pool; `ingest.py` skips only when `len(embedding_category)==256`.

**Regression tests:**
- `test_category_vector_is_256d_without_whole_token_match`
- `test_corrupted_category_dim_reembedded_on_update_import`

---

## T6 — prismrag-patch pin

**Fix:** `pyproject.toml` → `prismrag-patch>=0.2.1,<1.0.0`

**Verified:** installed API imports `PrismRAGPatch`, `RulesStrategy`, `MappingConfig`, `project_sem_to_personal` — matches `taxonomy/mapping.py`.

---

## T7 — Embedded hex decode

**Fix:** `_HEX_EMBEDDED` regex search/replace (mirrors base64 branch).

**Regression test:** `test_normalize_embedded_hex_payload` — `0x68656c6c6f` → `hello` in output.

---

## T8 — Seed merge hash collision

**Fix:** Authored sources win over external with logged warning; equal-priority external duplicates → later source wins with warning (no silent overwrite).

**Regression test:** `test_merge_authored_wins_over_external_on_hash_collision`

---

## T9 — Substring word boundaries

**Fix:** `\b{word}\b` regex in `_substring_match_scores`.

**Regression test:** `test_substring_rule_respects_word_boundaries`

---

## T10 — Dead `content_changed` branch

**Fix:** Removed dead branch; comment explains hash-keyed lookup makes in-place content change unreachable.

---

## T11 — Test quality

- `test_import_runs_taxonomy_after_replace_scope` — asserts `taxonomy.ingest.embedded == 1`
- Renamed `test_data_exfil_category_description_documents_output_scan_gap`
- Tightened `test_turns_entries_import_with_canonical_hash` (exact counts + canonical join)
- Added `tests/test_cli.py` (skip-taxonomy / force-embed kwargs via monkeypatch)

---

## Files changed

```
prismguard/runtime/fusion.py, check.py, thresholds.py, normalize.py
prismguard/config/loader.py, triage.yaml
prismguard/taxonomy/constants.py, mapping.py, ingest.py
prismguard/taxonomy/pipeline.py, __init__.py  (circular import fixes)
prismguard/seed/merge.py, importer.py
pyproject.toml
tests/test_bug1_runtime.py, test_bug1_seed.py, test_cli.py
tests/test_bundled_seed.py, test_seed_import.py
```

---

## Full test output

```
pytest -q
50 passed in ~2.5s
```

---

## Blocked / not in scope

- Full graph BFS and multi-community routing (stubs remain heuristic)
- Output-side scan for `data_exfiltration_via_output`
- T9c calibration / T10 benchmark

No commit (Director did not request).
