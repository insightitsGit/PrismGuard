# PrismGuard production integration guide

## Choose your integration path

| Path | When | Tier |
|------|------|------|
| **Library** (`create_checker_for_app`) | Python agent in-process | OSS |
| **HTTP sidecar** (`prismguard serve`) | Polyglot or microservice deploy | Business |
| **ChorusGraph node** (`integrations.chorusgraph`) | ChorusGraph-native graphs | OSS |

Examples + do/don’t: [`examples/README.md`](../examples/README.md) · [`best-practices.md`](best-practices.md) · compare: `python scripts/compare_profiles.py`

## Profiles and env contract (Dogfood1)

| Profile / env | Behavior |
|---------------|----------|
| `create_checker_for_app("web_chat")` | Rules + structural, HashEmbedder, **no ONNX**, fail-open gray — **hub/FAQ; not the scorecard path** |
| `create_checker_for_app("law_pilot")` | Law domain pack; ONNX if `PRISMGUARD_USE_ONNX=1` or `use_onnx=True`. **Only profile that builds prismrag taxonomy** when `[prism]` is installed |
| `create_checker_for_app("heavy")` / `"security_bench"` | **Heavy ONNX** — always-on (`first`). Scorecard / max coverage; ~350–500 ms. Loud if weights missing |
| `create_checker_for_app("light")` / `"low_latency"` | **Light ONNX** — selective (`hybrid`). Production/stack latency; rules/structural first. Loud if weights missing |
| `create_checker_for_app("sidecar")` | HTTP-oriented; HashEmbedder by default; ONNX opt-in |
| `PRISMGUARD_USE_ONNX=1` | **Opt-in** ONNX enforce (default: off). Loads `prism-pi-v1` unless overridden |
| `PRISMGUARD_CLASSIFIER_MODE` | Override: `first` \| `hybrid` \| `parallel` \| `gray_only` |
| `PRISMGUARD_ORT_PROVIDERS` | Optional ORT providers (e.g. `CUDAExecutionProvider,CPUExecutionProvider`) |
| `PRISMGUARD_ORT_INTRA_THREADS` | ORT intra-op threads (default `min(4, cpu_count)`) |

### Heavy vs light ONNX

| | Light (`light`) | Heavy (`heavy`) |
|--|-----------------|-----------------|
| Benefit | Fast path when rules/structural win; better p50 for agents | Classifier sees every prompt; best for soft paraphrases + scorecard claims |
| Tradeoff | Relies on Tier-1/structural coverage for short-circuits | Pays ONNX latency on easy prompts too |
| Pick for | Production UX, PrismShine stacks | Security benches, holdout methodology |

Both require the same `prismguard-model download`. Neither enables prismrag taxonomy — use `law_pilot`+`[prism]` for learn-from-seed.

| `PRISMGUARD_ARTIFACT_ID` | **Opt-in** artifact id (default: triage/`prism-pi-v1`). Use `prism-pi-hub-v1` after hub gates |
| `PRISMGUARD_GUARD_MODEL_PATH` | **Opt-in** absolute artifact dir (overrides id) |
| `PRISMGUARD_SHADOW_ONNX=1` | Rules enforce; ONNX verdict in `details["shadow_onnx"]` only |
| `PRISMGUARD_FEEDBACK_PERSIST=1` | **Opt-in** feedback queue for pilot training (default: off) |
| `PRISMGUARD_TENANT_LEXICON_PATH` | Optional customer entity words / severity boosts |
| `PRISMGUARD_STORAGE_BACKEND` | `memory` (OSS default) or `pgvector` / `chroma` / … (**Team+** license) |
| `PRISMGUARD_STORAGE_DSN` | DSN for pgvector (Team+) |
| `PRISMGUARD_OFFLINE=1` | Skip HF / transformer taxonomy; HashEmbedder |
| `PRISMGUARD_DOMAIN` | Unset / `general` / `core` → **no law overlay**. Set `law` for legal pack. |

