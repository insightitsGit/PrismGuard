# PrismGuard — distribution channel research

**Saved:** 2026-07-09  
**Trigger:** LinkedIn + X posted · Product Hunt + community launch **tomorrow (2026-07-10)**  
**Product:** PrismGuard v0.1.6 · PyPI + GitHub live · website **404** (gap)

---

## Executive summary

| Priority | Channel | Why | Effort | Best day |
|----------|---------|-----|--------|----------|
| **P0** | **Product Hunt** | Dev discovery burst; one shot per 6mo | High prep | **Tue/Wed** ideal · Fri OK if ready |
| **P0** | **Hacker News (Show HN)** | Engineer trust; free; technical audience | Medium | Any weekday **8–10am PT** |
| **P1** | **Reddit** (targeted subs) | Prompt-injection / RAG devs | Low per sub | Stagger 1/day |
| **P1** | **dev.to** | SEO + dev feed; tutorial format | Medium | Same week |
| **P1** | **LangChain / LangGraph Discord** | Exact integration avatar | Low | After 1-min tutorial link |
| **P2** | **Lobste.rs** | HN-adjacent, security-minded | Low | Invite or post |
| **P2** | **GitHub** (README pin + release note) | Converts traffic you already send | Low | Before PH |
| **P2** | **Awesome lists** (PR) | Long-tail discovery | Low | Week 2 |
| **P3** | **Indie Hackers / BetaList** | Smaller burst | Low | Optional |
| **Skip for now** | Angel DMs on PH day | ChorusGraph queue separate | — | — |

**Blocker before Product Hunt:** `insightits.com/products/prismguard.html` is **404**. PH traffic needs a landing that converts → **GitHub README as primary URL** until page ships, or ship page tonight.

---

## Product Hunt (P0)

### Is it right for PrismGuard?

**Yes** — OSS dev tool, pip install, terminal aesthetic, clear tagline. Not ideal as *revenue* play; ideal for **qualified dev signups + GitHub stars**.

### Timing (research-backed)

- Launch **12:01 AM Pacific** for full 24h homepage window
- **Tuesday or Wednesday** = highest traffic (Friday tomorrow is **OK** but weaker)
- First **2–4 hours** matter most (steady organic upvotes, no spike spam)
- Be online **24 hours** — reply every comment
- **One launch per product per ~6 months** — treat tomorrow as v0.1.6 “significant update” launch if first time

### PH listing prep (do tonight or tomorrow AM)

| Field | Draft |
|-------|-------|
| **Name** | PrismGuard |
| **Tagline** (60 chars) | `Self-hosted LLM guard — auditable blocks, not scores` (52) |
| **Alt tagline** | `Prompt-injection firewall for prod LLM apps` (44) |
| **Link** | https://github.com/insightitsGit/PrismGuard (until website live) |
| **Description** (500 chars) | PrismGuard is an open-source firewall for LLM applications. Drop it in front of your model to block prompt injection — every allow/block returns resolution_gate (which rule decided), not a probability score. Rules-first pip install, optional local ONNX, Apache-2.0. Cold holdout: 14/14 vs LLM Guard 9/14. Built for engineers shipping agents and RAG in production. |
| **Topics** | Developer Tools · Security · Open Source · Artificial Intelligence |
| **Gallery** (3+ images) | 1) Terminal flyer 2) `prismguard check` CLI screenshot 3) resolution_gate output / split 0.87 vs rule |
| **Maker comment** | Use engineer post hook + honest alpha + link to user-updates.md |
| **First comment** | pip install one-liner + 3 use cases |

### PH day checklist

- [ ] Schedule 12:01 AM PT (or launch manually at wake)
- [ ] Pin maker comment within 5 min
- [ ] Post X + LinkedIn **link to PH page** (not duplicate launch post)
- [ ] Reply every PH comment < 30 min
- [ ] Ask 5–10 dev friends for **honest** comments (not vote brigade)
- [ ] Do **not** mass-DM angels for upvotes

---

## Hacker News — Show HN (P0)

### Title format

`Show HN: PrismGuard – Self-hosted prompt-injection guard with auditable block/allow`

### Post body (link to GitHub)

Short technical post — HN hates marketing fluff:

```
PrismGuard is an Apache-2.0 firewall for LLM apps. Rules-first pip install; optional local ONNX.

Every check returns resolution_gate (which rule/layer decided) instead of a raw score — we got tired of debating 0.87 in incident channels.

Cold holdout benchmark (law domain, n=14 attacks never in training): 14/14 blocked vs 9/14 LLM Guard. Alpha; feedback export + train path in v0.1.6.

pip install "prismguard[prism,guard-model]==0.1.6"

Happy for feedback on false positives and where you'd wire this (agent entry vs RAG chunks).
```

### Timing

