# PrismGuard

Self-hosted, audit-traceable prompt-injection firewall. Composes **prismRAG** (taxonomy-aware graph retrieval), **prismCortex** (vector seed store — pgvector default, swappable), and **prismLib** (in-process runtime cache) into a two-tier request pipeline designed to minimize LLM calls: deterministic rules and taxonomy-grounded similarity/graph matching resolve the vast majority of traffic, with a fast local Guard Model and a rare, isolated LLM Judge handling only genuinely ambiguous gray-zone cases.

Status: **design draft + T1 scaffold** — see [`handoffs/handoffPrismGuardImplementation.md`](handoffs/handoffPrismGuardImplementation.md) for the full build plan (includes LLM-minimization enhancements in Part I).

See [docs/prismguard-design.md](docs/prismguard-design.md) for the full architecture, data model, attack taxonomy/seed corpus, cost-control design, feedback loop, and open risks.

## At a glance

- **Goal**: catch prompt injection / jailbreak attempts before they reach an LLM, while keeping LLM Judge calls to well under 1% of traffic.
- **Depends on**: `prismrag`, `prismcortex`, `prismlib` (existing Prism family packages).
- **Storage**: pgvector/Postgres by default; Chroma, Pinecone, Weaviate via `prismguard[pgvector|chroma|pinecone|weaviate]` — see `prismguard/storage/`.
- **Seed import**: multi-source (`prismguard-seed import file1.yaml dir/ @manifest.txt`), `update` or `replace` mode — see `prismguard/seed/`.
- **Bundled seed**: ships in `prismguard/seed/corpus/` (authored + neuralchemy + S-Labs + yanismiraoui). Quick start: `pip install prismguard[seed]` then `prismguard-seed import --bundled` (authored) or `--bundled --profile full` (~30k+ rows). See [`seed/README.md`](seed/README.md).
- **Not**: a replacement for output-side monitoring, tool sandboxing, or instruction-hierarchy prompting — one layer in a defense-in-depth stack.
