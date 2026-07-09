# Handback — LandingPage1 (PrismGuard product landing)

**ID:** HO-LandingPage1  
**From:** landing-page agent (InsightitsAIAgent)  
**To:** Director Amin  
**Status:** Ready for QA  
**Date:** 2026-07-09  

---

## Local URL

- **Landing:** http://localhost:5173/products/prismguard.html  
- Dev server: `npm run dev` in `C:\code\InsightitsAIAgent`

---

## Generated image assets

| Asset ID | Path |
|----------|------|
| `hero-prismguard` | `InsightitsAIAgent/public/images/NewDesign/prismguard/hero-prismguard.png` |
| `architecture-flow` | `InsightitsAIAgent/public/images/NewDesign/prismguard/architecture-flow.png` |
| `audit-decision` | `InsightitsAIAgent/public/images/NewDesign/prismguard/audit-decision.png` |
| `og-social` | `InsightitsAIAgent/public/images/NewDesign/prismguard/og-social.png` |
| `icon-mark` | `InsightitsAIAgent/public/images/NewDesign/prismguard/icon-mark.png` (+ nav logo copy at `logos/prismguard-logo-text.png`) |

All five §5 assets generated and wired into the page (hero, how-it-works, proof, OG meta, favicon/nav).

---

## Hormozi Section 8 (filled for PrismGuard)

### Avatar
- **Title:** Head of Security / AI Platform Lead / Compliance Eng (legal AI or enterprise copilots)
- **Company:** B2B SaaS or legal-tech with LLM features in production or pilot
- **Bleeding pain:** Prompt injection / jailbreak risk + cannot explain blocks to auditors; fear of data exfil via model output; toolkit scanners that return scores without allow/block policy
- **Economic buyer:** Often CISO / VP Eng / Head of Platform — CTAs help sell upward (Autopsy + Pilot)

### Dream outcome
```
Dream outcome: Ship an auditable prompt-injection firewall in front of your LLM
               so every allow/block is defensible in a compliance review —
               without sending prompts to a third-party scanner SaaS.
Time horizon:  first useful check in <15 minutes; pilot evidence in 14 days
Success metric: attack holdout blocked; normal traffic allowed; resolution_gate
               present on 100% of decisions; optional HTTP sidecar for polyglot stacks
```

### Value Equation (page fixes)
| Lever | Score | Page treatment |
|-------|-------|----------------|
| Dream Outcome | 8 | Hero leads with defendable allow/block, not ONNX trivia |
| Perceived Likelihood | 5→↑ | Benchmark table + CLI proof + count-up metrics + GitHub/PyPI/CI |
| Time Delay | 7 | Install → doctor → check section with copy-paste blocks |
| Effort & Sacrifice | 6→↑ | Full/minimal/verify pip blocks; ChorusGraph snippet; Business HTTP |

### Grand Slam Offer
| Stage | Offer | Price | CTA on page |
|-------|-------|-------|-------------|
| Lead magnet | Guardrail Autopsy (30-min) | $0 | Book a Guardrail Autopsy |
| Entry | OSS install | $0 | Install with pip |
| Paid wedge | Law Domain Production Pilot | ~$25k | Apply for Pilot |
| Recurring | Team / Business | ~$199 / ~$699 | Start Team / Start Business |

**Conditional guarantee (on page):** If staging report with `resolution_gate` on every decision + green `prismguard eval self-check` not delivered within 14 days of kickoff, refund pilot fee — configs kept.

---

## Files changed (InsightitsAIAgent)

### Created
- `products/prismguard.html`
- `src/pages/products/prismguard-landing/PrismGuardLanding.jsx`
- `src/pages/products/prismguard-landing/prismguardFaq.js`
- `src/pages/products/prismguard-landing/prismguardCodeExamples.js`
- `public/images/NewDesign/prismguard/*` (5 assets)
- `public/images/NewDesign/logos/prismguard-logo-text.png`

