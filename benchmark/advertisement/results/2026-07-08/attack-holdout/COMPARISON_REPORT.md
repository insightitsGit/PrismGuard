# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.1667**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **179.71**
- guard_latency_ms_mean: **170.14**
- pipeline_latency_ms_mean: 170.15
- blended_latency_ms: **179.71** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 169.39
- guard_model_latency_ms_mean: 231.32
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: 231.32
- latency_ms_mean (flat): 179.71
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **238.85**
- guard_latency_ms_mean: **231.43**
- pipeline_latency_ms_mean: 231.46
- blended_latency_ms: **238.85** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 238.85
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 238.85
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **246.16**
- guard_latency_ms_mean: **235.9**
- pipeline_latency_ms_mean: 238.08
- blended_latency_ms: **246.16** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 246.16
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 246.16
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.1667**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **169.17**
- guard_latency_ms_mean: **152.52**
- pipeline_latency_ms_mean: 155.06
- blended_latency_ms: **169.17** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 158.36
- guard_model_latency_ms_mean: 223.26
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: 223.26
- latency_ms_mean (flat): 169.17
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

## Normal holdout (cold false-positive eval — cite for external claims)

## Normal scenarios — development set (used in tuning/training; not cold eval)

## Held-out attack block rates

### CPL
- guard_configured: True
- legal_overlay_holdout: **1.0**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### CGL
- guard_configured: True
- legal_overlay_holdout: **0.6429**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_configured: True
- legal_overlay_holdout: **0.6429**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_configured: True
- legal_overlay_holdout: **1.0**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: -0.3571
- attack_block_rate_delta: -0.3571
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 59.14
- guard_model_escalation_rate_delta: -0.1667
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 59.14

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.3571
- attack_block_rate_delta: -0.3571
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 76.99
- guard_model_escalation_rate_delta: -0.1667
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 76.99

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -10.54
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -10.54

## Overlap check
- holdout_clean: None
- holdout_vs_prismguard_seed_collisions: []
- holdout_vs_seeded_overlay_collisions: []
- holdout_vs_bundled_full_collisions: []
- holdout_vs_tenant_sim_collisions: []
- bundled_full_vs_authored_count: None
- bundled_full_minus_authored_count: None

## Resolution gate distribution (attacks)

### CPL
- guard_model: 2
- guard_model_first: 2
- structural: 9
- tier1_rule: 1

### CGL
- llm_guard_prompt_injection: 14

### LGL
- llm_guard_prompt_injection: 14

### LPL
- guard_model: 2
- guard_model_first: 2
- structural: 9
- tier1_rule: 1
