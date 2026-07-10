# PrismGuard — The Story (NotebookLM Source)

**Purpose:** Upload this document to Google NotebookLM to generate an audio overview, study guide, or briefing on PrismGuard — covering the marketing story, customer benefits, and technical build.

**Company:** Insight IT Solutions LLC  
**Founder:** Amin Parva  
**Product:** PrismGuard v0.1.6 (Apache-2.0, PyPI, GitHub)  
**Date:** July 2026

---

## Chapter 1 — Why we built it

In 2026, every company was shipping LLM copilots and agents. The models were powerful. The guardrails were not.

Amin Parva and the Insight IT Solutions team were building production AI systems — website hubs, agent runtimes, RAG pipelines — and kept hitting the same wall. When a guard tool flagged a prompt, it returned a number: 0.87. Maybe that meant block. Maybe allow. The on-call engineer did not know. Legal could not defend it in an audit. Twenty minutes disappeared in Slack debating what the score meant.

That is not a security outcome. That is a communication failure dressed up as machine learning.

The insight was simple: **production security needs the same thing web security got decades ago — a firewall that logs which rule fired.** Not a probability. Not a shrug. An auditable decision.

PrismGuard was born from that frustration. It is an open-source prompt-injection firewall that sits in front of any LLM application and answers one question on every request: **allowed or blocked — and which layer decided.**

The team dogfooded it on their own insightits.com website hub before publishing to PyPI. If the marketing chatbot could not run the guard without surprise 700-megabyte model downloads, the product was not ready. That dogfooding discipline became a core design principle: **rules-first by default, heavy models only when you opt in.**

---

## Chapter 2 — The problem we sell against

### Prompt injection moved from research to production

Attackers no longer need to hack your API keys. They **instruct** your model. A corrupted PDF, a poisoned email, a malicious chunk buried in a vendor agreement — indirect prompt injection — and your agent calls the wrong tool, leaks the wrong data, or bypasses your policies.

This is now an AppSec problem, not an ML paper.

### The market gap

Most guardrail tools are **toolkits**. They give you a classifier and let you assemble policy. That works for research labs. It fails in production when:

- Compliance asks *why* something was blocked
- Security questionnaires demand auditable AI guardrails
- Teams cannot send production prompts to third-party scan APIs
- RAG pipelines need guards at **chunk** boundaries, not just user chat

PrismGuard positions as the **opinionated firewall layer** — like a WAF for LLMs — not another toolkit box of parts.

### Category size

The prompt-injection and LLM guardrails market is estimated at roughly **two billion dollars** in 2025–2026, growing toward seven to eleven billion by the early 2030s. PrismGuard does not claim that entire market. Its wedge is narrower and more valuable: **self-hosted, auditable allow/block decisions for regulated and production agent stacks.**

---

## Chapter 3 — What PrismGuard is (plain language)

PrismGuard is a **self-hosted firewall for LLM applications**.

Before a prompt reaches your model, PrismGuard checks it through a tiered pipeline: structural rules, an owned ONNX classifier, taxonomy-aware fusion, and — only for uncertain cases — an optional LLM Judge. Every outcome returns:

- **blocked** or **allow**
- **resolution_gate** — the named layer that decided (for example `tier1_rule`, `guard_model_first`, `fusion_block`)
- **decision_source** — traceable metadata for compliance logs

This is the product's core promise: **every block is explainable.**

It ships as:

- A **Python library** (`pip install prismguard`)
- A **CLI** (`prismguard check`, `prismguard doctor`)
- An **HTTP sidecar** (`prismguard serve`) for production fleets
- A **ChorusGraph integration** (`make_guard_handler`) as a guard node before retrieve/LLM

Apache-2.0. No mandatory cloud scan. Data stays in your VPC.

---

## Chapter 4 — Benefits by audience

### For engineers shipping agents

- **Two-minute try:** `pip install` + `prismguard doctor` + `prismguard check`
- **Rules-first profiles** — no surprise ONNX download on a FAQ bot
- **Wire anywhere:** agent entry node, RAG chunk gate, HTTP sidecar
- **Familiar output:** logs look like infrastructure, not ML research (`resolution_gate=tier1_rule`)

