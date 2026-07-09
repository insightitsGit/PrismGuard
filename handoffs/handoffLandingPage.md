# Handoff LandingPage — PrismGuard business model + product landing page

**Director:** Amin · **Architect:** Claude · **Engineer:** (receiving agent)
**Refs:** [`docs/enterprise-product-model.md`](../docs/enterprise-product-model.md) · [`docs/law-pilot-readiness.md`](../docs/law-pilot-readiness.md) · [`docs/integration-guide.md`](../docs/integration-guide.md) · `benchmark/law/results/current/` · **cross-repo:** landing page in `C:\code\InsightitsAIAgent`
**Date issued:** 2026-07-09 · **Updated:** 2026-07-09 (dual-product + production layers + user-update model)

---

## 0. Strategy (read before Part A)

PrismGuard is **two things at once**:

1. **Standalone product** — sellable like PrismCortex (open-core library + paid Team/Business/Enterprise SKUs).
2. **ChorusGraph plugin** — guard layer for the published enterprise runtime at `C:\code\ChorusGraph` (OSS guard node today; future `GuardBackend` port on `ChorusStack`).

**Do not collapse pricing.** ChorusGraph = orchestration. PrismGuard = security/audit. Bundle for enterprise deals; keep separate SKUs for procurement.

**ChorusGraph today:** Apache-2.0 OSS + license-gated Postgres persistence. **No guard port yet** — PrismGuard ships `prismguard.integrations.chorusgraph.make_guard_handler()` (OSS). ChorusGraph v2 should add optional `GuardBackend` (enterprise co-sell).

**PrismGuard production layers shipped in this repo (2026-07-09):**

| Layer | Path | Tier |
|-------|------|------|
| License gates | `prismguard/licensing/` | Team/Business |
| HTTP guard API | `prismguard serve` → `prismguard/http/service.py` | Business |
| ChorusGraph node | `prismguard/integrations/chorusgraph.py` | OSS |
| Integration guide | `docs/integration-guide.md` | all |
| Enterprise model | `docs/enterprise-product-model.md` | GTM |

**Claim discipline (unchanged):** every stat traces to `benchmark/law/results/current/` or fresh `adversarial_self_check.py` output. No healthcare/finance. Lead with audited + cost, not generic “beats all scanners.”

**Safe claims:** owned ONNX classifier · audit `resolution_gate` on every decision · reproducibility · selective Judge escalation · ChorusGraph + LangGraph integration · ~200ms ONNX law path (cite report).

**Do not claim on landing page:** holdout YAML as a customer feature · "we patch your runtime from eval sets" · healthcare/finance readiness.

---

## PART A0 — User updates vs holdout (landing + docs copy)

**Correction (2026-07-09):** Holdout files are **evaluation-only**. They are never imported into customer runtime or bundled seed. Earlier confusion treated holdout like a runtime patch — it is not.

### How customers get better guard quality

| Channel | What improves | Customer action |
|---------|---------------|-----------------|
| `pip install -U prismguard` | Code, structural rules, HTTP API | Upgrade package |
| `prismguard init` / seed `update` | Bundled + domain overlay corpus | Re-run after upgrade |
| Model artifact in wheel | ONNX classifier (`prism-pi-v1`) | Automatic on pip upgrade when version bumps |
| Signed license | Team/Business features (pgvector, serve, tenant) | Renew `PRISMGUARD_LICENSE_FILE` |
| Future eval pack (Team+) | Self-verify on customer infra | Optional download — **still never merged into seed** |

### Landing page section — "How updates work"

Suggested copy (honest, procurement-friendly):

> PrismGuard improves through versioned pip releases, optional seed updates, and model artifacts shipped in the package. Internal benchmark holdout sets are used only by Insight IT to prevent overfitting — they are not imported into your production guard. After upgrading, run `prismguard eval self-check` to verify fresh probes on your machine.

Link: `docs/user-updates.md` on GitHub (once published).

### What engineers run vs what customers run

| Command | Audience | Includes holdout? |
|---------|----------|-------------------|
| `python scripts/adversarial_self_check.py` | Maintainers / CI | Yes — full gates |
| `prismguard eval self-check` | Customers post-pip | No — fresh probes only |
| `prismguard doctor` | Everyone | No |

---

## PART A — Business model (landing page depends on this)

### Product SKUs (Prism family pattern)

Mirror `prismcortex` / `chorusgraph` / `chorusgraph-pilot`:

| SKU | Price (pre-validation) | Includes |
|-----|------------------------|----------|
| `prismguard` | $0 | Library, ONNX classifier, heuristic Judge, memory storage, law domain, ChorusGraph guard node, CLI `doctor`/`init` |
| `prismguard-team` | ~$199/mo | pgvector persistence, feedback review persistence, calibration exports |
| `prismguard-business` | ~$699/mo | `prismguard serve` HTTP API, OpenAI Judge option, tenant lexicon, session hooks |
| `prismguard-pilot` | ~$25k | Enterprise pilot — custom lexicon, security pack, SLA, ChorusGraph co-integration |

Comment in JS: `// pre-validation estimate — see docs/enterprise-product-model.md`

### T1 — `productDeployPrices.js`

**Files:** `C:\code\InsightitsAIAgent\src\pages\products\productDeployPrices.js`

