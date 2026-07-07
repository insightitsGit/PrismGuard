# Law benchmark — Azure deployment (isolated resources)

**Do not provision without Director confirmation.** This mirrors ChorusGraph's
`benchmark/azure/` pattern but targets a dedicated resource group for the five
law-benchmark containers (CPL, CRL, LNL, LPL, ATK).

## Planned resources

| Resource | Purpose |
|----------|---------|
| `rg-prismguard-benchmark-law` | Isolated resource group |
| Azure Container Registry | Build/push 5 images |
| 4× Azure Container Instances | CPL, CRL, LNL, LPL |
| 1× Azure Container Instance | ATK (attacks the four endpoints) |
| Storage account (optional) | Fetch `comparison.json` + jsonl artifacts |

## Local validation first

```bash
cd benchmark/law
docker compose up --build
# In another shell after services are healthy:
python -m benchmark.law.run_law_benchmark --output-dir benchmark/law/results/latest
```

## Deploy (after Director approval)

```powershell
./benchmark/law/azure/deploy_and_run.ps1 -ResourceGroup rg-prismguard-benchmark-law -Location eastus
./benchmark/law/azure/fetch_results.ps1 -ResourceGroup rg-prismguard-benchmark-law
./benchmark/law/azure/teardown.ps1 -ResourceGroup rg-prismguard-benchmark-law
```

## Environment secrets

| Variable | Used by |
|----------|---------|
| `REBUFF_API_TOKEN` | CRL (real Rebuff cloud API) |
| `OPENAI_API_KEY` + `PINECONE_*` | CRL self-hosted RebuffSdk alternative |
| NeMo may require additional LLM keys per `nemoguardrails` config |

## Teardown policy

Always run `teardown.ps1` after fetching results. Do not leave ACI groups running
between sessions.
