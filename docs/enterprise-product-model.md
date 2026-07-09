# PrismGuard — Enterprise product model

**Strategy:** PrismGuard is **independently sellable** (like PrismCortex) **and** a **first-class plugin** for ChorusGraph enterprise stacks. Same open-core pattern as the rest of the Prism family.

## Two go-to-market motions

| Motion | Buyer | What they buy |
|--------|-------|----------------|
| **Standalone PrismGuard** | Compliance / security team embedding guardrails in any agent stack | Audited ONNX firewall library + optional HTTP sidecar |
| **ChorusGraph + PrismGuard** | Platform team standardizing on ChorusGraph | Native guard node / future `GuardBackend` port on `ChorusStack` |

ChorusGraph remains the **orchestration** product (LangGraph-like, enterprise Postgres persistence). PrismGuard remains the **security** product (classifier + rules + audit gates). Do not bundle pricing — cross-sell, don't collapse.

## Tier matrix (mirrors PrismCortex / ChorusGraph)

| SKU | Price (pre-validation) | Audience | Included |
|-----|------------------------|----------|----------|
| **prismguard** (OSS) | $0 | Developers | `RuntimeChecker`, ONNX `prism-pi-v1`, structural rules, heuristic Judge, memory storage, `prismguard doctor`, law domain pack, ChorusGraph guard node helper |
| **prismguard-team** | ~$199/mo | Small teams | pgvector persistence, feedback review persistence, calibration exports, email support |
| **prismguard-business** | ~$699/mo | Production deployments | HTTP guard service (`prismguard serve`), OpenAI Judge option, tenant lexicon runtime, session Redis hooks, OTel metrics on `/metrics` |
| **prismguard-pilot** | ~$25k one-time | Enterprise design partner | Custom lexicon onboarding, security review pack, SLA, ChorusGraph co-integration, named customer success |

> Prices are Director estimates — not customer-validated. See `handoffs/handoffLandingPage.md` Part A.

## Open core vs paid gates (code)

| Feature | OSS | Team+ | Business+ |
|---------|-----|-------|-----------|
| `RuntimeChecker.check()` | yes | yes | yes |
| `scan_output()` | yes | yes | yes |
| `integrations.chorusgraph` guard node | yes | yes | yes |
| pgvector / persistent seed | — | license | license |
| `prismguard serve` HTTP API | — | — | license |
| Tenant context production | — | — | license |
| Signed offline license file | — | required | required |

License env: `PRISMGUARD_LICENSE_FILE` (signed Ed25519 JSON — same issuer pattern as `CHORUSGRAPH_LICENSE_FILE`). Verify with `pip install prismguard[enterprise]`.

Dev override: `PRISMGUARD_DEV_UNRESTRICTED=1` (local only — never in production docs).

### Production license key gate (Business / Enterprise)

**Do not issue real customer licenses against the current embedded key.**  
`prismguard/licensing/keys.py` ships a **development / CI** Ed25519 public key shared with ChorusGraph (`_LICENSE_PUBLIC_KEY_B64`). That key is intentionally public (verification only); it is **not** a production issuer.

Before any paid Team / Business / Pilot license is sold or signed:

1. Director (or designated security owner) generates a **new** Ed25519 keypair used only for PrismGuard customer licenses.
2. The **private** half is held in a secure issuer store (not in git, not shared with the ChorusGraph dev/CI key).
3. `_LICENSE_PUBLIC_KEY_B64` in `keys.py` is updated to the **production public** key and released in a versioned package.
4. Customer license files are signed with that production private key only.

Until those steps are done, signed licenses are for **dev/CI/demo** only. Code already supports the swap via `license_public_key_bytes()` — this is a business-process gate, not a missing feature.

Customer updates (pip / seed / model — **not** holdout import): see [`user-updates.md`](user-updates.md). Post-install verify: `prismguard eval self-check`.

## Honest positioning (all channels)

**Say:** cheaper + audited — every decision exposes `resolution_gate` and `decision_source` for compliance logs; ONNX path ~200ms; selective Judge escalation.

**Do not say:** beats LLM Guard on detection; healthcare/finance supported; enterprise-ready without pilot.

## ChorusGraph compatibility plan

| Phase | Deliverable | Repo |
|-------|-------------|------|
| **Now** | `prismguard.integrations.chorusgraph.make_guard_handler()` — drop-in graph node | PrismGuard |
| **Next** | ChorusGraph v2 documents PrismGuard as recommended guard; example graph in ChorusGraph `examples/` | ChorusGraph |
| **Enterprise** | Optional `GuardBackend` port on `ChorusStack` (6th port, parallel to retrieval) | ChorusGraph + PrismGuard adapter |

PrismGuard benchmark CPL today is a **linear pipeline mirror**, not a native `chorusgraph` import. The integration module closes that gap for customers without waiting for a ChorusGraph release.

## Production readiness checklist

| Layer | Status | Owner |
|-------|--------|-------|
| Detection (law cold holdout) | green — `adversarial_self_check.py` | PrismGuard |
| Business model + SKU gates | this doc + `prismguard/licensing/` | PrismGuard |
| HTTP guard service | `prismguard serve` | PrismGuard |
| ChorusGraph guard node | `prismguard/integrations/chorusgraph.py` | PrismGuard |
| Integration guide | `docs/integration-guide.md` | PrismGuard |
| Landing page + pricing JS | `handoffs/handoffLandingPage.md` | InsightitsAIAgent |
| Customer discovery | open | GTM |
| Classifier retrain (reduce heuristics) | open | PrismGuard ML |
| ChorusGraph GuardBackend port | planned | ChorusGraph |

## Related docs

- [law-pilot-readiness.md](law-pilot-readiness.md) — technical gate before external claims
- [prismguard-design.md](prismguard-design.md) — architecture
- [integration-guide.md](integration-guide.md) — how to embed in production
