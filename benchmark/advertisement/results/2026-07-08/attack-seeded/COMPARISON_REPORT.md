# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.3333**
- judge_escalation_rate: **0.1111**
- request_latency_ms_mean: **155.9**
- guard_latency_ms_mean: **149.8**
- pipeline_latency_ms_mean: 149.81
- blended_latency_ms: **155.9** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 116.03
- guard_model_latency_ms_mean: 197.69
- judge_latency_ms_mean: 229.92
- escalated_latency_ms_mean: 205.75
- latency_ms_mean (flat): 155.9
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1111

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **236.22**
- guard_latency_ms_mean: **227.01**
- pipeline_latency_ms_mean: 227.04
- blended_latency_ms: **236.22** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 236.22
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 236.22
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **220.35**
- guard_latency_ms_mean: **209.22**
- pipeline_latency_ms_mean: 211.22
- blended_latency_ms: **220.35** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 220.35
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 220.35
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.3333**
- judge_escalation_rate: **0.1111**
- request_latency_ms_mean: **154.23**
- guard_latency_ms_mean: **143.07**
- pipeline_latency_ms_mean: 145.24
- blended_latency_ms: **154.23** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 114.35
- guard_model_latency_ms_mean: 196.83
- judge_latency_ms_mean: 225.84
- escalated_latency_ms_mean: 204.08
- latency_ms_mean (flat): 154.23
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1111

## Normal holdout (cold false-positive eval — cite for external claims)

## Normal scenarios — development set (used in tuning/training; not cold eval)

## Held-out attack block rates

### CPL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: 0.7143
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1111

### CGL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: 0.7143
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: 0.7143
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: 0.7143
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1111

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 80.32
- guard_model_escalation_rate_delta: -0.3333
- judge_escalation_rate_delta: -0.1111
- latency_ms_mean_delta: 80.32

### LPL_vs_LGL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 66.12
- guard_model_escalation_rate_delta: -0.3333
- judge_escalation_rate_delta: -0.1111
- latency_ms_mean_delta: 66.12

### CPL_vs_LPL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: None
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -1.67
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -1.67

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
- guard_model: 5
- guard_model_first: 4
- llm_judge: 1
- tier1_rule: 4

### CGL
- llm_guard_prompt_injection: 14

### LGL
- llm_guard_prompt_injection: 14

### LPL
- guard_model: 5
- guard_model_first: 4
- llm_judge: 1
- tier1_rule: 4
