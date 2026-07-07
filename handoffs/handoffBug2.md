# Handoff Bug2 — make the law benchmark's numbers real

**Director:** Amin · **Architect:** Claude · **Engineer:** (receiving agent)
**Refs:** [`handoffs/testhandoff1.md`](testhandoff1.md) · [`handoffs/handoffbackTestHandoff1.md`](handoffbackTestHandoff1.md) (what was built) · this handoff's findings came from independently re-running the tests, checking `az group list` for real (nothing provisioned), and reading `benchmark/law/shared/guards.py` and `benchmark/law/atk/attack_runner.py` directly
**Date issued:** 2026-07-07 · **Revision:** 2026-07-07 — Rebuff/NeMo Guardrails replaced (see below)

---

## 0. Why

TestHandoff1's scaffold is real and honestly built — 56 tests pass, no Azure resources were created without asking, and the guardrail gates genuinely check for credentials rather than faking a result. But the headline comparison numbers (CPL/LPL: 100% block, CRL/LNL: 0% block) are not yet a real result, for two independent reasons, plus one gap the Director flagged directly:

1. **The two comparison guardrails never actually ran** (Rebuff needed a paid API token or a self-hosted OpenAI+Pinecone stack; NeMo Guardrails needed a working Colang rails config + LLM backend neither was wired). Both returned `gray`/`*_unconfigured` for every input. A 0% block rate from a system that was never given a real try is not a competitive result.

2. **PrismGuard's 100% block rate on the legal overlay is close to tautological.** `PrismGuardGate.__init__` (guards.py:31) imports `benchmark/law/data/legal_attacks.yaml` directly into PrismGuard's own seed corpus. `attack_runner.py`'s `_load_attack_overlay` (line 63) then replays that *exact same file, verbatim* as the attack traffic. The bundled-attack portion has the same problem: `PrismGuardGate` loads the `"authored"` bundled profile as its seed corpus (guards.py:25), and `attack_runner.py`'s default `--bundled-profile` is also `"authored"` (line 27). The attacker is currently asking PrismGuard "do you recognize text that is byte-for-byte in your own seed store," not "can you catch a novel or paraphrased attack." This is exactly the "held-out eval set, never used for tuning" requirement from `docs/prismguard-design.md` Part 10 (T10), which this run skipped.

3. **Director's addition:** the benign side needs the same rigor as the attack side. Right now "does this break normal usage" is measured only by 6 task-success queries folded into one aggregate number — not enough volume or diversity to trust a false-positive claim.

**This revision replaces the comparison guardrails** — Rebuff and NeMo Guardrails are dropped in favor of two options with no external-credential blocker:

