# PrismGuard — integration tutorial briefs

**Source:** Google research + `kb/PRISMGUARD_GTM_STRATEGY.md`  
**Status:** Ready to build — **PrismGuard distribution path** (not ChorusGraph angel path)

---

## Tutorial 1 — LangGraph entry node (priority 1)

**Title:** How to Secure Your LangGraph Agent from Indirect Prompt Injection in 5 Minutes Using PrismGuard

**Hook:**
```python
from prismguard.runtime.factory import create_checker_for_app
checker = create_checker_for_app("web_chat")
```

**Story:** Entry-node guard before tool execution; indirect injection via user input.

**Distribute:** LangChain/LangGraph Discord, r/LangChain, dev.to

**CTA:** PyPI install · GitHub · Guardrail Autopsy

---

## Tutorial 2 — LlamaIndex legal RAG (priority 3 — vertical premium)

**Title:** Jailbreak Defense for Legal AI: Securing LlamaIndex RAG Pipelines Against Context-Stuffed Injections

**Hook:** Intercept retrieved chunks (MSA/NDA/adversarial embedded text) before synthesis.

**ONNX:** `prism-pi-v1` + `PRISMGUARD_USE_ONNX=1` + law domain — **disclose law-calibrated**.

**Distribute:** Legal AI communities, LlamaIndex Discord

**CTA:** Law domain pilot ($25k) · domain packs

---

## Tutorial 3 — Docker sidecar (priority 2 — AppSec)

**Title:** Deploying a Self-Hosted, Air-Gapped AI Firewall in 60 Seconds with Docker and `prismguard serve`

**Hook:** `prismguard serve` + cached ONNX + no outbound prompt scan

**Buyer:** AppSec — enforce across chatbot fleet

**Distribute:** security blogs, platform eng, Business SKU page

**CTA:** Business tier ~$699/mo · pilot

---

## Build order

1. LangGraph (widest reach)  
2. Sidecar (AppSec / revenue SKU)  
3. LlamaIndex legal (vertical monetization)
