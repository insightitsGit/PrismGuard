# Handoff: README — domain ONNX train is MANDATORY for every new domain

**ID:** HO-PrismGuard-017  
**Project:** PrismGaurd (PrismGuard)  
**Date:** 2026-07-23  
**From:** Senior QA / Architect  
**To:** docs-agent / Dev agent  
**Priority:** P1  
**Status:** Pending

## Context

FinancePackBench mid (2026-07-23) proved:
- Hub `web_chat` ONNX-off → task healthy, **PI attack block 15%** on finance cold set
- Law `prism-pi-v1` light ONNX → PI ~80% but **task 37.5%** / benign allow 30% (not shippable)
- **Finance-trained** `prism-pi-finance-v1` → task **100%**, PI **75%**, benign **90%**

Director lock already in `C:\code\PrismGaurd\AGENTS.md` and `.cursor\rules\domain-artifact-mandatory.mdc`. **README still says customer train is “opt-in”** — that contradicts the lock and will cause agents/integrators to skip retrain.

User directive (2026-07-23): for **any new domain**, domain model train is **mandatory, not optional**. Apply via Dev window (QA does not edit PrismGuard source on this pass).

Evidence:
- `C:\code\QA\projects\FinancePackBench\results-archive\mid_pl_financeonnx_20260723\`
- `C:\code\QA\projects\FinancePackBench\reviews\2026-07-23-finance-onnx-train.md`
- `C:\code\QA\projects\PrismGaurd\handoffs\HO-PrismGuard-016-finance-domain-retrain.md`

## Objective

Update PrismGuard public docs so **new domain ⇒ train a domain-matched ONNX artifact** is stated as **MANDATORY** (product requirement), not optional R&D / opt-in nicety.

## Background

| Traffic | Allowed ONNX artifact | Forbidden |
|---------|----------------------|-----------|
| Law / scorecard | `prism-pi-v1` | Claiming finance/hub proof from law weights |
| Finance | `prism-pi-finance-v*` after train + gates | Enforcing law artifact on finance ingress |
| Hub / general | `prism-pi-hub-v*` / customer after gates | Silent law ONNX on hub FAQ |
| **Any other new domain** | `prism-pi-<domain>-v*` after train + gates | Reusing law/finance weights “because ONNX is on” |

Hub UX wiring (`web_chat` ONNX off + optional shadow) stays valid for **ingress UX**. That does **not** replace domain train when the product needs domain-calibrated PI enforcement or bake-off claims.

## Tasks

- [ ] **Task 1:** Add a prominent **“Domain ONNX artifacts (MANDATORY)”** section to `README.md` (paste-ready text below). Place after the ONNX download / honesty note (around the paragraph that currently says customer train is opt-in).  
  - Files: `C:\code\PrismGaurd\README.md`  
  - Acceptance: Section heading exists; word **MANDATORY** appears; table of domain → artifact present

- [ ] **Task 2:** Replace misleading “opt-in” language for domain retrain.  
  - Find: `Customer train loop (all **opt-in**)`  
  - Replace with language that: feedback persist / learn extras remain feature layers; **domain-matched train when entering a new domain is mandatory**  
  - Also fix Pick-your-features / capabilities table row that says “Learn from your traffic (opt-in)” if it implies domain train is optional for new domains  
  - Acceptance: No README sentence that frames domain retrain as optional for new domains

- [ ] **Task 3:** Extend **Finance / hub agents with ChorusGraph** Do/Don’t:  
  - **Do:** For finance PI enforce / bake-off: train `prism-pi-finance-v1` (or newer), gate, then `PRISMGUARD_ARTIFACT_ID=…` on that path  
  - **Don’t:** Treat law `prism-pi-v1` as the finance solution; don’t close domain work with web_chat-only when domain PI was the ask  
  - Acceptance: Finance subsection mentions mandatory domain artifact

- [ ] **Task 4:** Mirror the lock in `docs/best-practices.md` under Finance agent pack + decision tree (new domain branch → train before enforce).  
  - Files: `C:\code\PrismGaurd\docs\best-practices.md`  
  - Acceptance: “new domain ⇒ retrain” stated as mandatory

- [ ] **Task 5:** Optional but preferred: one-line cross-link from README section to `docs/guard-model-training.md` (if that doc exists) and keep `AGENTS.md` as agent canon (do not weaken AGENTS.md).

## Paste-ready README section (Task 1)

```markdown
### Domain ONNX artifacts (MANDATORY)

