# Handoff LandingPage1 — Build the PrismGuard product landing page (shine)

**ID:** HO-LandingPage1  
**Director:** Amin  
**To:** landing-page agent (InsightitsAIAgent or dedicated marketing/frontend project)  
**Priority:** P0 — GTM surface  
**Status:** Ready for QA (see handoffbackLandingPage1.md)  
**Date issued:** 2026-07-09  
**Source product repo:** `C:\code\PrismGaurd` (GitHub: [insightitsGit/PrismGuard](https://github.com/insightitsGit/PrismGuard))  
**Cross-repo target:** `C:\code\InsightitsAIAgent` (or new `prismguard-landing/` scaffold — match how PrismCortex / ChorusGraph landings live)  
**Marketing playbook:** `C:\code\alex-hormozi.md` (Hormozi Value Equation + Grand Slam Offer — **read and apply**)  
**Supersedes / extends:** `handoffs/handoffLandingPage.md` (business model + SKUs still valid; this handoff is the **full creative + build brief**)

> **Receiving agent:** set Status → `In Progress` while working. When done, write `handoffs/handoffbackLandingPage1.md` in *this* PrismGuard repo (or mirror path in your project) with Status → `Ready for QA`. Ship a live local URL + generated image assets. Do not invent benchmark numbers — only cite sources below.

---

## 0. Mission

Create a **conversion-grade product landing page** that makes PrismGuard feel inevitable for the primary buyer: a security / compliance / platform lead who needs **auditable allow/block decisions** in front of production LLMs — not another opaque scanner score.

The page must:

1. Sell the **dream outcome** (Hormozi), not a feature dump.
2. Include **every canonical link** (GitHub, PyPI, docs, install).
3. Use **honest proof** from law-domain benchmarks.
4. Generate **original graphical assets** (hero, architecture, audit/decision visual, social OG) so the product *shines*.
5. Wire **pricing SKUs** and CTAs into the Insightits catalog pattern if that is where landings live.

---

## 1. Canonical product facts (do not invent)

### 1.1 Identity

| Field | Value |
|-------|--------|
| Product name | **PrismGuard** |
| One-liner | Open-source **prompt-injection firewall** for production LLM apps — every decision is auditable |
| Tagline options | “Protect your LLM before malicious prompts ever reach it.” · “Audited allow/block — not a black-box score.” |
| License | Apache-2.0 open core |
| Version (live) | **0.1.4** (PyPI) |

### 1.2 Links (must appear on page)

| Asset | URL |
|-------|-----|
| **GitHub** | https://github.com/insightitsGit/PrismGuard |
| **PyPI** | https://pypi.org/project/prismguard/ |
| **PyPI pin** | https://pypi.org/project/prismguard/0.1.4/ |
| **Docs (design)** | https://github.com/insightitsGit/PrismGuard/blob/master/docs/prismguard-design.md |
| **Integration guide** | https://github.com/insightitsGit/PrismGuard/blob/master/docs/integration-guide.md |
| **Enterprise / SKUs** | https://github.com/insightitsGit/PrismGuard/blob/master/docs/enterprise-product-model.md |
| **User updates** | https://github.com/insightitsGit/PrismGuard/blob/master/docs/user-updates.md |
| **CI** | https://github.com/insightitsGit/PrismGuard/actions/workflows/ci.yml |
| **ONNX model release** | https://github.com/insightitsGit/PrismGuard/releases/tag/v0.1.2 |
| **ChorusGraph** (partner) | https://github.com/insightitsGit/ChorusGraph |

### 1.3 Install copy (copy-paste blocks on page)

**Recommended (full classifier):**

```bash
pip install "prismguard[prism,guard-model]==0.1.4"
prismguard-model download
prismguard init --domain law
prismguard check "your prompt here"
```

**Minimal (rules path):**

```bash
pip install prismguard==0.1.4
```

**Verify:**

```bash
prismguard doctor
prismguard eval self-check
```

**Business HTTP sidecar** (paid tier — mention, don’t pretend it’s free):

```bash
pip install "prismguard[serve,enterprise,prism,guard-model]"
# requires PRISMGUARD_LICENSE_FILE for production
prismguard-serve
# POST /v1/check  ·  POST /v1/scan-output  ·  GET /metrics
```

### 1.4 What the product actually does

- Sits **in front of the LLM** (and can scan **assistant output** for exfil patterns).
- Pipeline: structural rules → taxonomy / fusion → local **ONNX** classifier (`prism-pi-v1`) → optional LLM Judge on gray zone.
- Every decision exposes **`resolution_gate`** + **`decision_source`** for compliance logs.
- Self-hosted: traffic stays on customer infra by default (no OpenAI required for classifier path).
- Law domain pack verified; healthcare/finance **not** claimed ready.

### 1.5 Proof stats (cite only these; refresh from repo if regenerating)

Source: `benchmark/law/results/current/COMPARISON_REPORT.md` in PrismGuard repo.

| Metric | PrismGuard | LLM Guard | Notes for copy |
|--------|------------|-----------|----------------|
| Attack holdout block (n=14) | **14/14 (100%)** | 9/14 (64.3%) | Law cold holdout — not “beats all scanners forever” |
| Normal holdout allow (HTTP, n=25) | **25/25** | **25/25** | |
| Expanded normal holdout (n=43) | **43/43** | — | |
| Mean latency (CPL vs CGL) | **~211 ms** | ~353 ms | ONNX law path |
| Judge escalation | ~7% of traffic (law bench) | — | Cost story: rare escalation |

**Safe claim framing:** “On our legal cold-holdout benchmark, PrismGuard blocked 100% of attack cases vs 64.3% for LLM Guard, with lower mean latency — and every decision is auditable.”

**Forbidden claims:** healthcare/finance ready · holdout YAML as a customer runtime feature · “enterprise-ready without pilot” · fake logos · fake customer counts.

### 1.6 Pricing SKUs (pre-validation — label as estimates)

| SKU | Price | Includes |
|-----|-------|----------|
| `prismguard` (OSS) | $0 | Library, ONNX path, CLI, law pack, ChorusGraph guard node helper |
| `prismguard-team` | ~$199/mo | pgvector persistence, feedback persistence, calibration exports |
| `prismguard-business` | ~$699/mo | `prismguard serve`, OpenAI Judge option, tenant lexicon, Redis session hooks, `/metrics` |
| `prismguard-pilot` | ~$25k one-time | Design partner: custom lexicon, security pack, SLA, ChorusGraph co-integration |

Comment in code: `// pre-validation estimate — see docs/enterprise-product-model.md`

**Do not collapse** PrismGuard price into ChorusGraph. Cross-sell: “Works natively with ChorusGraph.”

---

## 2. Hormozi strategy (mandatory — from `alex-hormozi.md`)

Apply Section 8 of the playbook. Do **not** lead with patents, ONNX trivia, or “we have fusion.” Lead with **pain → proof → plan → named CTA**.

### 2.1 Primary avatar (one funnel)

| Field | Value |
|-------|--------|
| Title | Head of Security / AI Platform Lead / Compliance Eng (legal AI or enterprise copilots) |
| Company | B2B SaaS or legal-tech with LLM features in production or pilot |
| Bleeding pain | Prompt injection / jailbreak risk + **cannot explain blocks to auditors**; fear of data exfil via model output; toolkit scanners that return scores without an allow/block policy |
| Economic buyer | Often CISO / VP Eng / Head of Platform (if avatar ≠ buyer, CTA must help them sell upward) |

### 2.2 Dream outcome

```
Dream outcome: Ship an auditable prompt-injection firewall in front of your LLM
               so every allow/block is defensible in a compliance review —
               without sending prompts to a third-party scanner SaaS.
Time horizon:  first useful check in <15 minutes; pilot evidence in 14 days
Success metric: attack holdout blocked; normal traffic allowed; resolution_gate
               present on 100% of decisions; optional HTTP sidecar for polyglot stacks
```

### 2.3 Value Equation scores (starting point for copy)

| Lever | Score (1–10) | How the page must improve it |
|-------|--------------|------------------------------|
| Dream Outcome | 8 | Lead with audit + risk reduction, not “ONNX” |
| Perceived Likelihood | 5 → fix | Benchmark table, CLI demo GIF/video, `pip` in 3 commands, GitHub stars/CI badge |
| Time Delay | 7 | “Install → doctor → check” in one section |
| Effort & Sacrifice | 6 → fix | Copy-paste install; ChorusGraph one-liner; Business HTTP for non-Python |

**Weakest levers to fix on the page:** Likelihood (proof + demo) and Effort (install friction).

### 2.4 Grand Slam Offer naming

| Stage | Offer name | Price | CTA |
|-------|------------|-------|-----|
| Lead magnet | **Guardrail Autopsy** (free 30-min) | $0 | “Book a Guardrail Autopsy” |
| Entry | OSS install | $0 | “Install with pip” → GitHub/PyPI |
| Paid wedge | **Law Domain Production Pilot** | ~$25k | “Apply for Pilot” |
| Recurring | Team / Business | $199 / $699 | “Start Team” / “Start Business” |

**Pilot stack (value anchors — illustrative for landing, not invoices):**

| Component | Solves | Value anchor (marketing) |
|-----------|--------|--------------------------|
| Shadow-mode / staging deploy of PrismGuard | “Won’t work here” | $8k |
| Law domain pack + custom lexicon pass | Domain false positives | $6k |
| Audited decision log design (`resolution_gate`) | Compliance objection | $5k |
| ChorusGraph or HTTP sidecar wiring | Integration hell | $4k |
| 90-day Slack + SLA | Support fear | $3k |
| **Total stack** | | **~$26k** |
| **Pilot price** | | **~$25k** |

**Conditional guarantee (honest):** “If we cannot produce a staging report with `resolution_gate` on every decision and green `prismguard eval self-check` within 14 days of kickoff, refund the pilot fee — you keep the configs.”

### 2.5 Pain → Proof → Plan (page spine)

**Pain**

> Your LLM is one jailbreak away from leaking matter data or ignoring policy — and your current scanner only gives a probability. When security asks *why* a prompt was blocked, nobody has an audit trail.

**Proof**

> On our legal cold-holdout benchmark: 14/14 attacks blocked, 43/43 expanded normals allowed, ~211 ms mean path — and every decision exposes `resolution_gate`. Open source on GitHub. Live on PyPI as `prismguard` 0.1.4.

**Plan**

1. `pip install "prismguard[prism,guard-model]==0.1.4"` + `prismguard-model download`  
2. `prismguard init --domain law` → `prismguard check "…"`  
3. Book a **Guardrail Autopsy** or apply for the **Law Domain Production Pilot**

**CTAs (named — never “Contact us” alone)**

- Primary: **Install with pip** (scroll to install / open PyPI)
- Secondary: **Book a Guardrail Autopsy**
- Tertiary: **View on GitHub**
- Enterprise: **Apply for Law Domain Pilot**

### 2.6 Channels (recommend on page footer / GTM notes)

Start with 2: **Product-led** (PyPI + GitHub) + **Outbound / LinkedIn** to legal-AI and platform leads. Partnerships: ChorusGraph co-sell.

---

## 3. Page structure (required sections)

Build **one composition** for the first viewport (not a dashboard). Follow Insightits / Cursor frontend taste: brand-first hero, expressive type, atmospheric background, full-bleed hero visual, **no card soup in the hero**, one job per section.

### Section map

1. **Hero** — Brand **PrismGuard** as the dominant word. One headline. One supporting sentence. CTA group: Install · Autopsy · GitHub. Full-bleed generated hero image (see §5).
2. **Pain** — Avatar-specific (legal AI / enterprise copilots / RAG).
3. **How it works** — 3 steps max + architecture graphic.
4. **Proof** — Benchmark table + latency + auditability (`resolution_gate` callout with sample CLI output).
5. **Install** — pip blocks + PyPI + GitHub links (prominent).
6. **Why not “just LLM Guard”?** — Positioning table from README (firewall vs toolkit) — honest, complementary.
7. **Integrations** — ChorusGraph `make_guard_handler()`, LangGraph mention, Business `POST /v1/check` + `/v1/scan-output`.
8. **Pricing** — 4 SKUs with estimate disclaimer.
9. **How updates work** — pip / seed / model; holdout is eval-only (copy from enterprise doc).
10. **Prism stack** — ChorusGraph · PrismGuard · PrismRAG · PrismCortex · PrismLib (links).
11. **FAQ** — ONNX download, self-host, no OpenAI by default, pilot vs OSS.
12. **Final CTA** — Autopsy + Install + Pilot.

### SEO / meta

- Title: `PrismGuard — Audited Prompt-Injection Firewall for Production LLMs`
- Description: include “self-hosted”, “resolution_gate”, “PyPI”, “Apache-2.0”
- OG image: generated (see §5)
- Canonical URLs to GitHub + PyPI

### Catalog wiring (if InsightitsAIAgent)

- `productDeployPrices.js` — SKUs from §1.6  
- `PRISMGUARD_EXTERNAL` in `productVerticalAIContent.js` — GitHub + PyPI **0.1.4** (verified live)  
- Pricing narrative: OSS / Team / Business / Pilot as in `handoffLandingPage.md` Part A

---

## 4. Sample UI copy (starting point — rewrite for voice)

**Headline:** Stop prompt injection before it reaches your LLM — with a decision you can defend.

**Sub:** PrismGuard is a self-hosted firewall that returns allow/block plus an audit `resolution_gate` on every request. Open source. ONNX-powered. Built for legal and enterprise copilots.

**CLI proof strip (use real style):**

```text
BLOCKED
resolution_gate=guard_model_first
matched_category=direct_instruction_override
confidence=0.9124
```

---

## 5. Graphical assets (REQUIRED — generate, don’t skip)

Generate **original** marketing visuals (image model / design tool). Export to the landing project’s `public/` or `docs/assets/` and reference from the page. Prefer PNG/WebP for photo-like heroes; SVG for diagrams if crisp.

| Asset ID | Spec | Purpose |
|----------|------|---------|
| `hero-prismguard` | 16:9 or 21:9, full-bleed. Dark atmospheric scene: luminous “firewall” plane between a user prompt stream and an LLM core. Brand word **PrismGuard** readable in-frame or as page type over image. **No** purple-on-white cliché; avoid cream+terracotta AI default. Cool slate / steel / electric cyan accents OK if distinctive. | Hero background |
| `architecture-flow` | Clean horizontal pipeline: User → PrismGuard (Rules / ONNX / Judge) → ALLOW→LLM / BLOCK→Audit. Match product truth. | How it works |
| `audit-decision` | Visual of a decision ticket: ALLOW/BLOCK + `resolution_gate=…` — compliance-friendly, not cyber-l33t. | Proof section |
| `og-social` | 1200×630, brand + one line + “pip install prismguard” | Open Graph / Twitter |
| `icon-mark` | Simple mark for favicon / nav (shield + prism facet or firewall glyph — original) | Brand |

**Also reuse if helpful (repo already has):**

- `https://raw.githubusercontent.com/insightitsGit/PrismGuard/master/docs/assets/hero.png` (if present)
- `docs/assets/architecture.svg` / `hero.svg` in repo — may regenerate higher quality for marketing

**Motion (ship 2–3 intentional):** hero fade/parallax subtle; CTA hover; proof numbers count-up once. No noise animations.

---

## 6. Design constraints (hard)

- First viewport = **one composition**: brand, one headline, one sentence, CTA group, dominant image.
- Brand test: remove nav — still obviously PrismGuard.
- No hero card grid, no floating badge stickers on the hero image.
- Cards only where interaction needs a container (pricing tiers OK).
- Mobile + desktop.
- Accessibility: contrast, alt text on all generated images, keyboard CTAs.

---

## 7. Tasks checklist

### T1 — Strategy freeze
- [ ] Fill Hormozi Section 8 block into `handoffbackLandingPage1.md` (avatar, offer, guarantee).
- [ ] Confirm PyPI 0.1.4 + GitHub URLs resolve.

### T2 — Generate graphics
- [ ] Produce all assets in §5; commit to landing project.
- [ ] Wire hero + OG + architecture into page.

### T3 — Build landing page
- [ ] Implement §3 section map with Hormozi spine.
- [ ] Install + GitHub + PyPI highly visible.
- [ ] Pricing + Pilot CTA + Autopsy CTA.

### T4 — Catalog / prices (InsightitsAIAgent)
- [ ] `productDeployPrices.js` SKUs.
- [ ] `PRISMGUARD_EXTERNAL` with live links.

### T5 — QA pass
- [ ] No forbidden claims (§1.5).
- [ ] Lighthouse / mobile smoke.
- [ ] Local URL in handback.

---

## 8. Acceptance criteria

- [ ] Landing page live locally (and staged if your project has deploy).
- [ ] GitHub + PyPI + pip install blocks present above the fold or one scroll.
- [ ] Hormozi Pain → Proof → Plan → named CTAs visible.
- [ ] ≥4 generated graphical assets shipped and used.
- [ ] Pricing SKUs match enterprise model (estimate disclaimer).
- [ ] Benchmark numbers match COMPARISON_REPORT (or regenerated with citation).
- [ ] Handback written with screenshots or URLs.

---

## 9. Hand back (`handoffbackLandingPage1.md`)

Include:

- Status: Ready for QA / Blocked  
- Local URL + paths to generated images  
- Hormozi Section 8 filled for PrismGuard  
- Files changed in InsightitsAIAgent (or landing scaffold)  
- Link verification (GitHub, PyPI 0.1.4)  
- Deviations  
- Suggested Director review (copy tone, pilot CTA destination)

---

## 10. Reference reading (receiving agent)

| Doc | Why |
|-----|-----|
| `C:\code\alex-hormozi.md` | Offer + messaging framework |
| `C:\code\PrismGaurd\README.md` | Product truth + install |
| `C:\code\PrismGaurd\docs\enterprise-product-model.md` | SKUs + claim discipline |
| `C:\code\PrismGaurd\docs\integration-guide.md` | Embed / HTTP / ChorusGraph |
| `C:\code\PrismGaurd\benchmark\law\results\current\COMPARISON_REPORT.md` | Proof numbers |
| `C:\code\PrismGaurd\handoffs\handoffLandingPage.md` | Prior business-model tasks |
| https://pypi.org/project/prismguard/0.1.4/ | Live package |
| https://github.com/insightitsGit/PrismGuard | Source |

---

*LandingPage1 · make PrismGuard shine: Hormozi offer + audited firewall story + pip/GitHub everywhere + generated visuals · PyPI 0.1.4 is live · do not invent customers or healthcare claims.*