### For security and compliance teams

- **Audit-defensible decisions** — not raw probability scores
- **Self-hosted path** — prompts do not leave your infrastructure by default
- **Shadow mode** — rules enforce while ONNX logs for calibration (`PRISMGUARD_SHADOW_ONNX`)
- **Guardrail Autopsy** (free 30-minute offer) — map where injection can hit their agent stack

### For enterprises and regulated verticals

- **Domain packs** — law verified today; healthcare and finance on roadmap
- **Law cold-holdout proof** published transparently (see Chapter 6)
- **Pilot path** — approximately twenty-five thousand dollar domain production pilot → recurring sidecar license (199–699 dollars per month tiers)
- **Stack story** — PrismGuard + ChorusGraph Route Ledger = orchestration audit + input guard

### For the open-source community

- Full GitHub source, 178+ tests, CI pipeline
- Customer improvement loop in v0.1.6: feedback export → train custom ONNX artifact
- Complements LLM Guard ecosystem — firewall layer when you need policy and audit trail built in

---

## Chapter 5 — How we built it (technical story)

### Design philosophy

The architecture document states the primary rule clearly: **run rules and classifier on every request; gate only the expensive LLM Judge.**

Nobody in this field skips the classifier because a request "looks fine." That judgment is itself an attack surface. What PrismGuard gates is the **generative** LLM call — the slow, costly Judge tier — targeting low single-digit percent escalation rates.

### The Prism family stack (reuse, not rebuild)

PrismGuard is not a monolith. It composes existing Insight IT infrastructure:

| Component | Role |
|-----------|------|
| **prismCortex** | Persistent vector seed store for forbidden-pattern corpus |
| **prismRAG** | Taxonomy-aware graph retrieval — categories, Tier-1 rules, dual vectors |
| **prismLib** | In-process runtime cache, warm corpus load |
| **PrismGuard runtime** | New: normalize → rules → classifier → fusion → judge → decision |

This composability reduced build time and aligned PrismGuard with the broader **Prism AI stack** (ChorusGraph orchestration, PrismRAG retrieval, PrismCortex memory).

### Request-time pipeline

```
Incoming prompt
  → Normalize (unicode NFKC, strip obfuscation, zero-width chars)
  → Tier-1 structural rules (fast block/allow)
  → ONNX classifier (prism-pi-v1) — runs on every request in classifier-first mode
  → Taxonomy fusion (prismRAG signals combined with classifier scores)
  → Gray zone policy (block, allow, or escalate)
  → Optional LLM Judge (only uncertain cases)
  → ALLOW → your LLM  |  BLOCK → audit log with resolution_gate
```

### Key technical decisions

1. **resolution_gate enum** — Every decision maps to a named gate (`tier1_rule`, `guard_model_first`, `fusion_block`, `llm_judge`, etc.). This is the engineering answer to the Slack score debate.

2. **Classifier-first mode** — ONNX runs synchronously before expensive paths. Measured: classifier calls on ~100% of traffic; judge calls on ~7% on law bench.

3. **Rules-first product profiles** — `create_checker_for_app("web_chat")` for hubs and marketing chat. ONNX requires explicit `PRISMGUARD_USE_ONNX=1`. Prevents a 705 MB download surprise.

4. **Shadow ONNX** — Rules enforce in production; ONNX runs in log-only mode for calibration. Lets teams tune before flipping enforcement.

5. **Domain packs** — Law, healthcare, finance overlays with holdout eval sets. Law is verified; others are roadmap with honest disclosure.

6. **Multi-artifact ONNX** — `PRISMGUARD_ARTIFACT_ID` swaps models: `prism-pi-v1` (law-bench), `prism-pi-hub-v1` (when gated), customer-trained artifacts.

7. **Customer train loop (v0.1.6)** — Opt-in `PRISMGUARD_FEEDBACK_PERSIST=1` → `prismguard feedback export` → `prismguard-model train --domain-pack general`. Any vertical can improve the model on their own traffic.

