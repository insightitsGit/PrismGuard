# PrismGuard GTM strategy — AppSec path (saved from Google research)

**Source:** Google research brief (user save, 2026-07-09)  
**Status:** Canonical PrismGuard GTM — **separate from ChorusGraph angel playbook**  
**Product KB:** `kb/PRISMGUARD_PRODUCT.md` · **Visual:** `canvases/prismguard-gtm-path.canvas.tsx`

---

## Why PrismGuard wins: the "AppSec budget" shift

Enterprise security buyers (CISOs and AppSec leads) are focused on **indirect prompt injection** — e.g. an agent reads a corrupted PDF or malicious email, gets injected, and executes a tool that deletes data or leaks PII.

**LLM Guard** is general-purpose toolkit friction. **PrismGuard** is the **opinionated firewall for auditable allow/block decisions** — sell to the person responsible for **liability**, not only the developer wiring agents.

| Buyer fear | PrismGuard answer |
|------------|-------------------|
| Indirect injection via RAG/docs/email | Guard at entry + optional chunk intercept (tutorials) |
| Can't defend probabilistic scores to regulators | Every decision has `resolution_gate` + `decision_source` |
| Prompts leaving VPC for scanning | Self-hosted rules + local ONNX (opt-in); no default third-party scan |
| Startup blocked on enterprise security questionnaire | Drop-in firewall module — "Secure Auditable Firewall" checkbox |

**Do not collapse** into ChorusGraph marketing. ChorusGraph = orchestration/devtool motion. PrismGuard = **AppSec / compliance budget**.

---

## Part 1 — Target angels (AI security & AppSec)

Angels who built cybersecurity, developer platforms, or invest in AI safety / alignment.

| # | Name | Why | Pitch angle | Channel |
|---|------|-----|-------------|---------|
| 1 | **Jaan Tallinn** (Skype co-founder, AI safety) | Early DeepMind/Anthropic backer; cares about defensive boundaries preventing rogue agent actions | Explainability + **local-first** ONNX (sensitive prompts not sent to third-party scan APIs) | LinkedIn · X |
| 2 | **Kevin Mahaffey** (Lookout co-founder, cyber angel) | Mobile security at scale; knows what audit logs must show for production sign-off | **"WAF layer for LLMs"** — CI/CD + explainable gates | Email · LinkedIn · X *(verify contact before send)* |
| 3 | **Michael Grinich** (WorkOS CEO) | Enterprise readiness (SSO, audit logs); AI startups blocked on Fortune 500 security review | PrismGuard = **enterprise readiness module** — "Secure Auditable Firewall" on security questionnaires | X DM @grinich |
| 4 | **Ben Sigelman** (OpenTelemetry co-creator) | High-throughput tracing; structured telemetry | `resolution_gate` metadata → **security traces** mapping to OTel backends | LinkedIn · X |

### Michael — two valid angles (pick one per touch)

| Motion | Lead | When |
|--------|------|------|
| **ChorusGraph stack** (existing) | Route Ledger + PrismGuard guard | WorkOS compliance / orchestration |
| **PrismGuard solo** (this doc) | Enterprise readiness checkbox for AI startups selling upmarket | Security questionnaire / AppSec |

Do **not** send both in one message.

### ChorusGraph angels — do NOT repurpose for PrismGuard solo

Nat · Bob · Jeff · Jared · Brianne = **ChorusGraph path only**. PrismGuard has its **own** angel list above.

---

## Part 2 — High-velocity integration tutorials

Security tools distribute as **guardrail middleware** in stacks developers already use.

### Target 1 — LangChain / LangGraph node

**Title:** How to Secure Your LangGraph Agent from Indirect Prompt Injection in 5 Minutes Using PrismGuard

**Content:** Inject local `prismguard` check at **entry node** of a LangGraph `StateGraph`.

```python
from prismguard.runtime.factory import create_checker_for_app

checker = create_checker_for_app("web_chat")  # rules-first, no surprise ONNX
```

