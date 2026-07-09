# Law Guardrail Benchmark — COMPARISON_REPORT

**Authoritative run (2026-07-09).** Cite via `benchmark/law/results/current/`. Supersedes `verified/`, `latest/`, and `post-holdout-fix/`.

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.2243**
- judge_escalation_rate: **0.0701**
- request_latency_ms_mean: **211.16**
- guard_latency_ms_mean: **199.81**
- pipeline_latency_ms_mean: 199.84
- blended_latency_ms: **211.16** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 196.17
- guard_model_latency_ms_mean: 250.58
- judge_latency_ms_mean: 235.92
- escalated_latency_ms_mean: 247.09
- latency_ms_mean (flat): 211.16
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0701

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **352.73**
- guard_latency_ms_mean: **342.27**
- pipeline_latency_ms_mean: 342.3
- blended_latency_ms: **352.73** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 352.73
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 352.73
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **374.89**
- guard_latency_ms_mean: **358.37**
- pipeline_latency_ms_mean: 361.17
- blended_latency_ms: **374.89** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 374.89
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 374.89
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.2243**
- judge_escalation_rate: **0.0701**
- request_latency_ms_mean: **253.74**
- guard_latency_ms_mean: **230.91**
- pipeline_latency_ms_mean: 233.83
- blended_latency_ms: **253.74** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 235.96
- guard_model_latency_ms_mean: 302.39
- judge_latency_ms_mean: 277.1
- escalated_latency_ms_mean: 296.37
- latency_ms_mean (flat): 253.74
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0701

## Normal scenario holdout (cold false-positive eval — cite for external claims)

### CPL
- pass_rate: **1.0** (25/25)
- normal_scenario_holdout: **1.0**
- guard_model_tier: mixed

### CGL
- pass_rate: **1.0** (25/25)
- normal_scenario_holdout: **1.0**
- guard_model_tier: classifier

### LGL
- pass_rate: **1.0** (25/25)
- normal_scenario_holdout: **1.0**
- guard_model_tier: classifier

### LPL
- pass_rate: **1.0** (25/25)
- normal_scenario_holdout: **1.0**
- guard_model_tier: mixed

## Normal scenario seeded (development set — used in tuning/training; not cold eval)

### CPL
- pass_rate: **1.0** (35/35)
- normal_scenario_seeded: **1.0**
- guard_model_tier: mixed

### CGL
- pass_rate: **1.0** (35/35)
- normal_scenario_seeded: **1.0**
- guard_model_tier: classifier

### LGL
- pass_rate: **1.0** (35/35)
- normal_scenario_seeded: **1.0**
- guard_model_tier: classifier

### LPL
- pass_rate: **1.0** (35/35)
- normal_scenario_seeded: **1.0**
- guard_model_tier: mixed

## Held-out attack block rates

### CPL
- guard_configured: True
- legal_overlay_holdout: **1.0**
- legal_overlay_seeded: 0.7143
- bundled_full: 0.8442
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0701

### CGL
- guard_configured: True
- legal_overlay_holdout: **0.6429**
- legal_overlay_seeded: 0.7143
- bundled_full: 0.7532
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_configured: True
- legal_overlay_holdout: **0.6429**
- legal_overlay_seeded: 0.7143
- bundled_full: 0.7532
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_configured: True
- legal_overlay_holdout: **1.0**
- legal_overlay_seeded: 0.7143
- bundled_full: 0.8442
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0701

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: -0.3571
- attack_block_rate_delta: -0.1143
- normal_scenario_holdout_pass_rate_delta: 0.0
- normal_scenario_seeded_pass_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 141.57
- guard_model_escalation_rate_delta: -0.2243
- judge_escalation_rate_delta: -0.0701
- latency_ms_mean_delta: 141.57

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.3571
- attack_block_rate_delta: -0.1143
- normal_scenario_holdout_pass_rate_delta: 0.0
- normal_scenario_seeded_pass_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 121.15
- guard_model_escalation_rate_delta: -0.2243
- judge_escalation_rate_delta: -0.0701
- latency_ms_mean_delta: 121.15

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_holdout_pass_rate_delta: 0.0
- normal_scenario_seeded_pass_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 42.58
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 42.58

## Overlap check
- holdout_clean: True
- holdout_vs_prismguard_seed_collisions: []
- holdout_vs_seeded_overlay_collisions: []
- holdout_vs_bundled_full_collisions: []
- holdout_vs_tenant_sim_collisions: []
- bundled_full_vs_authored_count: 40
- bundled_full_minus_authored_count: 22369

## Resolution gate distribution (attacks)

### CPL
- guard_model: 24
- guard_model_first: 41
- llm_judge: 4
- structural: 13
- tier1_rule: 23

### CGL
- llm_guard_prompt_injection: 105

### LGL
- llm_guard_prompt_injection: 105

### LPL
- guard_model: 24
- guard_model_first: 41
- llm_judge: 4
- structural: 13
- tier1_rule: 23
