# Law-domain benchmark sample data

Synthetic legal corpus for the CPL/CRL/LNL/LPL guardrail matrix. Same KB and query
set for all four stacks — only framework and guardrail differ.

## Knowledge base (`data/kb_documents.yaml`)

| Category | Documents | Topics |
|----------|-----------|--------|
| `contracts` | 6 | NDA termination, limitation of liability, indemnity, assignment |
| `case_law` | 6 | Synthetic holdings on privilege, standing, summary judgment |
| `compliance` | 5 | GDPR lawful basis, SEC disclosure, privilege log requirements |

**Total:** 17 KB chunks with `category_slug` for PrismRAG taxonomy routing.

## Legitimate queries (`data/queries.yaml`)

| Count | Purpose |
|-------|---------|
| 18 | Task-success measurement with rubric keywords per query |

Variants mirror ChorusGraph healthcare bands: `exact_repeat`, `paraphrase`, `novel`.

## Attack overlay (`data/legal_attacks.yaml`)

| Count | Purpose |
|-------|---------|
| 18 | Domain-flavored attacks mapped to PrismGuard taxonomy slugs |

General corpus (~22k rows) is replayed by ATK from the bundled `full` profile;
this overlay adds legal-context phrasing only.

## Taxonomy categories (PrismRAG routing)

- `contracts`
- `case_law`
- `compliance`

These are retrieval categories for the law KB, separate from PrismGuard attack
taxonomy slugs used in `legal_attacks.yaml`.
