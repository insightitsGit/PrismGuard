# Architecture — PrismGuard

PrismGuard sits **in front of your LLM** as an input firewall. Full design: [prismguard-design.md](prismguard-design.md).

## Stack placement

```
Application / agents (ChorusGraph, custom API, …)
        │
        ▼
┌───────────────────┐
│ PrismGuard        │  ← normalize · rules · optional ONNX · optional Judge
│ (this library)    │
└─────────┬─────────┘
          │
     ALLOW│ BLOCK (+ resolution_gate)
          ▼
        LLM / tools
```

## Request-time flow (simplified)

```
Incoming prompt
  → Normalize
  → Rules / structural (Tier-1)
  → Optional ONNX guard model (opt-in)
  → Optional fusion / taxonomy path
  → Optional LLM Judge (gray only)
  → CheckResult(decision, resolution_gate, …)
```

Default app factory `create_checker_for_app("web_chat")` is **rules-first** (no surprise ONNX). Set `PRISMGUARD_USE_ONNX=1` only when the artifact matches your traffic domain.

## Related

- [ai-overview.md](ai-overview.md) · [llm-context.md](llm-context.md)  
- [integration-guide.md](integration-guide.md) · [scorecard.md](scorecard.md)  
- SVG: [assets/architecture.svg](assets/architecture.svg)
