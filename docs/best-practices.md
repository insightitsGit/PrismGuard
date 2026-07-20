# PrismGuard best practices

Companion to the README [Pick your features](../README.md#pick-your-features) table and runnable [`examples/`](../examples/).

## Decision tree

```text
Hub / FAQ / marketing chat?
  └─ yes → web_chat (#1)
           optional: shadow ONNX (#7) before enforcing

Need local ONNX injection classifier?
  ├─ Production / agent UX latency → light (#2)
  └─ Scorecard / never-skip-model   → heavy (#3)

Claim "learns from corpus / our words"?
  └─ law_pilot + [prism] + FEEDBACK_PERSIST (#5–#6)
     DB persistence → Team+ (#9)

ChorusGraph / agent graph?
  └─ guard node BEFORE cache/RAG (#10); pick light or heavy above
```

## Practices by option

### #1 Hub — `web_chat`

**Do**
- Use for product FAQ and low-FP chat.
- Log `resolution_gate` on every decision.
- Pair with output scan (#12) on model responses.

**Don’t**
- Cite law scorecard / COMPARISON_REPORT numbers from this path.
- Force `PRISMGUARD_USE_ONNX=1` with `prism-pi-v1` on hub FAQ until a hub artifact passes gates.

**Example:** [`examples/01_hub_web_chat.py`](../examples/01_hub_web_chat.py)

### #2 Light ONNX — `light` / `low_latency`

**Do**
- Default for PrismShine / production agents once weights are downloaded.
- Keep Tier-1 + structural rules strong (they create the fast path).
- Measure with `python scripts/latency_by_gate.py --profile light`.
- Compare quality with `python scripts/compare_profiles.py`.

**Don’t**
- Expect identical recall to `heavy` on soft paraphrases.
- Claim learn-from-seed taxonomy (HashEmbedder / skip_taxonomy).

**Example:** [`examples/02_light_onnx.py`](../examples/02_light_onnx.py)

### #3 Heavy ONNX — `heavy` / `security_bench`

**Do**
- Use for security benches and published holdout methodology.
- Budget ~350–500 ms mean when ONNX runs every request.
- Fail loud if `model.onnx` missing (by design).

**Don’t**
- Use as the only production profile if p50 UX matters — prefer `light` unless policy requires always-on ONNX.
- Skip measuring benign allow rate (false positives still matter).

**Example:** [`examples/03_heavy_onnx.py`](../examples/03_heavy_onnx.py)

### #5–#6 Learn-from-seed

**Do**
- Install `prismguard[guard-model,prism]`.
- Use `law_pilot` + `use_onnx=True` (not `light`/`heavy`).
- Set `PRISMGUARD_FEEDBACK_PERSIST=1`, review queue, then export → train.
- Verify `prismguard caps --profile law_pilot` shows `prismrag_taxonomy: True`.

**Don’t**
- Market “learns from your DB” on memory-only installs without Team+ storage (#9).
- Import holdout YAML into production seed.

**Example:** [`examples/04_learn_from_seed.py`](../examples/04_learn_from_seed.py)

### #7 Shadow ONNX

**Do**
- Run beside `web_chat` to estimate would-block rate on real FAQ traffic.
- Promote to enforce only after FP gate is green + matching artifact id.

**Example:** [`examples/05_shadow_onnx.py`](../examples/05_shadow_onnx.py)

### #10 ChorusGraph

**Do**
- Place guard **before** cache-gated hops.
- Hub: `block_on={"block"}` (gray continues). Stack: often `{"block","gray"}`.
- Pick `light` for latency, `heavy` for max coverage.

**Examples:** [`chorusgraph_hub_guard.py`](../examples/chorusgraph_hub_guard.py), [`chorusgraph_law_guard.py`](../examples/chorusgraph_law_guard.py)

### #12 Output scan

**Do**
- Always scan model responses for exfil patterns in production.
- Treat as complementary to input `check()`, not a replacement.

**Example:** [`examples/06_output_scan.py`](../examples/06_output_scan.py)

### #13 Verify

```bash
prismguard caps --profile light|heavy|law_pilot|web_chat
python scripts/compare_profiles.py          # which profile wins on your machine
python scripts/s1_miss_analysis.py --profile light --attacks YOUR_SET
```

## Which is “best”?

There is no single winner — optimize for the goal:

| Goal | Prefer | Why |
|------|--------|-----|
| Lowest hub FP | `web_chat` | No law ONNX on FAQ |
| Best stack latency (near-top quality) | `light` | Hybrid skips ONNX on rule hits |
| Max attack block / scorecard parity | `heavy` | Always-on classifier (same F1 as light on many rule-heavy sets; higher mean latency) |
| Learn from customer words | `law_pilot`+`[prism]` | Taxonomy + feedback loop |

### Measured on this repo’s compare set (2026-07-20, local CPU)

Prompt set: 10 attacks + 8 benign in `scripts/compare_profiles.py` (warmup 2, repeat 3).

| profile | mode | attack block | benign allow | F1 | mean ms | p50 ms | p95 ms | ONNX invoke % |
|---------|------|--------------|--------------|-----|---------|--------|--------|---------------|
| `web_chat` | off | 0.80 | **1.00** | 0.889 | **0.1** | **0.1** | 0.2 | 0.0 |
| `light` | hybrid | **1.00** | 0.75 | **0.909** | **18.6** | **0.1** | 114 | **0.17** |
| `heavy` | first | **1.00** | 0.75 | **0.909** | 59.7 | 55.1 | 128 | 0.50 |

**Verdict for stacks:** prefer **`light`** — same attack block / F1 as `heavy` on this set, ~3× lower mean latency, much lower p50 and ONNX invoke rate.  
**Verdict for hubs:** prefer **`web_chat`** — perfect benign allow, sub-ms; accepts lower attack recall.  
**Use `heavy`** when policy requires always-on ONNX or you are matching scorecard methodology (not because it won F1 here).

**FP note:** `light`/`heavy` use law-oriented `prism-pi-v1` — short greetings like “Hi” may block (`guard_model_first`). That is why hub FAQ stays on `web_chat` (or shadow ONNX) until a hub artifact passes gates.

Re-run on your machine / your attacks:

```bash
python scripts/compare_profiles.py
python scripts/s1_miss_analysis.py --profile light --attacks YOUR_SET
```