**Defaults stay safe:** rules-first, ONNX off, law artifact only if you opt in.  
**`prism-pi-v1` is law-bench proof.** Hub/FAQ chat needs a hub/customer artifact + green gates before enforce.

**Without `[prism]`:** seed overlay text can still be stored, but **taxonomy / word-graph is skipped**. Do not claim “learns from your corpus” on that path.

```bash
prismguard caps --profile law_pilot   # onnx_ready, prismrag_taxonomy, feedback_persist, …
```

### Core rules vs domain pack vs holdout

| Layer | What it is | When loaded |
|-------|------------|-------------|
| **Core rules** | Bundled authored seed (`seed.yaml`) + structural heuristics | Always |
| **Domain pack** | Overlay under `prismguard/domains/<name>/` (entries + optional triage) | Only when `PRISMGUARD_DOMAIN=<name>` or `law_pilot` |
| **Holdout** | Eval-only YAML (`holdout.yaml`) | Never seeded into runtime; used by eval/benchmarks |

## Library (recommended for hubs)

```python
from prismguard.runtime.factory import create_checker_for_app
from prismguard.runtime.output_scan import scan_output

checker = create_checker_for_app("web_chat")  # dogfood-safe default
result = checker.check(user_prompt, session_id=session_id)
if result.decision == "block":
    return reject(result.resolution_gate, result.details)

answer = agent.generate(user_prompt)
scan = scan_output(answer)
if scan.decision == "block":
    return reject("output_scan", scan.details)

# Optional observability
print(checker.metrics_snapshot())
```

**Log for compliance:** `decision`, `resolution_gate`, `matched_category`, `details.decision_source`.

## HTTP sidecar (Business license)

```bash
export PRISMGUARD_LICENSE_FILE=/path/to/license.json
# Optional: law pack for legal pilots
# export PRISMGUARD_DOMAIN=law
# export PRISMGUARD_USE_ONNX=1   # only after hub/law calibration
export PRISMGUARD_STORAGE_BACKEND=memory
prismguard-serve
```

```http
POST /v1/check
{"text": "user prompt here"}

POST /v1/scan-output
{"text": "model response here"}
```

Health: `GET /health`, `GET /ready`.

## ChorusGraph

### Hub / FAQ (fail-open gray)

```python
from prismguard.integrations.chorusgraph import (
    create_checker_for_app,
    make_guard_handler,
    route_after_guard,
)

checker = create_checker_for_app("web_chat")
# Gray continues unless you pass block_on=frozenset({"block", "gray"})
guard_node = make_guard_handler(checker)
# graph.add_node("guard", guard_node)
# graph.add_conditional_edges("guard", route_after_guard, {"end": END, "continue": "retrieve"})
```

See `examples/chorusgraph_hub_guard.py`.

### Law / scorecard path (block + gray)

```python
from prismguard.integrations.chorusgraph import (
    create_checker_for_app,
    make_guard_handler,
    route_after_guard,
)

checker = create_checker_for_app("light")   # or "heavy" for always-on ONNX
guard = make_guard_handler(checker, block_on=frozenset({"block", "gray"}))
# START → guard → [end | retrieve…]  BEFORE cache hops
```

See `examples/chorusgraph_law_guard.py`. Measure: `python scripts/latency_by_gate.py --profile light`.

**Order:** guard **before** cache-gated hops so unsafe prompts are not replayed from cache.

Future: `GuardBackend` port on `ChorusStack` (ChorusGraph enterprise) — same checker, scheduler-invoked.

## Learn from seed / words / DB

Single recipe for the marketing “learns from your words / DB” story:

```text
seed YAML / domain overlay  →  storage (memory = OSS, or Team+ DB)
tenant lexicon (optional)   →  severity / force-classifier
feedback persist            →  export JSONL → corpus-plan → train → artifact
                            →  PRISMGUARD_GUARD_MODEL_PATH / PRISMGUARD_ARTIFACT_ID
```

