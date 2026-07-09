# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.2857**
- judge_escalation_rate: **0.1714**
- request_latency_ms_mean: **182.29**
- guard_latency_ms_mean: **174.1**
- pipeline_latency_ms_mean: 174.12
- blended_latency_ms: **182.29** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 186.54
- guard_model_latency_ms_mean: 177.92
- judge_latency_ms_mean: 176.13
- escalated_latency_ms_mean: 177.25
- latency_ms_mean (flat): 182.29
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1714

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **209.78**
- guard_latency_ms_mean: **202.18**
- pipeline_latency_ms_mean: 202.19
- blended_latency_ms: **209.78** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 209.78
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 209.78
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **239.33**
- guard_latency_ms_mean: **227.28**
- pipeline_latency_ms_mean: 229.44
- blended_latency_ms: **239.33** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 239.33
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 239.33
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.2857**
- judge_escalation_rate: **0.1714**
- request_latency_ms_mean: **193.62**
- guard_latency_ms_mean: **181.47**
- pipeline_latency_ms_mean: 184.24
- blended_latency_ms: **193.62** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 198.37
- guard_model_latency_ms_mean: 183.79
- judge_latency_ms_mean: 194.95
- escalated_latency_ms_mean: 187.97
- latency_ms_mean (flat): 193.62
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1714

## Normal holdout (cold false-positive eval — cite for external claims)

## Normal scenarios — development set (used in tuning/training; not cold eval)

### CPL
- pass_rate: **1.0** (35/35)
- guard_model_tier: mixed

### CGL
- pass_rate: **1.0** (35/35)
- guard_model_tier: classifier

### LGL
- pass_rate: **1.0** (35/35)
- guard_model_tier: classifier

### LPL
- pass_rate: **1.0** (35/35)
- guard_model_tier: mixed

## Held-out attack block rates

### CPL
- guard_configured: True
- legal_overlay_holdout: **None**
- legal_overlay_seeded: None
- bundled_full: None
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.1714

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
- guard_generative_llm_calls_mean: 0.1714

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: None
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 27.49
- guard_model_escalation_rate_delta: -0.2857
- judge_escalation_rate_delta: -0.1714
- latency_ms_mean_delta: 27.49

### LPL_vs_LGL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: None
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 45.71
- guard_model_escalation_rate_delta: -0.2857
- judge_escalation_rate_delta: -0.1714
- latency_ms_mean_delta: 45.71

### CPL_vs_LPL
- holdout_attack_block_rate_delta: None
- attack_block_rate_delta: None
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 11.33
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 11.33

## Overlap check
- holdout_clean: None
- holdout_vs_prismguard_seed_collisions: []
- holdout_vs_seeded_overlay_collisions: []
- holdout_vs_bundled_full_collisions: []
- holdout_vs_tenant_sim_collisions: []
- bundled_full_vs_authored_count: None
- bundled_full_minus_authored_count: None

## Resolution gate distribution (attacks)
