# Seed corpus

The bundled seed corpus ships inside the installed package at:

**`prismguard/seed/corpus/`**

| Path | Contents |
|------|----------|
| `authored/seed.yaml` | Taxonomy, Tier-1 rules, hand-written examples (ours) |
| `external/s-labs/` | S-Labs prompt-injection dataset (MIT) — train/val/test CSV |
| `external/yanismiraoui/` | Multilingual injection prompts (Apache-2.0) |
| `external/neuralchemy/` | Placeholder README (parquet not bundled — fetch separately) |
| `manifest.authored.txt` | Fast import: authored only |
| `manifest.txt` | Full import: authored + all external CSVs |
| `MANIFEST.md` | Licenses, row counts, import notes |

## Quick start

```bash
pip install prismguard[seed]   # pyarrow for neuralchemy parquet

# Authored seed only (~40 examples, default)
prismguard-seed import --bundled

# Full corpus including external datasets (~30k+ rows, all taxonomy gaps filled)
prismguard-seed import --bundled --profile full
```

```python
from prismguard.seed import import_bundled_seed, load_bundled_seed
from prismguard.storage import create_storage

storage = create_storage("memory")
import_bundled_seed(storage, profile="authored")   # or profile="full"
```

When users `pip install prismguard`, all files under `prismguard/seed/corpus/` are included automatically.
