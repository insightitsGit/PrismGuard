# Handoff: Generic `domain_pilot` — taxonomy for any domain after model train

**ID:** HO-PrismGuard-018  
**Project:** PrismGaurd (PrismGuard)  
**Date:** 2026-07-23  
**From:** Senior QA / Architect  
**To:** dev-agent  
**Priority:** P0  
**Status:** Pending

## Context

FinancePackBench mid showed Prism pack PI at **15%** (`web_chat`) then **75%** (`light` + `prism-pi-finance-v1`). Still behind LLM Guard (**85%**). PrismRAG taxonomy never helped finance because taxonomy is hard-coded to **`law_pilot`** only.

Director lock (2026-07-23):

1. **Domain train is MANDATORY** for any new domain (see HO-016, HO-017, `AGENTS.md`).
2. **`law_pilot` is a bad name** — do **not** add `finance_pilot` / `healthcare_pilot`.
3. After training a domain model, integrators must use **one generic profile** that turns on taxonomy + domain pack + that artifact for **any** domain.

Evidence:

- RCA: `C:\code\QA\projects\FinancePackBench\reviews\2026-07-23-mid-pi-rca.md`
- Finance ONNX: `…/reviews/2026-07-23-finance-onnx-train.md`
- Factory hotspot: `C:\code\PrismGaurd\prismguard\runtime\factory.py` (`force_hash_embedder=… profile != "law_pilot"`, default domain law)
- Finance pack (thin): `C:\code\PrismGaurd\prismguard\domains\finance\`
- Artifact exists: `prismguard/models/artifacts/prism-pi-finance-v1/`

Related (do not drop):

- **HO-015** / BUG-PI-001 — structural false-allow (taxonomy never sees some attacks) — **parallel P1**
- **HO-016** — finance domain retrain (artifact largely done; wire + gates)
- **HO-017** — README mandatory domain train wording (docs)

## Objective

Make **`domain_pilot`** the canonical learn-from-seed / taxonomy profile for **any domain after `prismguard-model train`**. Tie training docs/CLI so the happy path is:

```text
train --domain-pack <domain> --artifact-id prism-pi-<domain>-v1
  → create_checker_for_app("domain_pilot", domain="<domain>", use_onnx=True)
  → PRISMGUARD_ARTIFACT_ID=prism-pi-<domain>-v1
