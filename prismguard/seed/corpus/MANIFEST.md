# Seed Manifest

What's in this folder, where it came from, its license, and what still needs to happen before it's fully imported. Fetched/verified 2026-07-06 directly from each source's Hugging Face API metadata (license, row counts, schema) — not from memory or the earlier research pass.

---

## `authored/` — ours, no license restriction

**`seed.yaml`** — the v0 taxonomy (10 categories, bridges), 5 starter Tier-1 rules, and ~24 hand-written examples from `docs/prismguard-design.md` Part 5/6. Written by the design team specifically for this product — safe to import, modify, and redistribute without any external license concern.

```
prismguard-seed import prismguard/seed/corpus/authored/seed.yaml --format yaml --mode update
```

---

## `external/` — real datasets, license-checked, downloaded 2026-07-06

| Source | License | Rows | Format | Schema |
|---|---|---|---|---|
| [S-Labs/prompt-injection-dataset](https://huggingface.co/datasets/S-Labs/prompt-injection-dataset) | **MIT** | 11,091 train / 2,101 val / 2,101 test | CSV | `text, label` (binary: 0=benign, 1=injection) |
| [neuralchemy/Prompt-injection-dataset](https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset) (`core` config) | **Apache-2.0** | 4,391 train / 941 val / 942 test | Parquet | `text, label, category, severity, group_id, augmented, tags` |
| [yanismiraoui/prompt_injections](https://huggingface.co/datasets/yanismiraoui/prompt_injections) | **Apache-2.0** | 1,034 | CSV | single column, multilingual attack text, no labels |

All three are safe for a commercial product under their stated licenses (verify no downstream terms changed since 2026-07-06 before a production release).

### neuralchemy → PrismGuard category mapping (best schema match — do this one first)

This dataset already ships `category` and `severity` columns, so it needs a **rename**, not manual re-labeling:

| neuralchemy `category` | → PrismGuard `category_slug` |
|---|---|
| `direct_injection` | `direct_instruction_override` |
| `jailbreak`, `persona_replacement` | `roleplay_jailbreak` |
| `system_extraction`, `prompt_leaking` | `system_prompt_exfiltration` |
| `encoding_obfuscation`, `token_smuggling` | `encoding_obfuscation` |
| `crescendo`, `many_shot` | `multi_turn_escalation` |
| `indirect_injection` | `indirect_injection` |
| `benign` | `benign_adjacent` |
| `context_overflow` | **no current mapping — see Gaps below** |

`severity` values (`low/medium/high/critical`) map directly, no transform needed. `label` (0/1) is redundant once `category_slug` is set but useful as a sanity check during import validation.

### S-Labs and yanismiraoui → require re-categorization

Neither ships a `category` field — S-Labs is binary (benign/injection) only, yanismiraoui is unlabeled attack text. Import these as `category_slug: unclassified_imported` (a staging category, not a real taxonomy category — add it as `is_attack_category: null` so the runtime never triages against it directly) and route through the Tier-1 rule set for auto-assignment, then human-review whatever the rules don't confidently classify. Don't bulk-assign these to a real attack category without that pass — that's exactly the kind of ungrounded taxonomy write the design doc's anti-poisoning principle (Part 8) warns against, even though this is pre-launch seed data rather than live feedback.

---

## Deliberately NOT downloaded — read before deciding whether to revisit

| Source | Why it's not here |
|---|---|
| [Necent/llm-jailbreak-prompt-injection-dataset](https://huggingface.co/datasets/Necent/llm-jailbreak-prompt-injection-dataset) | MIT-licensed and aggregates 30+ safety datasets, but **1.01 GB** across 4 parquet shards — too large to pull wholesale into a git repo without a real reason. If you want this one, sample it via the `datasets` library's streaming mode (`load_dataset(..., streaming=True)`) and pull a bounded subset rather than the full file — don't just re-run the curl commands used for the others. |
| [Mindgard/evaded-prompt-injection-and-jailbreak-samples](https://huggingface.co/datasets/Mindgard/evaded-prompt-injection-and-jailbreak-samples) | **Gated** — its data file requires an authenticated, approved Hugging Face account (the metadata page is public, the actual parquet is not). It is also **CC-BY-NC-4.0** — non-commercial — so even after gaining access, it cannot be used to seed a commercial product's corpus without a separate license from Mindgard. Useful only as an internal/research-only test set for evaluating graph-expansion coverage against adversarially-evaded samples (its actual purpose per its paper), never as shipped training/seed data. |
| [JailbreakBench (JBB-Behaviors)](https://arxiv.org/pdf/2410.22770) | Not fetched as seed data on purpose — per `docs/prismguard-design.md` Part 10 (T10), this belongs in the **held-out benchmark set**, not the training/seed corpus, so thresholds aren't tuned on the same data used to evaluate them. |

---

## Taxonomy gaps these sources don't cover

Confirmed by actually reading each dataset's category list, not assumed:

- **`payload_splitting`** — no source here represents cross-message split attacks. Single-message datasets can't capture this by construction.
- **`data_exfiltration_via_output`** — none of the three imported sources have this as a labeled category.
- **`refusal_suppression`** — not a distinct label in any source; may be present as unlabeled text within `direct_injection`/`jailbreak` rows but not extractable without re-reading each row.
- **`context_overflow`** (neuralchemy has this, PrismGuard's taxonomy doesn't) — worth a decision: add it as an 11th category, or fold it into `encoding_obfuscation`/`payload_splitting` as a sub-case. Flagging rather than deciding here.

These four categories still need hand-authored or red-team-sourced examples beyond what's in `authored/seed.yaml` — the public datasets are strongest on single-message direct/jailbreak/exfiltration attacks and weak on everything structural or cross-turn.

---

## Next step

Run the importer (once built per `handoffs/handoffPrismGuardImplementation.md` Part B) in this order: `authored/seed.yaml` first (defines the categories everything else references), then `external/neuralchemy/*` (best schema match), then `external/s-labs/*` and `external/yanismiraoui/*` staged into `unclassified_imported` pending the rule-based/human-reviewed re-categorization pass described above.