### Catalog / routing / nav
- `src/pages/products/productCatalog.js` — `PRODUCT_CATALOG.prismguard` + full `PRISMGUARD_EXTERNAL` (GitHub spelling fixed to PrismGuard)
- `src/pages/products/productDeployPrices.js` — SKUs (already present; pilot name aligned)
- `src/pages/products/productVerticalAIContent.js`
- `src/pages/products/productSeo.js` + `src/seo/seoCtr.js` + `src/seo/technicalKeywords.js`
- `src/pages/products/real-estate-landing/product-landing-main.jsx`
- `src/pages/products/navProductGroups.js`
- `public/product-groups.js`
- `public/hero-grouped-rotator.js`
- `vite.products.config.js` + `scripts/prepare-product-build.js`
- `index.html` — hero card `--17`, stack copy, FAQ schema text
- `sitemap.xml`, `llms.txt`, `ai-info.txt`, `public/aeo/faq-schema.json`
- `docs/prism-family-reference.md`

### Backend / shop
- `meeting-scheduler/website_hub/kb/product_catalog.py` — product + Team/Business/Pilot SKUs
- `meeting-scheduler/website_hub/kb/education_blocks.py`
- `meeting-scheduler/services/startup_seeder.py`

### Tests
- `tests/test_product_landing_external_links.js`
- `scripts/check-product-landing-urls.mjs`

---

## Link verification (2026-07-09)

| URL | Status |
|-----|--------|
| https://github.com/insightitsGit/PrismGuard | 200 |
| https://pypi.org/project/prismguard/0.1.4/ | 200 |
| Catalog verify (`npm run verify:products`) | OK prismguard |
| External links unit test | OK |

---

## Page sections shipped (§3)

1. Hero (brand-first, full-bleed generated image, Install / Autopsy / GitHub)  
2. Pain  
3. How it works (+ architecture graphic + 3 steps)  
4. Proof (benchmark table, count-up, audit visual, CLI `resolution_gate`)  
5. Install (full / minimal / verify + PyPI / GitHub / CI / ONNX)  
6. Why not “just LLM Guard?”  
7. Integrations (ChorusGraph `make_guard_handler`, Business serve)  
8. Pricing (4 SKUs + pilot value stack + guarantee)  
9. How updates work  
10. Prism stack  
11. FAQ  
12. Final CTA  

Motion: hero fade-in, CTA hover, proof count-up once.

---

## Deviations

1. SEO title uses ASCII hyphen (`PrismGuard - Audited…`) to avoid Windows encoding mojibake in sync script; handoff preferred em dash — content intent matches.  
2. Autopsy CTA routes to `/#contact?utm_…=guardrail_autopsy` (same pattern as ChorusGraph Agent Stack Audit) — no dedicated Calendly event yet.  
3. Team/Business/Pilot are mailto / contact CTAs (pre-validation estimates); no Stripe checkout wiring yet (unlike PrismCortex).  
4. Homepage hero card count is now 18 platform+vertical widgets (added card 17); Risk Management rotator index shifted to 18.  
5. Local page briefly shows “Loading…” while `/api/products` times out / falls back to catalog — expected when Flask is not running; catalog fallback renders full landing.

---

## Suggested Director review

1. Copy tone on hero subhead vs pain section (Hormozi spine).  
2. Pilot CTA destination — keep mailto vs dedicated form / Calendly for Guardrail Autopsy.  
3. Whether to regenerate a text-logo PNG (current nav mark is the shield icon) for shop grids that expect “logo-text” wordmarks.  
4. Deploy to Azure when ready (not deployed in this handback — awaiting confirmation).

---

## Acceptance checklist

- [x] Landing live locally  
- [x] GitHub + PyPI + pip install above fold / one scroll  
- [x] Pain → Proof → Plan → named CTAs  
- [x] ≥4 generated graphical assets shipped and used (5)  
- [x] Pricing SKUs match enterprise model with estimate disclaimer  
- [x] Benchmark numbers match COMPARISON_REPORT citation  
- [x] Handback written with local URL + asset paths  

*PrismGuard landing shines: Hormozi offer + audited firewall story + pip/GitHub everywhere + generated visuals · PyPI 0.1.4 verified live.*
