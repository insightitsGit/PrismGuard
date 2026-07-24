# Handoff: Next PrismGuard version — finance PI structural (fresh impl, no AWS)

**ID:** HO-PrismGuard-019  
**Project:** PrismGaurd (PrismGuard)  
**Date:** 2026-07-23  
**From:** Senior QA / Architect  
**To:** dev-agent (library / next release)  
**Priority:** P0  
**Status:** Pending  
**Supersedes for release packaging:** HO-015  
**Related:** BUG-PrismGuard-PI-001 · HO-016 · HO-018 (`domain_pilot`, separate)

## Director constraints (2026-07-23)

1. **Fresh implementation** for the **new package version** — do not merely “ship the QA patch as-is.” Re-implement cleanly in library style (tests, docs, changelog), using QA candidate as **evidence / reference only**.  
2. **No AWS / no FinancePackBench cloud spend** while doing this library work. Bench mid/AWS re-run is **out of scope** for this HO. Keep cost ≈ **$0**.  
3. **No LLM Judge** to claim PI 100% on the mid holdout.

## AWS cost — do not touch

| Fact | Detail |
|------|--------|
| Inventory | `C:\code\QA\projects\FinancePackBench\AWS-RESOURCE-INVENTORY.md` — status **$0 billable leftovers** (teardown 2026-07-23) |
| Pause note | `C:\code\QA\projects\FinancePackBench\AWS-PAUSE-LIBRARY-VERSION.md` |
| Hygiene | `AWS-COST-HYGIENE.md` — no new Aurora/KB/AgentCore/Lambda/Fargate for this HO |
| This HO | **Local / editable PrismGuard only** — pytest + fixture rescore on laptop |
| Forbidden | `provision-mid-*`, AgentCore deploy, Lane A AWS, any new tagged `Project=FinancePackBench` resources |

Optional verify after `aws sso login --sso-session insightits` (profile `default` / `newacct` — not `oldacct`):

```powershell
aws sts get-caller-identity
aws resourcegroupstaggingapi get-resources --region us-east-1 --tag-filters Key=Project,Values=FinancePackBench --query "ResourceTagMappingList[].ResourceARN"
```

Expect **empty**. Do **not** create resources “to test.”

## Context

FinancePackBench mid: P PI **15%** (`web_chat`) → **75%** (`light` + `prism-pi-finance-v1`). Remaining gap was **PrismGuard library** (structural false-allow + weak finance patterns), not harness wiring.

QA proved a deterministic structural approach can hit **20/20** mid attack / **10/10** benign on `web_chat` **without Judge** (local rescore). That proof may exist in tree as a **candidate**; your job is a **clean next-version implementation**.

## Objective

Publish a **new PrismGuard version** with a fresh, maintainable finance PI structural fix such that:

- Mid holdout `pi_finance_mid.json` → **20/20** block on `web_chat` (ONNX off), benign **≥10/10**
- FX/FAQ/`Hi` still **allow**
- **No** LLM Judge dependency for this claim
- Changelog + tests ship with the version bump
- **Zero** new AWS cost from this workstream

## Background — numbers

| Config | PI attack | Benign | Notes |
|--------|-----------|--------|-------|
| Mid `web_chat` (pre-fix) | 15% | 100% | Hub path |
| Mid `light` + finance ONNX | **75%** | 90% | Best before structural |
| QA proof (structural, local) | **100% (20/20)** | **100% (10/10)** | Reference only |

Fixture: `C:\code\FinancePackBench\fixtures\pi_finance_mid.json`.

## QA candidate (reference — re-implement cleanly)

| Path | Role |
|------|------|
| `prismguard/runtime/structural.py` | QA draft — **rewrite/harden for release quality** |
| `tests/test_structural_session.py` | Keep intent; clean up |
| QA note | `FinancePackBench/reviews/2026-07-23-structural-no-judge-100.md` |

## Tasks

- [ ] **T0:** Ack: fresh next-version impl · **no AWS** · **no Judge**.  
- [ ] **T1:** Design + implement structural/Tier-1 finance PI fix (may replace QA draft).  
- [ ] **T2:** Unit tests green.  
- [ ] **T3:** Local fixture rescore only (no AWS): `web_chat` 20/20 attacks, ≥10/10 benign, FX allow.  
- [ ] **T4:** Version bump + CHANGELOG.  
- [ ] **T5:** Short README / best-practices note.  
- [ ] **T6:** Handback with version id, pytest, rescore table, **AWS: no resources created / $0**.  
- [ ] **T7 (later, separate HO):** Full mid/AWS re-bench — **not** this HO.

## Constraints

- **No AWS** for this HO  
- **No LLM Judge** for the 20/20 claim  
- **No** law ONNX on FX to inflate PI  
- **No** `finance_pilot` (see HO-018)  
- Do not edit `C:\code\QA\` except `handoffs-back/`  
- Commit / publish only if user asks  

## Acceptance Criteria

- [ ] New version ready with changelog  
- [ ] Local 20/20 + benign/FX gates  
- [ ] Tests green  
- [ ] Handback confirms **no AWS resources created**  
- [ ] Release-quality impl (not unchecked QA dump)  

## How to hand back

1. Status → `Ready for QA` or `Blocked`  
2. `projects/PrismGaurd/handoffs-back/HB-PrismGuard-019-next-version-finance-pi.md`  
3. Only QA sets **Closed**

## Product path for Dev window

`C:\code\PrismGaurd\handoffs\handoffQa019-next-version-finance-pi.md`
