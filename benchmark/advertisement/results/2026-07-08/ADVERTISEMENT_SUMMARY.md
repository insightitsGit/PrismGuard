# PrismGuard Advertisement Benchmark Summary

_Generated: 2026-07-09T03:08:24.638463+00:00_

## How to cite these numbers

| Metric | Suite | Safe for external claims? |
|--------|-------|---------------------------|
| Attack holdout block rate | `attack-holdout` | Yes (cold attack eval) |
| Normal holdout pass rate | `normal-holdout` | Yes (cold benign eval) |
| Normal dev pass rate | `normal-dev` | No — used in tuning/training |
| Seeded overlay block rate | `attack-seeded` | No — in-corpus attacks |
| Full combined benchmark | `law-full` | Supporting context only |

## CPL headline metrics by suite

### `attack-holdout` (headline)
- traffic_count: 18
- request_latency_ms_mean: **179.71**
- attack_holdout_block_rate: **1.0**
- attack_block_rate (suite): **1.0**
- normal_dev_pass_rate: None
- normal_holdout_pass_rate: **None**
- kb_benign_fp_rate: 0.25

### `attack-seeded` (diagnostic)
- traffic_count: 18
- request_latency_ms_mean: **155.9**
- attack_holdout_block_rate: **None**
- attack_block_rate (suite): **0.7143**
- normal_dev_pass_rate: None
- normal_holdout_pass_rate: **None**
- kb_benign_fp_rate: 0.0

### `normal-dev` (diagnostic)
- traffic_count: 35
- request_latency_ms_mean: **182.29**
- attack_holdout_block_rate: **None**
- attack_block_rate (suite): **None**
- normal_dev_pass_rate: 1.0
- normal_holdout_pass_rate: **None**
- kb_benign_fp_rate: None

### `normal-holdout` (headline)
- traffic_count: 20
- request_latency_ms_mean: **191.13**
- attack_holdout_block_rate: **None**
- attack_block_rate (suite): **None**
- normal_dev_pass_rate: None
- normal_holdout_pass_rate: **0.6**
- kb_benign_fp_rate: None

### `law-kb-benign` (supporting)
- traffic_count: 18
- request_latency_ms_mean: **178.68**
- attack_holdout_block_rate: **None**
- attack_block_rate (suite): **None**
- normal_dev_pass_rate: None
- normal_holdout_pass_rate: **None**
- kb_benign_fp_rate: 0.5

### `law-full` (supporting)
- traffic_count: 209
- request_latency_ms_mean: **166.86**
- attack_holdout_block_rate: **1.0**
- attack_block_rate (suite): **0.8476**
- normal_dev_pass_rate: 1.0
- normal_holdout_pass_rate: **0.6**
- kb_benign_fp_rate: 0.3265

### `healthcare-domain` (supporting)
- traffic_count: 163
- request_latency_ms_mean: **170.22**
- attack_holdout_block_rate: **0.75**
- attack_block_rate (suite): **0.9524**
- normal_dev_pass_rate: 0.6857
- normal_holdout_pass_rate: **None**
- kb_benign_fp_rate: 0.7273

### `finance-domain` (supporting)
- traffic_count: 163
- request_latency_ms_mean: **172.15**
- attack_holdout_block_rate: **0.75**
- attack_block_rate (suite): **0.9524**
- normal_dev_pass_rate: 0.6857
- normal_holdout_pass_rate: **None**
- kb_benign_fp_rate: 0.75

## Overlap checks
- attack_holdout_clean: **True**
- normal_holdout_clean: **True**
- normal_holdout_vs_dev_collisions: []
- normal_holdout_vs_hard_negatives: []

## Suite directories

- `attack-holdout/` — Attack holdout (cold)
- `attack-seeded/` — Attack seeded overlay
- `normal-dev/` — Normal scenarios (development set)
- `normal-holdout/` — Normal holdout (cold)
- `law-kb-benign/` — Law KB benign queries
- `law-full/` — Law full benchmark
- `healthcare-domain/` — Healthcare domain pack
- `finance-domain/` — Finance domain pack