- **Weekday 8–10 AM Pacific** — best Show HN window
- **Friday tomorrow:** post **after** PH goes live OR **Monday** if PH is Friday (avoid splitting attention) — **recommendation: PH Friday, Show HN Monday 9am PT**

### Rules

- Respond fast to comments; be technical and humble
- Don't ask for upvotes
- Acknowledge alpha + small holdout n

---

## Reddit (P1) — stagger, don’t spam

Post **native text** + link in comment (many subs auto-remove link posts). **One sub per day.**

| Subreddit | Angle | Post style |
|-----------|-------|------------|
| **r/LangChain** | LangGraph entry-node guard | "How I added prompt-injection check before tools" |
| **r/LocalLLaMA** | Self-hosted, no cloud scan | ONNX opt-in, VPC-friendly |
| **r/MachineLearning** | Research-adjacent | Holdout methodology — **strict rules, may remove** |
| **r/cybersecurity** | AppSec angle | Indirect injection via RAG — **no hype** |
| **r/netsec** | Same, more technical | resolution_gate audit story |
| **r/Python** | pip install, OSS | "Released v0.1.6 – feedback welcome" |
| **r/artificial** | Broader AI | Lighter, problem-first |
| **r/selfhosted** | sidecar + local ONNX | `prismguard serve` |

**Avoid:** r/programming (Show HN overlap), posting same copy to 5 subs same day.

---

## dev.to (P1)

**Title:** Block prompt injection in prod — auditable guard with pip install

Format: short tutorial post (800–1200 words):
1. Problem (scores in Slack)
2. 5-min install
3. Python snippet `create_checker_for_app("web_chat")`
4. RAG chunk example
5. Honest limits (alpha, law proof domain)

Tag: `#ai` `#security` `#python` `#opensource`  
Cross-post link to PH when live.

---

## Discord / Slack communities (P1)

| Community | Action |
|-----------|--------|
| **LangChain Discord** | `#showcase` or security channel — 1 paragraph + link |
| **LangGraph** | Same when tutorial exists |
| **LlamaIndex** | After RAG chunk tutorial |
| **Hugging Face forums** | OSS guard category |
| **MLOps Community** | Slack — production guardrail thread |

**Rule:** Lead with code snippet, not pitch deck.

---

## GitHub hygiene (P2 — do before PH)

- [ ] Release notes for **v0.1.6** on GitHub Releases (if not already)
- [ ] README: 3-line "what is this" at top + pip install badge
- [ ] Pin issue or Discussion: "Show and Tell – v0.1.6 launch"
- [ ] Add topics: `prompt-injection` `llm-security` `firewall`

---

## Awesome list PRs (P2 — week 2)

| List | Repo |
|------|------|
| Awesome LLM Security | search GitHub `awesome-llm-security` |
| Awesome AI Agents | agent tool sections |
| Awesome Self-Hosted | if sidecar documented |
| Awesome Python | security subsection |

One PR per week; follow each repo's contribution rules.

---

## Optional / lower ROI

| Channel | Notes |
|---------|-------|
| **BetaList** | Free submit; small dev traffic |
| **Indie Hackers** | "Launch" post — builder story |
| **Lobste.rs** | Needs invite; security crowd |
| **Hashnode / Medium** | Mirror dev.to |
| **LinkedIn repost** | Link PH page day-of only |
| **Mastodon / Bluesky** | #InfoSec #LLM tags |

---

## NOT for this launch

- Nat, Bob, Jeff, Jared, Brianne angel DMs (ChorusGraph)
- Mass email blast
- Paid upvote services (PH bans)
- Claiming "enterprise certified"

---

## Recommended 7-day schedule

| Day | Action |
|-----|--------|
| **Fri 7/10** | Product Hunt 12:01am PT · PH maker comments · X/LinkedIn link to PH |
| **Fri 7/10** | GitHub release notes + README polish |
| **Mon 7/13** | Show HN 9am PT |
| **Tue 7/14** | r/LangChain + dev.to tutorial |
| **Wed 7/15** | r/LocalLLaMA or r/Python |
| **Thu 7/16** | LangChain Discord |
| **Week 2** | Awesome list PR · sidecar tutorial |

---

## Copy assets (ready)

| Asset | Path |
|-------|------|
| LinkedIn post | `kb/outreach/prismguard-linkedin-post.md` |
| X post | `kb/outreach/prismguard-x-post.txt` |
| Flyer | `kb/outreach/prismguard-linkedin-flyer.png` |
| PH description | This doc § Product Hunt |
| Show HN body | This doc § Hacker News |

---

## Open gaps (fix before PH if possible)

1. **Website 404** — use GitHub as PH link or deploy `prismguard.html`
2. **CLI screenshot** — take real `prismguard check` terminal shot for PH gallery
3. **PH gallery** — need 3 images (flyer + 2 screenshots)
