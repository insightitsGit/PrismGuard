# Hub / general training pack (opt-in)

Used only when you pass `--domain-pack general` (or run `scripts/train_prism_pi_hub.py`).

| File | Role |
|------|------|
| `hub_attacks.yaml` | Jailbreak seed for training (not holdout) |
| `hub_benign_hard_negatives.jsonl` | FAQ/product allows from `../benign_faq.txt` |

**Default train** (no `--domain-pack`) does **not** include these files.