| Step | How | Tier |
|------|-----|------|
| Install taxonomy stack | `pip install "prismguard[guard-model,prism]"` | OSS |
| Factory | `create_checker_for_app("law_pilot", use_onnx=True)` — **not** `security_bench` | OSS |
| Domain words | `PRISMGUARD_DOMAIN=law` (implied by `law_pilot`) | OSS |
| ONNX | `prismguard-model download` + `PRISMGUARD_USE_ONNX=1` | OSS |
| Feedback | `PRISMGUARD_FEEDBACK_PERSIST=1` → `prismguard feedback export` → `prismguard-model train` | OSS |
| Persistent DB seed/feedback | `PRISMGUARD_STORAGE_BACKEND=pgvector` + `PRISMGUARD_STORAGE_DSN` + license | **Team+** |
| Tenant lexicon | `PRISMGUARD_TENANT_LEXICON_PATH=/path/to/lexicon.yaml` | path OSS / production **Business+** |

**Never** label memory-only + rules-only as “learns from your DB.”  
Verify: `prismguard caps --profile law_pilot` → `prismrag_taxonomy`, `feedback_persist`, `storage_backend`.

## Customer / hub ONNX path (opt-in)

Seed import updates **rules**, not ONNX weights. To turn ONNX on for *your* traffic:

```bash
# 1) Pilot: rules enforce + optional shadow (defaults)
export PRISMGUARD_SHADOW_ONNX=1          # opt-in
export PRISMGUARD_FEEDBACK_PERSIST=1     # opt-in

# 2) After human review of the queue:
prismguard feedback export -o customer.jsonl
# optional: --include-calibration-allows

# 3) Plan (no train) — domain pack is opt-in (default: none)
prismguard-model corpus-plan --profile full --feedback-jsonl customer.jsonl

# 4) Train customer or hub artifact (opt-in --domain-pack)
prismguard-model train --profile full --feedback-jsonl customer.jsonl \
  --domain-pack general --holdout-domain general \
  --normal-txt benchmark/hub/benign_faq.txt \
  --artifact-id customer-pi-v1 --output-dir ./artifacts/customer-pi-v1

# 5) Gate
prismguard-model eval --domain general --artifact-path ./artifacts/customer-pi-v1 \
  --normal-txt benchmark/hub/benign_faq.txt

# 6) Enforce only after gates pass
export PRISMGUARD_USE_ONNX=1
export PRISMGUARD_GUARD_MODEL_PATH=./artifacts/customer-pi-v1
```

Hub maintainer shortcut: `python scripts/train_prism_pi_hub.py` (builds `prism-pi-hub-v1`).

## Production standards checklist

- [ ] Prefer `create_checker_for_app("web_chat")` for product hubs; use `law_pilot` for legal / learn-from-seed
- [ ] Run `prismguard caps` and confirm capabilities match the claim (scorecard vs learn vs hub)
- [ ] Keep `PRISMGUARD_USE_ONNX` unset until hub/customer FAQ FP gate is green
- [ ] Install `[prism]` before claiming word-graph / learn-from-seed
- [ ] Run `python scripts/adversarial_self_check.py` before each release (law bench)
- [ ] Cite **cold holdout** metrics only externally (not seeded dev set)
- [ ] Wire **output scan** on every model response
- [ ] Persist audit logs: `resolution_gate` + timestamp + request id
- [ ] Do not use `PRISMGUARD_DEV_UNRESTRICTED` in production
- [ ] Team tier: pgvector + `PRISMGUARD_STORAGE_DSN` for persistent feedback seed

## ChorusGraph + PrismGuard bundle (enterprise sales)

Sell as **complementary SKUs**:

- ChorusGraph enterprise → orchestration + Postgres persistence
- PrismGuard business → guard sidecar or embedded checker
- Bundle discount optional; keep separate licenses for clean procurement

See [enterprise-product-model.md](enterprise-product-model.md).
