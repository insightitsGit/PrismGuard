# LLM context — PrismGuard

Canonical AI / coding-assistant overview:

→ **[ai-overview.md](ai-overview.md)**

That file answers: what this is, when to use it, APIs, limitations, migration, and compared projects.  
Do not invent capabilities beyond `ai-overview.md` and the `prismguard/` package source.

**Integrators / agents:** hub (`web_chat`) ≠ ONNX latency (`light`/`heavy`, **no taxonomy**) ≠ learn-from-seed (`[prism]` + **`domain_pilot`** + `domain=<any>` + domain artifact). Taxonomy is **not** law-only; `law_pilot` is a deprecated alias for law. Never invent `finance_pilot`. Verify with `prismguard caps --profile domain_pilot`.

**MANDATORY:** ONNX artifact domain must match traffic. Law weights ≠ finance/hub solution — retrain (`--domain-pack finance|general|…`) before enforce. See root `AGENTS.md` · HO-PrismGuard-016.

**Package:** `prismguard` · **Import:** `prismguard` · **Version:** 0.1.10