8. **Benchmark harness** — Reproducible 4-stack factorial evaluation (PrismGuard vs LLM Guard vs LangGraph vs LangChain patterns) on cold holdout — attacks never seen in training.

9. **Output-side scan** — Post-generation exfil detection (URLs, base64) exists in library; separate from input `check()` path.

10. **ChorusGraph integration** — `make_guard_handler()` writes `resolution_gate` and `blocked` into graph state before retrieve/LLM nodes.

### Version milestones

**v0.1.5 — Dogfood1:** Hardened on insightits.com hub. Rules-first web_chat profile. ONNX opt-in only. Offline rules path for air-gapped installs.

**v0.1.6 — OnnxCustomer1:** Feedback export, any-domain train path, multi-artifact support. Law remains published proof domain; product is domain-agnostic.

---

## Chapter 6 — Proof we publish (honest)

### Law cold holdout benchmark

Prompts in the holdout set were **never** in training or seed data. Same framework compared against LLM Guard.

| Metric | PrismGuard | LLM Guard |
|--------|:----------:|:---------:|
| Attack holdout block (n=14) | **14/14 (100%)** | 9/14 (64%) |
| Normal holdout allow (n=25) | **25/25** | 25/25 |
| Expanded normal (n=43) | **43/43** | — |
| Mean latency | **211 ms** | 353 ms |

**How to say it in marketing:** Plus thirty-five point seven percentage points more holdout attacks blocked; one hundred percent normal pass; lower mean latency on law bench.

**What not to say:** "Beats all attacks." "Enterprise certified." "Healthcare and finance ready." Holdout n is fourteen — strong delta, small sample. Pair with methodology, not hype.

Law is the **verified benchmark domain**, not the product boundary. The firewall works across verticals via rules, packs, and customer training.

---

## Chapter 7 — Marketing strategy (how we launched it)

### Separate funnel from ChorusGraph

Insight IT builds two hero products with different buyers:

| | ChorusGraph | PrismGuard |
|---|-------------|------------|
| Buyer | Platform engineers, devtool founders | AppSec, compliance, production agent teams |
| Pain | LLM cost, LangGraph ops tax | Cannot explain blocks to auditors |
| Proof | Azure benchmarks vs LangGraph | Law holdout vs LLM Guard + resolution_gate |
| Channel | Angel DMs, OSS tutorials | Product Hunt, LinkedIn, security communities |

Mixing both messages in one cold email dilutes both. PrismGuard has its own GTM path.

### Messaging framework (Hormozi method)

**Pain → Proof → Plan → Named CTA**

- **Pain:** Prompt injection in prod; teams debating guard scores in Slack
- **Proof:** Cold holdout numbers + resolution_gate demo
- **Plan:** pip install → doctor → check
- **CTA:** Guardrail Autopsy (free 30 min) — not vague "contact us"

### Engineer-first launch copy

The winning LinkedIn and X post did not open with the brand name. It opened with a lived production moment:

*"Prompt injection in prod — and your team is still debating guard scores in Slack."*

Tagline for broader channels: **"Know which rule fired — not 0.87 and a shrug."**

### Visual marketing

The launch flyer used a **retro terminal / hacker aesthetic** — dark grid background, split panel showing "Most guards: 0.87 ???" versus "PrismGuard: resolution_gate: tier1_rule". Deliberately not generic corporate security teal. Matched the engineer audience.

### Channels executed (July 2026)

1. **LinkedIn** — Short post + terminal flyer + pinned comment thread with technical use cases
2. **X (Twitter)** — Adapted shorter caption + same flyer + reply thread
3. **Product Hunt** — Scheduled launch with tagline, description, topics (Developer Tools · Security · Artificial Intelligence), maker first comment inviting feedback on false positives and wiring points

### Distribution pipeline (next)

- Show HN (Monday 9am Pacific — separate from Product Hunt day)
- Reddit staggered (r/LangChain, r/LocalLLaMA, r/Python)
- dev.to tutorial
- LangChain Discord showcase
- Awesome-list PRs (week 2)

