# Law pilot readiness — priorities before any new domain or feature work

**Gate:** Do not call law "solid" or ship externally until `scripts/adversarial_self_check.py` exits 0.

## Operating principles (non-negotiable)

1. **Fix FP root cause first** — veto/escalation architecture + classifier training for `structural=continue` paths.
2. **Phrasing-diverse holdouts by rule** — every holdout must cover short/long × formal/casual (`benchmark/shared/holdout_quality.py`); CI enforces this.
3. **Adversarial self-check before any win** — run `scripts/adversarial_self_check.py`; fresh probes + holdout + overlap must pass.
4. **Law first — feature freeze** — no healthcare, finance, tenant context, or general-domain expansion until law passes self-check.
5. **Positioning: cheaper + audited** — not "beats LLM Guard on raw detection." Lead with `resolution_gate` audit trail and ONNX latency.
6. **Customer discovery** — after self-check passes, talk to one real prospective buyer before building more.

## What we are building (honest claim)

**Cheaper + audited prompt-injection guard for compliance-focused legal AI workflows.**

Not: "beats LLM Guard on raw detection across every domain."

Yes:

- ONNX classifier + structural rules + optional LLM Judge escalation
- Every decision has a **`resolution_gate`** audit trail (`structural`, `guard_model_first`, `llm_judge`, …)
- Typical path latency ~200ms ONNX-only vs multi-second generative scanners
- Cold holdout metrics only for external claims — seeded sets are dev/tuning only

## Blockers (in order)

### 1. False-positive root cause — DONE (architecture); training ongoing

| Mechanism | Fix | Status |
|-----------|-----|--------|
| structural=allow + classifier block → veto | `disagreement_escalation` → Judge or structural wins | **Shipped** |
| structural=continue + classifier block on benign | Structural benign framing + hard negatives + retrain | **Partial** (holdout 43/43) |

Run: `python scripts/diagnose_fp_path.py`

### 2. Phrasing-diverse holdouts — ENFORCED

Every holdout YAML must cover **four quadrants**:

- short_fragment / formal
- short_fragment / casual
- full_question / formal
- full_question / casual

Enforced in CI via `benchmark/shared/holdout_quality.py` (min 4 per quadrant for normal holdout ≥20 rows).

### 3. Adversarial self-check — REQUIRED BEFORE ANY "WIN"

Before internal or external success claims, run:

```powershell
python scripts/adversarial_self_check.py
```

This runs overlap checks, phrasing diversity, fresh adversarial probes, and holdout pass rates. **No green check = no win.**

### 4. Law first — FEATURE FREEZE

**Frozen until law pilot passes adversarial self-check:**

- healthcare / finance domain packs
- tenant context production path
- general-domain product expansion
- new advertisement suites

### 5. Customer discovery — STILL OPEN

After blockers 1–3 are green, talk to **one real prospective customer** (compliance/legal AI buyer) before building anything else. That was the original open question and remains unanswered.

## External messaging template

> PrismGuard is a **low-latency, auditable** guardrail for legal AI assistants. Each request returns a decision gate suitable for compliance logs. We optimize for **predictable cost and explainability**, not beating every generic scanner on every paraphrase.

## Commands

```powershell
python scripts/adversarial_self_check.py
python scripts/diagnose_fp_path.py
python -m benchmark.law.run_local_benchmark --output-dir benchmark/law/results/latest --bundled-limit 50 --warmup-requests 3
python -m pytest tests/test_law_benchmark.py tests/test_disagreement_escalation.py -q
```
