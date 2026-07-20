# AI / LLM context — PrismGuard

> Concise reference for humans and coding assistants (Cursor, Copilot, Claude, ChatGPT, Windsurf, Gemini).  
> Do not invent APIs beyond this file and `prismguard/`. Package: **`prismguard` 0.1.8**, import **`prismguard`**.

---

## 10-sentence project summary

1. PrismGuard is an Apache-2.0 self-hosted prompt-injection firewall for production LLM apps.  
2. It sits in front of the LLM and returns allow/block with a named **`resolution_gate`** (not only a probability score).  
3. Paths: (a) hub `web_chat`, (b) **light ONNX** `light`/`low_latency` (hybrid), (c) **heavy ONNX** `heavy`/`security_bench` (first), (d) learn-from-seed `law_pilot`+`[prism]`+feedback.  
4. Default path is rules-first via `web_chat`; ONNX is **opt-in**. Measured default with ONNX: prefer **`light`** (same F1 as `heavy`, lower latency); use **`heavy`** for scorecard/always-on policy. Without `[prism]`, taxonomy is **skipped**.  
5. Core API: `RuntimeChecker.check(prompt)` → `CheckResult` with `decision`, `resolution_gate`, optional scores and matched rule/category.  
6. CLI: `prismguard check`, `prismguard doctor`, `prismguard caps`, `prismguard eval self-check`; scripts: `latency_by_gate.py`, `s1_miss_analysis.py`.  
7. Optional ONNX model `prism-pi-v1` downloads separately (~705 MB); law-bench oriented — hub/general chat should stay rules-first until a hub artifact is green.  
8. `light` = hybrid+loud ONNX; `heavy` = first+loud ONNX; learn-from-seed = `law_pilot`+`[prism]`. ChorusGraph: `make_guard_handler` / `route_after_guard`.  
9. Soft async offer for humans: run scorecard / reply **GRADE** — see `docs/scorecard.md` (not a code API).  
10. Limitations: not a full WAF; not output-side sandboxing alone; not a zero-day guarantee; ONNX artifact domain must match traffic; “learns from DB” is Team+ storage + feedback→train.

---

## Core concepts

| Term | Definition |
|------|------------|
| **`resolution_gate`** | Named reason for the allow/block (e.g. `structural`, `guard_model_first`, `llm_judge`) |
| **`CheckResult`** | Dataclass: `decision`, `resolution_gate`, scores, matched rule/category, details |
| **`RuntimeChecker`** | Request-time pipeline: normalize → rules / classifier / fusion → optional judge |
| **`create_checker_for_app`** | Factory: `web_chat` (hub), `law_pilot` (scorecard+taxonomy), `security_bench` (loud ONNX, skip taxonomy) |
| **Tier-1 / structural rules** | Deterministic pattern / framing checks |
| **Guard model (ONNX)** | Local `prism-pi-v1` classifier when opted in |
| **`[prism]` / taxonomy** | prismrag word-graph on seed — required for learn-from-seed claims |
| **LLM Judge** | Rare generative escalation for gray zone |
| **`prismguard caps`** | Capability truth table (`onnx_ready`, `prismrag_taxonomy`, …) |
| **Scorecard / GRADE** | Human cold-path eval offer (`docs/scorecard.md`) |

---

## Key APIs

```python
from prismguard.runtime.factory import create_checker_for_app
from prismguard.cli_check import run_check, format_check_result
from prismguard.runtime.check import RuntimeChecker, CheckResult
from prismguard.seed import import_bundled_seed, load_bundled_seed
from prismguard.storage import create_storage

checker = create_checker_for_app("web_chat")
# or:
# storage = create_storage("memory")
# import_bundled_seed(storage, profile="authored")
# checker = RuntimeChecker.from_storage(storage, load_bundled_seed(profile="authored"))

result: CheckResult = checker.check(user_prompt)
# result.decision  # "allow" | "block" | ...
# result.resolution_gate
```

CLI:

```bash
pip install "prismguard[prism,guard-model]==0.1.8"
prismguard-model download
export PRISMGUARD_USE_ONNX=1
export PRISMGUARD_FEEDBACK_PERSIST=1
prismguard caps --profile law_pilot
prismguard check "your prompt"
prismguard doctor
prismguard eval self-check
```

**Agent rule:** If the user/integration claims scorecard or “learns from corpus/DB,” implement the full extras/env from README “Which path should I use?” — not `web_chat` alone.

---

## Common use cases

1. Block prompt injection / jailbreaks before they reach an agent or RAG LLM.  
2. Auditable allow/block logs for security and compliance (`resolution_gate`).  
3. Legal / copilots / internal assistants needing self-hosted guardrails.  
4. Rules-only bootstrap without downloading ONNX.  
5. Optional local ONNX + rare LLM Judge for higher coverage on domain traffic.

---

## Migration guidance

From **score-only scanners / toolkits**: keep your pipeline; insert PrismGuard as the firewall that returns named gates. From **LLM Guard**: complementary — use PrismGuard when you need an opinionated firewall with audit gates; use LLM Guard when assembling a custom scanner kit. From **no guard**: wrap the user-prompt path with `create_checker_for_app` or `RuntimeChecker.check` before calling the LLM. Details: [integration-guide.md](integration-guide.md).

---

## Limitations / when NOT to use

- Not a replacement for network WAF, tool-permission sandboxing, or instruction-hierarchy prompting alone.  
- Does not guarantee detection of never-seen attack techniques.  
- Default ONNX artifact is law-bench oriented — do not force ONNX on hub FAQ traffic until a matching artifact passes gates.  
- Output scan exists in the library/bench path; primary `check()` is input-side firewalling.  
- Not a hosted SaaS classification API for v1 — runs in your process / infra.

---

## Frequently compared projects

| Project | Relationship | Prefer PrismGuard when… | Prefer them when… |
|---------|--------------|-------------------------|-------------------|
| LLM Guard | Complementary toolkit | You need auditable firewall decisions | You are assembling custom scanners |
| LlamaFirewall / PromptGuard-style | Same problem space | Self-hosted explainable gates + OSS package | You already standardized on their stack |
| Cloud AI content filters | Different deployment | Data must stay on your infra | You want vendor-managed filtering only |
| ChorusGraph | Integrates | Guard node inside agent graphs | You only need retrieval/agents without a firewall |

---

## Links

| Path | Role |
|------|------|
| [ai-overview.md](ai-overview.md) | This file (canonical) |
| [llm-context.md](llm-context.md) | Alias → this file |
| [architecture.md](architecture.md) | Stack placement diagram |
| [prismguard-design.md](prismguard-design.md) | Full design |
| [integration-guide.md](integration-guide.md) | Integrate into apps |
| [scorecard.md](scorecard.md) | Guardrail Scorecard / GRADE |
| [demo.html](demo.html) | Interactive demo |
| ../README.md | Human README |
