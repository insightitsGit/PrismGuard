# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.6111**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **178.68**
- guard_latency_ms_mean: **168.52**
- pipeline_latency_ms_mean: 168.63
- blended_latency_ms: **178.68** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 171.6
- guard_model_latency_ms_mean: 183.19
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: 183.19
- latency_ms_mean (flat): 178.68
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **146.09**
- guard_latency_ms_mean: **140.66**
- pipeline_latency_ms_mean: 140.79
- blended_latency_ms: **146.09** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 146.09
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 146.09
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **172.2**
- guard_latency_ms_mean: **160.97**
- pipeline_latency_ms_mean: 163.3
- blended_latency_ms: **172.2** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 172.2
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 172.2
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.6111**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **193.57**
- guard_latency_ms_mean: **178.93**
- pipeline_latency_ms_mean: 182.27
- blended_latency_ms: **193.57** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 206.54
- guard_model_latency_ms_mean: 185.31
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: 185.31
- latency_ms_mean (flat): 193.57
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

## Normal holdout (cold false-positive eval — cite for external claims)

## Normal scenarios — development set (used in tuning/training; not cold eval)

## Held-out attack block rates

### CPL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### CGL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: None
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -32.59
- guard_model_escalation_rate_delta: -0.6111
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -32.59

### LPL_vs_LGL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: None
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -21.37
- guard_model_escalation_rate_delta: -0.6111
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -21.37

### CPL_vs_LPL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: None
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 14.89
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 14.89

## Overlap check
- holdout_clean: None
- holdout_vs_prismguard_seed_collisions: []
- holdout_vs_seeded_overlay_collisions: []
- holdout_vs_bundled_full_collisions: []
- holdout_vs_tenant_sim_collisions: []
- bundled_full_vs_authored_count: None
- bundled_full_minus_authored_count: None

## Resolution gate distribution (attacks)