| Was | Now | Why |
|---|---|---|
| Rebuff (ChorusGraph pairing) | **LLM Guard** (Protect AI) | MIT licensed, ~3.1k stars, dedicated `PromptInjection` scanner, runs fully local via its own HuggingFace classifier — no API token, no Pinecone/vector-DB dependency. Directly removes the credential blocker. |
| NeMo Guardrails (LangGraph pairing) | **LlamaFirewall** (Meta) | Open source, Meta-backed (comparable credibility to NVIDIA's NeMo), `PromptGuard 2` is a purpose-built jailbreak/prompt-injection classifier — no Colang rails authoring or LLM-backend wiring required to get a real result. |

**Naming updated accordingly** (framework letter unchanged, guardrail letter changed, domain letter unchanged):

| ID (was) | ID (now) | Framework | Guardrail | Domain | Path |
|---|---|---|---|---|---|
| CPL | **CPL** (unchanged) | ChorusGraph | PrismGuard | Law | `benchmark/law/cpl/` |
| CRL | **CGL** | ChorusGraph | LLM Guard | Law | `benchmark/law/cgl/` (renamed from `crl/`) |
| LNL | **LFL** | LangGraph | LlamaFirewall | Law | `benchmark/law/lfl/` (renamed from `lnl/`) |
| LPL | **LPL** (unchanged) | LangGraph | PrismGuard | Law | `benchmark/law/lpl/` |

**Second-order finding from this swap, worth naming explicitly:** neither LLM Guard's `PromptInjection` scanner nor LlamaFirewall's `PromptGuard 2` makes a real generative-LLM API call — both are local classifier models (small fine-tuned transformers), the same shape as PrismGuard's own not-yet-built "Guard Model" tier. That means **none of the four stacks will make a real paid LLM call in the guard step** once this lands. That's actually a fairer comparison than the original plan (Rebuff's self-hosted path would have made real OpenAI calls, PrismGuard makes none — an apples-to-oranges cost comparison) — but it also means this specific benchmark run no longer tests PrismGuard's original "minimize LLM calls vs. approaches that use them" claim. Track this as `guard_classifier_calls` (local model inference count, all four stacks) separately from `guard_generative_llm_calls` (expected to be 0 for all four right now) — see T5.

**Domain note (Director asked, no code change):** keeping the Law domain — third regulated vertical after ChorusGraph's existing Finance/Healthcare benchmarks, matches PrismRAG's own documented fit, and none of the fixes in this handoff are domain problems.

**Standing rules:**
- **No metric gets reported as a number if the system that produced it wasn't actually exercised.** If LLM Guard/LlamaFirewall still can't run for some reason, report block rate as `null`/`"unconfigured"` explicitly, not `0.0`.
- **Attack traffic used to measure detection must not appear in any container's own seed/config at import time.** Verify this by diffing the attacker's attack text against each stack's seed/scanner config before trusting a block-rate number.
- **Every new test data file needs a one-line comment stating whether it's held-out or seeded.**
- Full `pytest -q` green after every task. Commit/push only when the Director asks.

---

## T1 — Wire LLM Guard for the ChorusGraph pairing (replaces old T1/Rebuff)

**Files:** `benchmark/law/shared/guards.py` (replace `RebuffGate` with `LLMGuardGate`), `benchmark/law/cgl/` (renamed from `crl/`), `pyproject.toml` (swap `rebuff` extra for `llm-guard`)

```python
from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType
```

`LLMGuardGate.check(text)` runs the `PromptInjection` scanner (local model, first call downloads/caches the classifier — note the one-time download cost in the handoff-back, don't let it look like per-request latency) and maps its `is_valid`/risk score to `block`/`allow`. No API token, no environment-variable gate needed — if it's installed, it runs. If install friction shows up (model download size, torch dependency conflicts), report it plainly rather than silently falling back to unconfigured.

**Exit:** `LLMGuardGate.check()` returns a real scanner verdict (not a stub) for at least one test call, with `guard_classifier_calls: 1` and a real (non-trivial) latency reflecting actual model inference.

## T2 — Wire LlamaFirewall for the LangGraph pairing (replaces old T2/NeMo)

**Files:** `benchmark/law/shared/guards.py` (replace `NemoGuardrailsGate` with `LlamaFirewallGate`), `benchmark/law/lfl/` (renamed from `lnl/`), `pyproject.toml` (swap `nemo` extra for `llamafirewall`), delete `benchmark/law/lnl/config/` (no rails config needed)

Wire `PromptGuard 2` specifically (not the full LlamaFirewall agent-alignment/CodeShield surface — out of scope for this benchmark, which is about prompt injection/jailbreak detection only). Confirm the actual package/import path against what's currently published (verify, don't assume from this handoff's description) before writing the integration.

**Exit:** `LlamaFirewallGate.check()` returns a real `PromptGuard 2` classification (not a stub) for at least one test call, with `guard_classifier_calls: 1` and real inference latency.

## T3 — Build a genuine held-out attack set

**Files:** `benchmark/law/data/legal_attacks_holdout.yaml` (new), `benchmark/law/atk/attack_runner.py`

Unchanged from the prior revision of this handoff:

- **Quick win:** change `attack_runner.py`'s default `--bundled-profile` from `"authored"` to `"full"` (the ~22k-row corpus). `PrismGuardGate` only ever seeds itself with `"authored"` (~40 rows), so almost all of `"full"` is already genuinely held-out relative to PrismGuard's own corpus at zero new-content cost. Verify this overlap assumption explicitly (diff the two sets).
- **Real fix:** write `legal_attacks_holdout.yaml` — 15-20 *new* paraphrases/variants of `legal_attacks.yaml`'s scenarios, same intent, different phrasing. **Must never be imported into any container's seed store or scanner config** — exists only in `atk/`'s attack traffic path, with the required "held-out, do not import" comment.

Update `attack_runner.py` to report attack results **split by source** (`legal_overlay_seeded` vs `legal_overlay_holdout` vs `bundled_full`), not one merged number.

**Exit:** `comparison.json` reports attack_block_rate separately for the seeded-overlap set and the held-out set; the held-out number is the one that answers "does this generalize."

## T4 — Explicit normal-scenario / false-positive suite (Director's addition)

**Files:** `benchmark/law/data/normal_scenarios.yaml` (new), `benchmark/law/run_law_benchmark.py`, `benchmark/law/compare_law.py`

Unchanged from the prior revision: 30-40 normal, legitimate legal-assistant scenarios distinct from the KB task-success queries, including some that are *superficially* attack-adjacent in phrasing but genuinely benign (e.g. "can you summarize what confidentiality means in this contract," "pretend you're explaining this contract to a first-year associate") — specifically stress-testing the `benign_adjacent` category boundary.

Report as its own first-class section in `COMPARISON_REPORT.md` — normal-scenario pass rate per stack, with specific wrongly-blocked prompts called out by name.

**Exit:** `comparison.json` has a `normal_scenarios` block per stack; `COMPARISON_REPORT.md` leads with this section alongside the held-out attack numbers.

## T5 — Fix the guard-call metric so it reflects reality post-swap

**Files:** `benchmark/law/shared/guards.py`, `benchmark/law/compare_law.py`

Per the "second-order finding" above: with LLM Guard and LlamaFirewall replacing Rebuff/NeMo, **all four stacks now use local classifier inference, not generative LLM API calls, in the guard step.** Replace the old `guard_llm_calls` field with two explicit fields:
- `guard_classifier_calls` — local model inference count (expected non-zero for CGL/LFL once T1/T2 land; still 0 for CPL/LPL since PrismGuard has no classifier-based Guard Model tier yet either — annotate that as `guard_model_tier: "not_implemented"`, same spirit as the original T5).
- `guard_generative_llm_calls` — real paid-API LLM calls. Expected `0` for all four stacks in this run. If this benchmark is later extended to include a real LLM Judge tier (PrismGuard's own, or a generative check inside another tool), this is the field that would move.

**Exit:** `comparison.json`/`COMPARISON_REPORT.md` clearly distinguish local-classifier inference from generative LLM calls, for every stack, with the "not implemented" vs "implemented and zero" distinction preserved from the original T5 intent.

## T6 — Re-run and re-report

**Files:** `benchmark/law/results/latest/*`

Re-run the full local comparison with T1-T5 in place. Report the same three paired comparisons (CPL vs CGL, LPL vs LFL, CPL vs LPL) — now on real LLM Guard/LlamaFirewall behavior, held-out attack data, and an explicit normal-scenario section — plus state plainly whether the held-out numbers still favor PrismGuard, and by how much, now that the test is fair in both directions.

**Exit:** an updated `COMPARISON_REPORT.md` where every number was produced by a system that was actually exercised, on data it hadn't already seen.

---

## Order & effort

T1 and T2 are no longer blocked on external credentials — both should be unblockable within this handoff (install friction is possible, e.g. model downloads or dependency conflicts, but not a hard stop requiring the Director). T3 and T4 don't depend on T1/T2 and can proceed in parallel. T5 is small, do it alongside T3/T4. T6 last.

Rough estimate: T1: 2-3h · T2: 3-5h (verifying the real package/import path first) · T3: 3-4h · T4: 3-4h · T5: 1h · T6: 1-2h.

## Return format (`handoffbackBug2.md`)

Per task: files · exit criteria pass/fail with real output · **for T1/T2, paste an actual LLM Guard/LlamaFirewall scanner response showing it genuinely ran** (verdict + latency), not just "resolution_gate changed" · for T3, the explicit overlap-check result · for T4, the full list of any normal-scenario prompts wrongly blocked, per stack · the re-run comparison numbers from T6, with a plain statement of whether PrismGuard still wins on the honest, held-out version of this test, and a note that this run no longer measures generative-LLM-call reduction (per T5) since none of the four stacks make one. No commits unless the Director asks.

---
*Bug2 (rev. 2) · Rebuff/NeMo replaced with LLM Guard/LlamaFirewall to remove the credential blocker · fixes the seed-overlap attack test and adds the Director's normal-scenario suite · domain stays Law · this run compares local-classifier-based detection across all four stacks, not generative-LLM-call reduction — that claim needs a future run once PrismGuard's own Guard Model/LLM Judge tiers exist.*