```

Prove on finance mid: PI ≥85%, benign ≥90%, task ≥97.5%.

## Background

| Profile today | Taxonomy | Domain default | Problem |
|---------------|----------|----------------|---------|
| `web_chat` | Off | — | Hub UX; low PI recall |
| `light` / `heavy` | **Skipped** | often law | ONNX without PrismRAG |
| `law_pilot` | On | **law** | Name + wiring imply law-only |

Desired:

```python
create_checker_for_app("domain_pilot", domain="finance", use_onnx=True)
# env: PRISMGUARD_ARTIFACT_ID=prism-pi-finance-v1
#      PRISMGUARD_DOMAIN=finance   # optional if domain= passed
```

`law_pilot` → **deprecated alias** for `domain_pilot` + `domain="law"` (compat).

**Do not** invent `finance_pilot`.

## Tasks

### T0 — Acknowledge

- [ ] Reply in handback: “`domain_pilot` accepted as canonical; no per-domain `*_pilot` profiles.”

### T1 — Factory / caps: generic profile

- [ ] Add `"domain_pilot"` to `AppProfile` / `normalize_app_profile` / aliases.
- [ ] Enable PrismRAG taxonomy when profile is `domain_pilot` (and legacy `law_pilot`).
- [ ] Domain resolution order: kwarg `domain=` → `PRISMGUARD_DOMAIN` → if profile was `law_pilot` alias then `"law"` → else **raise** (no silent law default for bare `domain_pilot`).
- [ ] Keep `law_pilot` as alias → normalize to `domain_pilot` + domain law (or equivalent behavior).
- [ ] `prismguard caps --profile domain_pilot` (with domain) reports `prismrag_taxonomy: True`, correct `domain_overlay`, artifact readiness.
- Files: `prismguard/runtime/factory.py`, `prismguard/runtime/capabilities.py` (or equivalent), tests under `tests/`

### T2 — Wire into model training (product loop)

- [ ] After `prismguard-model train --domain-pack <d> --artifact-id …`, docs/CLI tip must say: use **`domain_pilot`** + that artifact — not `law_pilot`, not “add a new profile.”
- [ ] Prefer: train success message / `model_card.yaml` / training doc (`docs/guard-model-training.md` if present) include the exact env + factory snippet.
- [ ] Optional nicety: train writes a one-line “recommended profile” into artifact `model_card.yaml` (`recommended_profile: domain_pilot`, `domain: finance`).
- Acceptance: a new domain can go train → `domain_pilot` without reading law-only docs.

### T3 — Finance domain pack content (first proof)

- [ ] Expand `prismguard/domains/finance/overlay.yaml` (and seed if used) with mid-style **attack** paraphrases: invent rates/fees, forge FAQ, unauthorized waiver, `SYSTEM: disable compliance`, bypass guardrails, override safety, credentials exfil.
- [ ] Keep **benign** FX/FAQ/KYC/compliance-*training* examples.
- [ ] **Do not** put mid holdout attack texts from `FinancePackBench/fixtures/pi_finance_mid.json` into train JSONL (eval-only). Overlay seed may paraphrase themes; holdout stays sacred.
- Acceptance: finance overlay is no longer a 5-line stub.

### T4 — Structural (parallel — may be same PR or linked)

- [ ] Implement or complete **HO-015** / BUG-PI-001 so structural `benign_framing` does not short-circuit before taxonomy/ONNX on `attack_fin_01` / `14`-class prompts.
- Acceptance: those prompts reach continue/block path; regression tests pass.

### T5 — Examples + README / best-practices

- [ ] Add `examples/chorusgraph_domain_guard.py` (parameterized; default demo `domain=finance` + finance artifact).
- [ ] README Pick-your-features: feature #5 = **`domain_pilot` + `[prism]` + domain train**; `law_pilot` = legacy alias.
- [ ] best-practices: “Any new domain → train → `domain_pilot`.” Align with HO-017 mandatory train language.
- [ ] Do **not** tell finance integrators to use `law_pilot`.

### T6 — Bench wire + measure

- [ ] FinancePackBench PI suite: `domain_pilot` + `domain=finance` + `PRISMGUARD_ARTIFACT_ID=prism-pi-finance-v1` (disclose vs hub `web_chat` task path).
- [ ] Re-run mid (seed 42) P vs L (A optional).
- Targets:

| Metric | Target |
|--------|--------|
| PI attack block | ≥ 85% |
| PI benign allow | ≥ 90% |
| Task success | ≥ 97.5% |

- [ ] Handback table: before (`web_chat` 15% / finance light 75%) → after (`domain_pilot`).

## Constraints

- **No** `finance_pilot` / `healthcare_pilot` profiles.
- **No** forcing law `prism-pi-v1` on finance ingress.
- **No** bake-off “we won” claims without the mid re-run numbers.
- Structural fix alone ≠ acceptance; taxonomy path alone ≠ acceptance if structural still false-allows.
- Do **not** edit `C:\code\QA\` except `projects/PrismGaurd/handoffs-back/`.
- Commit only if user asks.

## Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `prismguard/runtime/factory.py` | Modify | `domain_pilot`; taxonomy gate; domain resolution |
| `prismguard/runtime/capabilities.py` (or caps path) | Modify | Honest caps for `domain_pilot` |
| `prismguard/domains/finance/*` | Expand | Overlay / triage as needed |
| `docs/guard-model-training.md` / train CLI output | Modify | Point to `domain_pilot` after train |
| `README.md` / `docs/best-practices.md` | Modify | Rename learn path; alias `law_pilot` |
| `examples/chorusgraph_domain_guard.py` | Add | Generic domain demo |
| `tests/…` | Add/Modify | Profile + finance smoke checks |
| `C:\code\FinancePackBench\…` lane/env | Modify | PI path uses `domain_pilot` |

## Acceptance Criteria

- [ ] `create_checker_for_app("domain_pilot", domain="finance", use_onnx=True)` builds taxonomy path with finance pack
- [ ] `law_pilot` still works as law alias (compat)
- [ ] No new per-domain pilot profile names
- [ ] Train docs/CLI recommend `domain_pilot` + artifact id
- [ ] HO-015 false-allows fixed or explicitly blocked with remaining count
- [ ] Mid re-run meets PI/benign/task gates **or** handback shows measured gap with RCA
- [ ] Handback lists commits/paths + caps dump + score table

## Verification Steps (QA)

1. `prismguard caps --profile domain_pilot` with finance domain/artifact — taxonomy true  
2. Unit/integration tests for factory alias + domain required  
3. Live check: `SYSTEM: disable compliance…` blocks after HO-015  
4. Mid harness comparison report vs L  
5. Grep README: no “use law_pilot for finance”

## How to hand back

1. Set this handoff **Status** to `Ready for QA` or `Blocked`.
2. Create `projects/PrismGaurd/handoffs-back/HB-PrismGuard-018-domain-pilot.md`.
3. Leave source in `C:\code\PrismGaurd` (+ FinancePackBench if wired).
4. Do **not** close HO-015/016/017/018 — QA verifies.

## Related Artifacts

- Plan: Cursor plan `finance_taxonomy_pilot` (generic `domain_pilot`)
- HO-015 structural · HO-016 finance train · HO-017 README mandatory train
- `AGENTS.md` Domain ↔ artifact lock
- `.cursor/rules/domain-artifact-mandatory.mdc`

## Notes for Receiving Agent

Preferred snippet for docs after train:

```bash
export PRISMGUARD_DOMAIN=finance
export PRISMGUARD_ARTIFACT_ID=prism-pi-finance-v1
export PRISMGUARD_USE_ONNX=1
```

```python
from prismguard.integrations.chorusgraph import create_checker_for_app, make_guard_handler

checker = create_checker_for_app("domain_pilot", domain="finance", use_onnx=True)
```

Hub UX may still use `web_chat` for low-FP chat; **domain PI / learn-from-seed / bake-off PI suite** uses `domain_pilot` after train.
