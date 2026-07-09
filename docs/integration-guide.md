# PrismGuard production integration guide

## Choose your integration path

| Path | When | Tier |
|------|------|------|
| **Library** (`RuntimeChecker`) | Python agent in-process | OSS |
| **HTTP sidecar** (`prismguard serve`) | Polyglot or microservice deploy | Business |
| **ChorusGraph node** (`integrations.chorusgraph`) | ChorusGraph-native graphs | OSS |

## Library (recommended for pilots)

```python
from prismguard.runtime.check import RuntimeChecker
from prismguard.runtime.output_scan import scan_output

result = checker.check(user_prompt, session_id=session_id)
if result.decision == "block":
    return reject(result.resolution_gate, result.details)

answer = agent.generate(user_prompt)
scan = scan_output(answer)
if scan.decision == "block":
    return reject("output_scan", scan.details)
```

**Log for compliance:** `decision`, `resolution_gate`, `matched_category`, `details.decision_source`.

## HTTP sidecar (Business license)

```bash
export PRISMGUARD_LICENSE_FILE=/path/to/license.json
export PRISMGUARD_DOMAIN=law
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
from prismguard.integrations.chorusgraph import make_guard_handler, route_after_guard

guard_node = make_guard_handler(checker)
# graph.add_node("guard", guard_node)
# graph.add_conditional_edges("guard", route_after_guard, {"end": END, "continue": "retrieve"})
```

**Order:** guard **before** cache-gated hops so unsafe prompts are not replayed from cache.

Future: `GuardBackend` port on `ChorusStack` (ChorusGraph enterprise) — same checker, scheduler-invoked.

## Production standards checklist

- [ ] Run `python scripts/adversarial_self_check.py` before each release
- [ ] Cite **cold holdout** metrics only externally (not seeded dev set)
- [ ] Set `PRISMGUARD_DOMAIN=law` until other domains are benchmarked
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