**Distribute:** LangChain/LangGraph Discord, relevant subreddits.  
**Buyer:** Agents with financial/DB tools needing local node firewall without API latency.

**Note:** LangGraph appears here as **integration target**, not as ChorusGraph benchmark competitor hero.

---

### Target 2 — Legal tech & document RAG (LlamaIndex)

**Title:** Jailbreak Defense for Legal AI: Securing LlamaIndex RAG Pipelines Against Context-Stuffed Injections

**Content:** Document agents (MSA, NDA, vendor agreements) vulnerable to adversarial text in long files. Run **local ONNX** (`prism-pi-v1`, law-calibrated) to intercept **retrieved chunks** before LLM synthesis.

**Distribute:** Legal AI / compliance dev communities.  
**Buyer:** Specialized legal-tech builders — premium domain packs.

**Honesty:** Law ONNX is **law-bench calibrated**; cite as verified vertical proof, not "works everywhere out of the box."

---

### Target 3 — FastAPI / sidecar (AppSec teams)

**Title:** Deploying a Self-Hosted, Air-Gapped AI Firewall in 60 Seconds with Docker and `prismguard serve`

**Content:** HTTP API sidecar with cached ONNX weights, isolated from internet.

**Distribute:** AppSec / platform security audiences.  
**Buyer:** Enforce firewall globally across internal chatbot fleet.

**SKU:** Business tier (`prismguard serve`) — aligns with **$699/mo** motion.

---

## Part 3 — Cybersecurity angel outreach template

**Use for:** Jaan Tallinn · Kevin Mahaffey · Ben Sigelman (adapt per angel)  
**Copy-paste file:** `kb/outreach/prismguard-security-angel-email-send.txt`  
**Michael:** Use PrismGuard enterprise-readiness angle OR existing ChorusGraph stack DM — not both.

**Sequence logic (from research):**

1. Position vs LLM Guard on **explainable** logs (compliance pain)  
2. Prove systems seriousness: local ONNX-first, rules path, optional Judge ~7%  
3. Law holdout as **verified proof** (14/14 vs 9/14; 211ms mean)  
4. GitHub + PyPI in 5 seconds — no call ask in v1

---

## Claims guardrails (KB-enforced)

| Claim | OK? |
|-------|-----|
| Auditable `resolution_gate` per decision | Yes |
| Law holdout 14/14 vs LLM Guard 9/14 | Yes (cold holdout) |
| Self-hosted / local ONNX opt-in | Yes — disclose `prismguard-model download` |
| "Zero data leak" | Soften to **"prompts stay in VPC by default"** — no overclaim |
| "WAF for LLMs" | Positioning metaphor — OK for security angels |
| Healthcare/finance domain ready | **No** — roadmap |
| External security audit complete | **No** |

**PyPI pin:** `pip install "prismguard[prism,guard-model]==0.1.6"`  
**v0.1.6 headline:** Customer feedback export + any-domain ONNX train path (OnnxCustomer1) — law holdout remains published proof.

---

## Execution order (recommended)

```
1. Ship prismguard.html + Guardrail Autopsy CTA
2. Tutorial 1 (LangGraph node) — widest dev distribution
3. Security angel email: Kevin or Jaan (verify email)
4. Tutorial 3 (sidecar) — AppSec / Business SKU
5. Tutorial 2 (LlamaIndex legal) — vertical premium path
6. Michael — PrismGuard enterprise-readiness OR ChorusGraph stack (one angle)
```

---

## Related files

| File | Purpose |
|------|---------|
| `kb/PRISMGUARD_PRODUCT.md` | Product truth, domain packs, market value |
| `kb/outreach/prismguard-security-angel-email-send.txt` | Kevin-style email template |
| `kb/outreach/michael-grinich-dm-send.txt` | Michael — ChorusGraph stack (alternate angle) |
| `kb/handoffs/prismguard-publish-michael-gate.md` | Publish gate (mostly closed) |
