# Grand Slam Offer: PrismGuard Guardrail Autopsy → Domain Pilot

> Hormozi Section 8 fill-in — primary wedge for AppSec / platform buyers.  
> Expert agent: `.cursor/skills/prismguard-b2b-marketing/SKILL.md`

## Product: PrismGuard (standalone — not ChorusGraph bundle)

### Avatar (one primary)
- **Title:** CISO · Head of Platform · AppSec / compliance engineer
- **Company type:** B2B shipping LLM features or agents in staging/production; regulated or audit-sensitive
- **Bleeding pain:** Indirect prompt injection via RAG/docs/email; can't defend probabilistic guard scores to auditors; security questionnaire blocks on "AI guardrails"
- **Budget authority:** Often CISO or VP Eng; economic buyer cares about **liability**, not pip ergonomics

### Dream outcome
- **Statement:** Every LLM allow/block decision is **defensible in an audit** — without sending production prompts to a third-party scan API
- **Metric:** Guard at all agent entry points; `resolution_gate` on every decision; pilot domain calibrated via feedback loop
- **Horizon:** pip install today → Guardrail Autopsy (30 min) → 30-day domain pilot → recurring sidecar

### Value Equation scores (1–10)
| Variable | Score | Notes |
|----------|-------|-------|
| Dream Outcome | **8** | Clear compliance / liability story |
| Perceived Likelihood | **4** | **Weakest** — alpha, n=14 law holdout, domain-agnostic claim needs Autopsy + pilot |
| Time Delay | **8** | pip + doctor in minutes; Autopsy = 30 min |
| Effort & Sacrifice | **7** | Self-hosted; rules-first avoids 705MB ONNX by default |
| **Fix first** | **Likelihood** | Holdout methodology + honest alpha + Autopsy on *their* entry points |

### Grand Slam Offer name
**Lead magnet:** **Guardrail Autopsy** (free 30 min)  
**Paid wedge:** **Domain Production Pilot** ($25k) → **$199–699/mo** HTTP sidecar

### Offer stack (Autopsy → Pilot)
| Component | Solves obstacle | Value anchor |
|-----------|-----------------|--------------|
| Entry-point map (RAG, email, chat, tools) | "Where would injection land?" | $3,000 |
| Live `resolution_gate` demo on their sample prompt | "Can't explain blocks to legal" | $2,500 |
| Rules-first profile recommendation (`web_chat` / `sidecar` / `law_pilot`) | "Integration surprise" | $2,000 |
| Cold-holdout proof pack (law benchmark methodology) | "No proof" | $1,500 |
| 30-day pilot credit toward production sidecar if convert | "Too risky on alpha" | $5,000 |
| **Total anchor** | | **$14,000** |
| **Autopsy price** | | **$0** (lead magnet) |
| **Pilot price** | | **$25,000** |

### Guarantee (conditional — pilot only)
Agreed attack scenarios blocked with auditable `resolution_gate` logs on pilot traffic, **or** pilot fee credited toward implementation. (Align when contract template ships.)

### Pain → Proof → Plan
- **Pain:** "Your agent reads untrusted documents. When it gets instructed, security can't explain *which* guard made the call."
- **Proof:** Law cold holdout 14/14 vs 9/14 (LLM Guard); 211ms vs 353ms; every decision has `resolution_gate`. Alpha disclosed.
- **Plan:** (1) pip install (2) Guardrail Autopsy (3) Domain pilot → sidecar license
- **CTA:** Comment "autopsy" or DM for free 30-min Guardrail Autopsy

### Category (Dunford)
**WAF layer for LLMs** — not "another LLM Guard." Opinionated firewall + audit trail.

### Channels (pick 2)
- [x] LinkedIn (B2B AppSec intro post + flyer)
- [x] OSS discovery (PyPI, GitHub, integration tutorials)
- [ ] Website landing (`prismguard.html` — pending)
- [ ] Legal-tech / security communities

### 30-day launch
- **Week 1:** LinkedIn intro post + flyer (category-first)
- **Week 2:** LangGraph guard tutorial brief → publish
- **Week 3:** prismguard.html + Autopsy booking link
- **Week 4:** First Autopsy conversations → pilot pipeline

### Do NOT merge with ChorusGraph funnel
Nat · Bob · Jeff · Jared · Brianne = ChorusGraph only. Michael = stack exception (Ledger + guard).