### Monetization funnel

```
OSS discovery (PyPI, GitHub, PH)
  → Guardrail Autopsy (free, 30 min)
    → Domain Production Pilot (~$25k)
      → Recurring sidecar ($199–699/mo)
```

Pre-revenue today. Alpha on PyPI. Strategic value is high as compliance layer on Prism stack; dollar capture starts at first paid pilot.

---

## Chapter 8 — Competitive positioning

| Alternative | Model | PrismGuard contrast |
|-------------|-------|-------------------|
| **LLM Guard** | OSS toolkit, BYO classifier | Opinionated firewall + built-in ONNX + audit gates |
| **Lakera / Protect AI** | Commercial SaaS | Self-hosted, no default third-party scan |
| **AgentArmor** | 8-layer agent framework | PrismGuard is focused firewall — explainable input guard, not full agent OS |
| **Cloud AI gateways** | Platform bundle | Independent, swappable on ChorusGraph bus |

**Positioning line:** Complement the ecosystem — PrismGuard is the firewall layer when security and compliance must explain every decision.

---

## Chapter 9 — Use cases (where teams wire it)

1. **Agent entry node** — Check user input before LangGraph or custom agent calls tools
2. **RAG chunk gate** — Scan retrieved PDF/email chunks before synthesis (indirect injection)
3. **Website / product chat** — `web_chat` profile, rules-only, dogfooded on Insight IT hub
4. **HTTP sidecar** — `prismguard serve` in front of chatbot fleet
5. **Regulated copilots** — `law_pilot` + ONNX opt-in for domain-calibrated enforcement
6. **ChorusGraph stack** — Guard node + Route Ledger for full compliance story

---

## Chapter 10 — What we admit (builds trust)

- **Alpha** on PyPI — not enterprise certified
- **Law domain** is where cold-holdout proof is published; other domains via packs and customer training
- **prism-pi-v1 ONNX** is law-bench oriented; hub/general ONNX only after false-positive gates pass
- **705 MB model download** — explicit opt-in, never default
- **Holdout n=14** — reproducible harness, small attack set
- **Website product page** was pending at launch (GitHub as primary URL)
- **No paying customers cited** at launch — honest early-stage positioning

Transparency on limitations increases perceived likelihood for technical buyers more than overclaiming.

---

## Chapter 11 — The founder narrative (for NotebookLM tone)

Amin Parva built PrismGuard at Insight IT Solutions because the team kept shipping AI features faster than they could defend them in audits.

They did not set out to build another AI safety startup pitch. They set out to fix a specific, boring, expensive problem: **security logs that do not explain themselves.**

The terminal aesthetic, the pip install, the cold holdout numbers, the honest alpha label — all deliberate. The buyer is an engineer or AppSec lead who has been burned by black-box scores.

PrismGuard is the firewall layer the LLM stack should have had from the beginning. The marketing is not "AI will save you." The marketing is: **install it, run check, read resolution_gate, know which rule fired.**

That is the story.

---

## Appendix — Quick facts for NotebookLM Q&A

**Install:** `pip install "prismguard[prism,guard-model]==0.1.6"`

**GitHub:** github.com/insightitsGit/PrismGuard

**PyPI:** pypi.org/project/prismguard/0.1.6/

**License:** Apache-2.0

**Key API:** `create_checker_for_app("web_chat")` → `checker.check(prompt)` → `result.resolution_gate`

**Benchmark headline:** 14/14 vs 9/14 LLM Guard attacks blocked; 211ms vs 353ms mean latency

**Lead magnet:** Guardrail Autopsy (30 min)

**Company:** Insight IT Solutions LLC · insightits.com

**Stack siblings:** ChorusGraph (agents), PrismRAG (retrieval), PrismCortex (memory), PrismLib (cache)

---

*End of NotebookLM source document. Upload this file plus optional: README.md from GitHub, prismguard-linkedin-post.md, PRISMGUARD_PRODUCT.md for richer audio overview.*