**`prism-pi-v1` is law-bench calibrated. It is not a universal PI model.**

For **any new domain** (finance, hub/FAQ, healthcare, custom vertical, …), you **MUST** train and ship a **domain-matched** ONNX artifact before enforcing ONNX on that traffic or claiming domain PI results. This is a **product requirement**, not optional R&D.

| Traffic domain | Allowed artifact | Forbidden |
|----------------|------------------|-----------|
| Law / scorecard | `prism-pi-v1` (or newer **law** artifact) | Claiming finance/hub proof from these weights |
| Finance | `prism-pi-finance-v*` after train + FP gates | Enforcing `prism-pi-v1` on finance ingress |
| Hub / general chat | `prism-pi-hub-v*` / customer artifact after gates | Silent law ONNX on hub FAQ |
| Any other new domain | `prism-pi-<domain>-v*` after train + gates | Reusing another domain’s weights “to turn ONNX on” |

**Locked loop**

```text
Target domain ≠ law (or ≠ your shipped artifact’s domain)
  → labeled attack + benign feedback (holdouts kept out of train)
  → prismguard-model train --domain-pack <domain> --artifact-id prism-pi-<domain>-v1 \
       --feedback-jsonl … [--normal-txt …]
  → eval gates: attack holdout block + benign allow (incl. domain UX such as FX)
  → only then: PRISMGUARD_ARTIFACT_ID=… + USE_ONNX on that path
  → disclose domain + artifact_id on every scorecard / COMPARISON_REPORT
```

Structural / regex fixes help but **do not replace** domain retrain.

Hub UX may still use `web_chat` (ONNX off) + optional shadow ONNX for low false positives. That path is **not** a substitute for a domain artifact when you need domain-calibrated enforcement or publishable PI claims.

Evidence (finance mid, 2026-07-23): `web_chat` ~15% PI block; law light ONNX recovered PI but collapsed task; finance-trained artifact reached ~100% task / ~75% PI / ~90% benign allow on the mid holdout harness.
```

## Constraints

- Do **not** weaken `AGENTS.md` or `.cursor/rules/domain-artifact-mandatory.mdc`
- Do **not** claim “we beat LangGraph / AgentCore” from mid finance ONNX numbers
- Do **not** tell integrators to set `PRISMGUARD_USE_ONNX=1` globally with the law artifact
- Keep smoke/mid disclosures (n, seed, planted grounding) honest
- **Do not edit files under `C:\code\QA\`** except writing a handoff-back under `projects/PrismGaurd/handoffs-back/`

## Files to Touch

| File | Action | Notes |
|------|--------|-------|
| `C:\code\PrismGaurd\README.md` | Modify | Mandatory domain section + remove “opt-in” for domain retrain |
| `C:\code\PrismGaurd\docs\best-practices.md` | Modify | Decision tree + Finance pack |

## Acceptance Criteria

- [ ] README states domain train is **MANDATORY** for any new domain
- [ ] Domain → artifact table present
- [ ] No “customer train = opt-in” wording that applies to new-domain retrain
- [ ] Finance/hub wiring still warns against global law ONNX
- [ ] `docs/best-practices.md` mirrors the lock
- [ ] Handback lists exact diffs / section anchors

## Verification Steps

1. Grep README for `opt-in` near train/domain — must not imply new-domain retrain is optional  
2. Grep README for `MANDATORY` + `Domain ONNX`  
3. Confirm finance section still has `web_chat` + no global `USE_ONNX=1`  
4. Spot-check `AGENTS.md` still has the Director lock intact  

## How to hand back

When work is done (or blocked), the receiving agent must:

1. Set this handoff **Status** to `Ready for QA` or `Blocked`.
2. Create `projects/PrismGaurd/handoffs-back/HB-PrismGuard-017-readme-domain-train-mandatory.md` from `_templates/handoff-back.md`.
3. Leave source changes in `C:\code\PrismGaurd` (commit only if the user asked).
4. Do **not** close this handoff — QA owns verification.

## Related Artifacts

- `AGENTS.md` — Domain ↔ ONNX artifact lock  
- `.cursor/rules/domain-artifact-mandatory.mdc`  
- HO-016 finance domain retrain  
- FinancePackBench mid finance ONNX review  

## Notes for Receiving Agent

Paste Task 1 section almost verbatim; adjust only if README anchors/headings need renumbering. Prefer one clear callout over burying the rule inside “Learn from seed.” User will run this through the Dev agent window.
