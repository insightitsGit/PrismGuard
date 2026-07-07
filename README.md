# PrismGuard

Self-hosted, audit-traceable prompt-injection firewall. Composes **prismRAG** (taxonomy-aware graph retrieval), **prismCortex** (vector seed store — pgvector default, swappable), and **prismLib** (in-process runtime cache) into a three-tier request pipeline: deterministic rules and taxonomy-grounded similarity/graph matching resolve most traffic; a **Prism-owned ONNX Guard Model** handles fusion gray-zone cases; a rare, isolated **LLM Judge** handles guard-uncertain prompts.

Status: **runtime + owned classifier + feedback loop implemented** — see [`docs/prismguard-design.md`](docs/prismguard-design.md) and [`docs/guard-model-training.md`](docs/guard-model-training.md).

See [docs/prismguard-design.md](docs/prismguard-design.md) for the full architecture, data model, attack taxonomy/seed corpus, cost-control design, feedback loop, and open risks.

## At a glance

- **Goal**: catch prompt injection / jailbreak attempts before they reach an LLM, while keeping LLM Judge calls to well under 1% of traffic.
- **Depends on**: `prismrag`, `prismcortex`, `prismlib` (existing Prism family packages).
- **Storage**: pgvector/Postgres by default; Chroma, Pinecone, Weaviate via `prismguard[pgvector|chroma|pinecone|weaviate]` — see `prismguard/storage/`.
- **Seed import**: multi-source (`prismguard-seed import file1.yaml dir/ @manifest.txt`), `update` or `replace` mode — see `prismguard/seed/`.
- **Bundled seed**: ships in `prismguard/seed/corpus/` (authored + neuralchemy + S-Labs + yanismiraoui). Quick start: `pip install prismguard[seed]` then `prismguard-seed import --bundled` (authored) or `--bundled --profile full` (~30k+ rows). See [`seed/README.md`](seed/README.md).
- **Guard Model**: owned ONNX classifier (`prismguard[guard-model]`); train from seed DB with `prismguard-model train --profile full`.
