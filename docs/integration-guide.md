# PrismGuard production integration guide

## Choose your integration path

| Path | When | Tier |
|------|------|------|
| **Library** (`create_checker_for_app`) | Python agent in-process | OSS |
| **HTTP sidecar** (`prismguard serve`) | Polyglot or microservice deploy | Business |
| **ChorusGraph node** (`integrations.chorusgraph`) | ChorusGraph-native graphs | OSS |

## Profiles and env contract (Dogfood1)

| Profile / env | Behavior |
|---------------|----------|
| `create_checker_for_app("web_chat")` | Rules + structural, HashEmbedder, **no ONNX**, fail-open gray |
| `create_checker_for_app("law_pilot")` | Law domain pack; ONNX only if `PRISMGUARD_USE_ONNX=1` |
| `create_checker_for_app("sidecar")` | HTTP-oriented; same ONNX opt-in |
| `PRISMGUARD_USE_ONNX=1` | Explicit opt-in to load `prism-pi-v1` (breaking vs older surprise-ONNX) |
| `PRISMGUARD_SHADOW_ONNX=1` | Rules enforce; ONNX verdict in `details["shadow_onnx"]` only |
| `PRISMGUARD_OFFLINE=1` | Skip HF / transformer taxonomy; HashEmbedder |
| `PRISMGUARD_DOMAIN` | Unset / `general` / `core` → **no law overlay**. Set `law` for legal pack. |

**`prism-pi-v1` is law-bench-oriented.** Do not enable ONNX enforce on general product FAQ / hub chat until the hub benign FAQ suite passes (see `tests/test_hub_benign_faq.py` and `benchmark/hub/`).

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

**Order:** guard **before** cache-gated hops so unsafe prompts are not replayed from cache.

See `examples/chorusgraph_hub_guard.py` for a fail-open hub sketch (guard → RAG → cache → LLM).

Future: `GuardBackend` port on `ChorusStack` (ChorusGraph enterprise) — same checker, scheduler-invoked.

## Production standards checklist

- [ ] Prefer `create_checker_for_app("web_chat")` for product hubs; use `law_pilot` only for legal pilots
- [ ] Keep `PRISMGUARD_USE_ONNX` unset until hub FAQ FP gate is green
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
