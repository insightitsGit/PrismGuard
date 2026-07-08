# PrismGuard

Self-hosted, audit-traceable prompt-injection firewall. Composes **prismRAG** (taxonomy-aware graph retrieval), **prismCortex** (vector seed store — pgvector default, swappable), and **prismLib** (in-process runtime cache) into a three-tier request pipeline: deterministic rules and taxonomy-grounded similarity/graph matching resolve most traffic; a **Prism-owned ONNX Guard Model** handles fusion gray-zone cases; a rare, isolated **LLM Judge** handles guard-uncertain prompts.

Status: **runtime + owned classifier + feedback + domain packs + tenant context + law benchmark implemented** — see [`docs/prismguard-design.md`](docs/prismguard-design.md) (v0.3), [`docs/guard-model-training.md`](docs/guard-model-training.md), and [`docs/tenant-context.md`](docs/tenant-context.md).

See [docs/prismguard-design.md](docs/prismguard-design.md) for the full architecture, data model, attack taxonomy/seed corpus, cost-control design, feedback loop, domain packs, benchmark harness, gap analysis (Part 14), and open risks.

## At a glance

- **Goal**: catch prompt injection / jailbreak attempts before they reach an LLM, while keeping LLM Judge calls to well under 1% of traffic.
- **Depends on**: `prismrag`, `prismcortex`, `prismlib` (existing Prism family packages).
- **Storage**: pgvector/Postgres by default (**backend stubs only today** — `memory` used in tests/benchmarks); Chroma, Pinecone, Weaviate via optional extras — see `prismguard/storage/`.
- **Domain packs**: law, healthcare, finance — `prismguard init --domain law` or `PRISMGUARD_DOMAIN=law`.
- **Tenant context**: optional lexicon — `prismguard context import` — see [`docs/tenant-context.md`](docs/tenant-context.md).
- **Calibration**: `prismguard-model calibrate --domain law` (holdout-safe threshold tuning).
- **Benchmark**: 4-stack law harness (CPL/CGL/LGL/LPL) — `benchmark/law/`.
- **Seed import**: multi-source (`prismguard-seed import file1.yaml dir/ @manifest.txt`), `update` or `replace` mode — see `prismguard/seed/`.
- **Bundled seed**: ships in `prismguard/seed/corpus/` (authored + neuralchemy + S-Labs + yanismiraoui). Quick start: `pip install prismguard[seed]` then `prismguard-seed import --bundled` (authored) or `--bundled --profile full` (~30k+ rows). See [`seed/README.md`](seed/README.md).
- **Guard Model**: owned ONNX classifier (`prismguard[guard-model]`); train from seed DB with `prismguard-model train --profile full`.
