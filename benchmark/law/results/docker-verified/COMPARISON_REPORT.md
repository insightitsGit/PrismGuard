# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.0899**
- judge_escalation_rate: **0.0688**
- request_latency_ms_mean: **400.98**
- guard_latency_ms_mean: **391.26**
- pipeline_latency_ms_mean: 391.32
- blended_latency_ms: **400.98** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 381.8
- guard_model_latency_ms_mean: 500.69
- judge_latency_ms_mean: 505.27
- escalated_latency_ms_mean: 502.68
- latency_ms_mean (flat): 400.98
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **1221.38**
- guard_latency_ms_mean: **1216.89**
- pipeline_latency_ms_mean: 1217.39
- blended_latency_ms: **1221.38** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 1221.38
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 1221.38
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **435.01**
- guard_latency_ms_mean: **426.07**
- pipeline_latency_ms_mean: 428.11
- blended_latency_ms: **435.01** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 435.01
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 435.01
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.0899**
- judge_escalation_rate: **0.0688**
- request_latency_ms_mean: **384.27**
- guard_latency_ms_mean: **369.67**
- pipeline_latency_ms_mean: 370.99
- blended_latency_ms: **384.27** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 365.68
- guard_model_latency_ms_mean: 454.92
- judge_latency_ms_mean: 519.27
- escalated_latency_ms_mean: 482.81
- latency_ms_mean (flat): 384.27
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

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
- legal_overlay_holdout: **0.8571**
- legal_overlay_seeded: 1.0
- bundled_full: 0.8961
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

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
- legal_overlay_holdout: **0.8571**
- legal_overlay_seeded: 1.0
- bundled_full: 0.8961
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: -0.2142
- attack_block_rate_delta: -0.1715
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 820.4
- guard_model_escalation_rate_delta: -0.0899
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: 820.4

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.2142
- attack_block_rate_delta: -0.1715
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 50.74
- guard_model_escalation_rate_delta: -0.0899
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: 50.74

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -16.71
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -16.71

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
- corpus_match: 16
- fusion_allow: 3
- fusion_block: 3
- guard_model: 6
- guard_model_first: 41
- llm_judge: 2
- structural: 11
- tier1_rule: 23

### CGL
- llm_guard_prompt_injection: 105

### LGL
- llm_guard_prompt_injection: 105

### LPL
- corpus_match: 16
- fusion_allow: 3
- fusion_block: 3
- guard_model: 6
- guard_model_first: 41
- llm_judge: 2
- structural: 11
- tier1_rule: 23
