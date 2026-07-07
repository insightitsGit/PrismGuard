# Seed Manifest

What's in this folder, where it came from, its license, and import behavior. Verified 2026-07-06 against each source's Hugging Face metadata.

---

## Two-layer gap fix (seed content + importer code)

The four taxonomy gaps were addressed at **two layers** that complement each other:

| Gap | Seed-content layer (`authored/seed.yaml`) | Code layer (`prismguard/seed/formats/`) |
|---|---|---|
| **`refusal_suppression`** | 7 rows **mined** from `external/s-labs/train.csv` malicious hits (`source: mined-slabs`), with `notes` flagging co-occurring categories (multi-label TBD) | `slabs_csv.py` heuristic re-labels matching `label=1` rows at import |
| **`context_overflow`** | Added as its own category (not folded into neighbors); bridged to `encoding_obfuscation` + `payload_splitting` | `neuralchemy_parquet.py` maps `context_confusion` → `context_overflow` |
| **`payload_splitting`** | `turns: [msg1, msg2]` entries document the real attack shape; single-text rows kept as approximations only | `EntrySeed.turns` + `canonical_text()` in `models.py`; `neuralchemy` `payload_injection` mapping; S-Labs split heuristic |
| **`data_exfiltration_via_output`** | Category `description` states this is an **output-scan** problem, not solvable by input examples alone | `neuralchemy` `output_manipulation`/`response_manipulation` mapping; S-Labs exfil heuristic for input-side instruct-to-leak prompts |

---

## `authored/` — ours, no license restriction

**`seed.yaml`** — taxonomy (12 categories including `context_overflow` and `unclassified_imported`), Tier-1 rules, hand-written examples, and multi-turn `turns` entries for `payload_splitting`.

```
prismguard-seed import prismguard/seed/corpus/authored/seed.yaml --format yaml --mode update
```

---

## `external/` — real datasets, license-checked

| Source | License | Rows | Format | Import handler |
|---|---|---|---|---|
| [neuralchemy/Prompt-injection-dataset](https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset) (`core`) | **Apache-2.0** | 4,391 / 941 / 942 | Parquet | `neuralchemy_parquet.py` |
| [S-Labs/prompt-injection-dataset](https://huggingface.co/datasets/S-Labs/prompt-injection-dataset) | **MIT** | 11,091 / 2,101 / 2,101 | CSV | `slabs_csv.py` + heuristic re-label |
| [yanismiraoui/prompt_injections](https://huggingface.co/datasets/yanismiraoui/prompt_injections) | **Apache-2.0** | 1,034 | CSV | `yanismiraoui_csv.py` |

Requires `pip install prismguard[seed]` (pulls `pyarrow` for parquet).

### neuralchemy → PrismGuard mapping (implemented)

| neuralchemy `category` | PrismGuard `category_slug` |
|---|---|
| `direct_injection`, `instruction_override`, `prompt_injection`, `system_manipulation` | `direct_instruction_override` |
| `jailbreak`, `persona_replacement` | `roleplay_jailbreak` |
| `system_extraction`, `prompt_extraction`, `training_extraction`, `model_fingerprinting` | `system_prompt_exfiltration` |
| `encoding`, `encoding_obfuscation`, `token_smuggling`, `token_injection` | `encoding_obfuscation` |
| `crescendo`, `many_shot`, `multi_turn` | `multi_turn_escalation` |
| `indirect_injection`, `rag_poisoning`, `agent_manipulation` | `indirect_injection` |
| `context_confusion` | **`context_overflow`** (added to taxonomy) |
| `output_manipulation`, `response_manipulation` | **`data_exfiltration_via_output`** |
| `payload_injection` | **`payload_splitting`** |
| `benign` | `benign_adjacent` |
| `adversarial`, `edge_case`, `control`, `code_execution`, `chain_of_thought` | `unclassified_imported` (staging) |

### S-Labs heuristic re-label (implemented)

Binary `label=1` rows are re-scanned before staging:

| Heuristic | → category |
|---|---|
| refusal-suppression phrasing (`must comply`, `never refuse`, …) | `refusal_suppression` |
| output-channel exfil phrasing (`markdown image`, `base64` in response, …) | `data_exfiltration_via_output` |
| split-payload phrasing (`part N of`, `execute X`, …) | `payload_splitting` |
| otherwise | `unclassified_imported` |

### yanismiraoui

Unlabeled multilingual attacks → `unclassified_imported` (no category column to trust).

---

## Taxonomy gaps — status after fix (2026-07-06)

| Gap | Resolution |
|---|---|
| **`context_overflow`** | Added to taxonomy; neuralchemy `context_confusion` rows map here |
| **`data_exfiltration_via_output`** | neuralchemy `output_manipulation` / `response_manipulation` + S-Labs heuristic + authored examples. **Note:** category also needs an output-side runtime scan — input pipeline alone is insufficient for production |
| **`refusal_suppression`** | S-Labs heuristic + authored/mined examples; not a distinct label in external datasets |
| **`payload_splitting`** | neuralchemy `payload_injection` + S-Labs heuristic + authored `turns` entries (multi-turn schema). Session-level runtime detection still required for production |

No public dataset fully represents cross-turn split attacks by construction — `turns` entries and session runtime (handoff Part D, T8b) cover what single-field imports cannot.

---

## Import order (`manifest.txt`)

```
authored/seed.yaml
external/neuralchemy/core-{train,validation,test}.parquet
external/s-labs/{train,validation,test}.csv
external/yanismiraoui/prompt_injections.csv
```

```bash
prismguard-seed import --bundled --profile full   # requires prismguard[seed]
```

---

## Deliberately NOT bundled

| Source | Why |
|---|---|
| Necent (1 GB) | Too large — stream a bounded subset if needed |
| Mindgard | Gated + **CC-BY-NC-4.0** (non-commercial) |
| JailbreakBench | Held-out benchmark only (design doc Part 10) |
