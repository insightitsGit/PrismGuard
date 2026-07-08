# Optional tenant context

PrismGuard supports an **optional** tenant vocabulary so guards can recognize client-specific entities (matter IDs, patient MRNs, account numbers) without scanning your whole database.

## Quick start (file-based — recommended)

Create `tenant_lexicon.yaml` in your project root (or any path):

```yaml
domain: law
entities:
  - term: Apex Holdings
    type: client_name
    sensitivity: restricted
  - term: matter-4471
    type: matter_id
    sensitivity: restricted
  - term: NDA termination notice
    type: legal_concept
    sensitivity: internal
override_tokens:
  - bypass privilege
```

Bootstrap with optional domain pack and tenant context:

```bash
prismguard init --domain law --context-file ./tenant_lexicon.yaml
prismguard doctor
```

Or import lexicon separately (dry-run first):

```bash
prismguard context import ./tenant_lexicon.yaml --dry-run
prismguard context import ./tenant_lexicon.yaml --apply
```

Enable in runtime config (`prismguard/config/triage.yaml`):

```yaml
tenant_context:
  enabled: true
  lexicon_path: ./tenant_lexicon.yaml
```

Or set `PRISMGUARD_TENANT_LEXICON_PATH`.

## Optional SQL table

Point at a **curated** table your team maintains (never auto-scan production):

```bash
prismguard init --domain law \
  --context-table guard_context_terms \
  --context-dsn "$DATABASE_URL"
```

Expected columns (case-insensitive): `term`, `type`, `sensitivity`, optional `aliases` (semicolon-separated).

## CSV format

```csv
term,type,sensitivity,aliases
Apex Holdings,client_name,restricted,
matter-4471,matter_id,restricted,4471
```

## Domain packs

| Domain | Command |
|--------|---------|
| Law | `prismguard-seed import --bundled --domain law` |
| Healthcare | `prismguard-seed import --bundled --domain healthcare` |
| Finance | `prismguard-seed import --bundled --domain finance` |

List packs: `prismguard domains`

## What tenant context does

1. **Tier-1 tenant rule** — blocks when override language co-occurs with a **restricted** entity
2. **Fusion severity boost** — raises fused score when internal/restricted terms appear
3. **Template seed entries** (optional `--apply`) — generates attack/benign examples using your terms, not raw DB rows
4. **Classifier veto** — parallel guard model can block even when fusion says allow (see `guard_model.veto_enabled`)

## Privacy notes

- Tenant context is **opt-in** (`tenant_context.enabled: false` by default)
- Import **curated** glossary tables, not full production dumps
- Holdout eval sets must never be copied into tenant lexicon or seed