```js
prismguard: { name: 'PrismGuard — Audited Prompt-Injection Firewall', price: 0, monthly: 0 },
'prismguard-team': { name: 'PrismGuard Team', price: 0, monthly: 199 },
'prismguard-business': { name: 'PrismGuard Business', price: 0, monthly: 699 },
'prismguard-pilot': { name: 'PrismGuard Enterprise Pilot', price: 25000, monthly: 0 },
```

Cross-link ChorusGraph bundle copy: "Works natively with ChorusGraph" — not "included in ChorusGraph price."

### T2 — `PRISMGUARD_EXTERNAL` in `productVerticalAIContent.js`

Mirror `PRISMCORTEX_EXTERNAL`. Verify GitHub + PyPI URLs before publish (PyPI may not exist yet — link GitHub if 404).

### T3 — Pricing page narrative

**OSS tier:** developers, self-hosted, Apache-2.0 library, no API key for classifier path.

**Team:** persistent corpus + feedback for teams running law/compliance pilots.

**Business:** HTTP sidecar for polyglot stacks; production tenant context.

**Pilot:** design partner — matches `docs/law-pilot-readiness.md` gate (adversarial self-check green).

**ChorusGraph enterprise bundle (sales talk track):**

- Customer runs ChorusGraph for agent graphs + Postgres checkpoints.
- Customer adds PrismGuard Business (sidecar or embedded) for audited input/output guard.
- Insight IT sells two licenses; optional bundle discount.

---

## PART B — Landing page (product)

(Unchanged task list T3–T7 from original handoff — scaffold `prismguard-landing/`, PROOF_STATS from fresh benchmark, honest narrative, SEO, catalog.)

**Additional section — Integrations:**

- ChorusGraph: `make_guard_handler()` code sample from `prismguard/integrations/chorusgraph.py`
- LangGraph: cite LPL benchmark stack
- HTTP: `POST /v1/check` for Business tier

**Differentiation (honest):**

- Audited decisions, not opaque scores
- Self-hosted classifier — traffic stays on customer infra
- Cheaper path via ONNX + rare Judge (cite escalation rate from benchmark)
- **Not:** superior detection vs LLM Guard

---

## PART C — PrismGuard repo production gaps (engineer)

Status after 2026-07-09 pip-readiness pass:

| Gap | Status |
|-----|--------|
| Business model doc | **Done** — `docs/enterprise-product-model.md` |
| License feature gates | **Done** — `prismguard/licensing/` |
| Signed Ed25519 licenses | **Done** — `prismguard/licensing/validator.py` (shared dev key with ChorusGraph) |
| HTTP guard service | **Done** — `prismguard-serve`, Business license |
| OTel-style `/metrics` | **Done** — Prometheus text on `prismguard serve` |
| pgvector / persistent backend gate | **Done** — `create_storage()` requires `enterprise_persistence` |
| User update model doc | **Done** — `docs/user-updates.md` |
| Customer verify CLI | **Done** — `prismguard eval self-check` |
| PyPI publish checklist | **Done** — `docs/publishing-pypi.md` |
| ChorusGraph integration module | **Done** — OSS |
| Integration guide | **Done** |
| ChorusGraph `GuardBackend` port | **Open** — ChorusGraph repo |
| ChorusGraph example graph | **Open** — `C:\code\ChorusGraph\examples/` |
| Classifier retrain | **Open** |
| Customer discovery | **Open** |
| Landing page Part B | **Open** — InsightitsAIAgent |

### Remaining engineering (priority)

1. **PyPI publish** — `python -m build`, `twine upload` per `docs/publishing-pypi.md` (version **0.1.1**).
2. **ChorusGraph example graph** in `C:\code\ChorusGraph\examples/prismguard_rag/` using real import.
3. **Landing page Part B** — scaffold + PROOF_STATS + "How updates work" section from Part A0.
4. **Production license public key** — replace dev issuer key before first paid customer.

### Cleanup (2026-07-09)

- Calibration `tune_thresholds` no longer overwrites `classifier_mode` when grid-searching (was causing false FP blocks in tests).
- PyPI wheel ships `prismguard` only — `benchmark/` stays repo-local.
- Shared fresh probes: `prismguard/eval/probes.py` (used by `eval self-check` + `adversarial_self_check.py`).
- README + design doc aligned with memory default, persistent backends, HTTP serve.
- PyPI wheel: `prism-pi-v1` only (v2 excluded); `MANIFEST.in` prunes benchmark/tests from sdist.
- **Tests:** 172 passed, 1 skipped (`pytest tests/`).

---

## Order & effort

Part A → Part B (landing). Part C can proceed in parallel in PrismGuard repo.

Estimate: T1: 1h · T2: 1–2h · T3–T7: 12–16h · Part C ChorusGraph example: 1–2 days.

## Return format (`handoffbackLandingPage.md`)

Per task: files · pass/fail · fresh benchmark output for stats · link verification · local dev URL.

---
*Dual product: PrismGuard standalone + ChorusGraph plugin · open core + Team/Business/Pilot SKUs · pip updates ≠ holdout import · HTTP serve = Business · guard node = OSS · PyPI 0.1.1 ready pending upload.*
