# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.3122**
- judge_escalation_rate: **0.0794**
- request_latency_ms_mean: **158.51**
- guard_latency_ms_mean: **150.83**
- pipeline_latency_ms_mean: 150.86
- blended_latency_ms: **158.51** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 139.82
- guard_model_latency_ms_mean: 190.19
- judge_latency_ms_mean: 177.22
- escalated_latency_ms_mean: 187.56
- latency_ms_mean (flat): 158.51
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0794

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **197.62**
- guard_latency_ms_mean: **190.32**
- pipeline_latency_ms_mean: 190.35
- blended_latency_ms: **197.62** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 197.62
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 197.62
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **196.68**
- guard_latency_ms_mean: **185.32**
- pipeline_latency_ms_mean: 187.21
- blended_latency_ms: **196.68** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 196.68
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 196.68
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.3122**
- judge_escalation_rate: **0.0794**
- request_latency_ms_mean: **169.45**
- guard_latency_ms_mean: **155.9**
- pipeline_latency_ms_mean: 158.02
- blended_latency_ms: **169.45** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 156.23
- guard_model_latency_ms_mean: 192.46
- judge_latency_ms_mean: 180.26
- escalated_latency_ms_mean: 189.99
- latency_ms_mean (flat): 169.45
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0794

## Normal scenarios (false-positive stress test)

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
- legal_overlay_holdout: **1.0**
- legal_overlay_seeded: 0.7143
- bundled_full: 0.8442
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0794

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
- guard_generative_llm_calls_mean: 0.0794

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: -0.3571
- attack_block_rate_delta: -0.1143
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 39.11
- guard_model_escalation_rate_delta: -0.3122
- judge_escalation_rate_delta: -0.0794
- latency_ms_mean_delta: 39.11

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.3571
- attack_block_rate_delta: -0.1143
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 27.23
- guard_model_escalation_rate_delta: -0.3122
- judge_escalation_rate_delta: -0.0794
- latency_ms_mean_delta: 27.23

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 10.94
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 10.94

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
