# How PrismGuard updates reach your install

PrismGuard improves through **packaged releases**, not by importing internal evaluation data into your runtime.

## What you get from `pip install prismguard`

| Artifact | Updates via | Your action |
|----------|-------------|-------------|
| Python library (`check`, structural rules, HTTP serve) | `pip install -U prismguard` | Upgrade package |
| Bundled seed corpus | `prismguard init` or `prismguard-seed import --bundled --mode update` | Re-run init/update after upgrade |
| Domain overlay (law) | Same as seed + `PRISMGUARD_DOMAIN=law` | `prismguard init --domain law` |
| ONNX classifier (`prism-pi-v1`) | Metadata in wheel; weights via `prismguard-model download` | Re-run download when model version bumps |
| Team/Business features | Signed license file | Renew license; set `PRISMGUARD_LICENSE_FILE` |

## What is **not** shipped into your runtime

Internal **holdout** sets (`normal_scenarios_holdout.yaml`, `legal_attacks_holdout.yaml`) and adversarial eval probes exist only for Insight IT benchmark discipline. They are **never** merged into bundled seed or customer imports.

If you previously thought holdout YAML was a runtime patch — it is not. Users get quality improvements through the rows above.

## Verify after upgrade

```bash
pip install -U "prismguard[guard-model]"
prismguard doctor
prismguard eval self-check
```

`eval self-check` runs fresh probes only — it does not print holdout scenario text. For full internal gates, maintainers run `python scripts/adversarial_self_check.py`.

## Enterprise: optional eval pack (future)

Team+ customers may receive a separate **signed eval pack** to self-verify allow/block rates on their infra. That pack remains eval-only and is never imported into production seed.

## License tiers (reminder)

| Feature | Env / command | Tier |
|---------|---------------|------|
| Library + memory storage | default | OSS |
| pgvector / vector backends | `PRISMGUARD_STORAGE_BACKEND=pgvector` + license | Team |
| `prismguard serve` | `PRISMGUARD_LICENSE_FILE` with `enterprise_http` | Business |
| Tenant lexicon import | `prismguard init --context-file` + `enterprise_tenant` | Business |

See [`enterprise-product-model.md`](enterprise-product-model.md) and [`integration-guide.md`](integration-guide.md).
