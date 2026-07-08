# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (client request_latency_ms first)

_Primary latency = HTTP client wall clock (`request_latency_ms`). Guard-only = `guard_latency_ms`. In-process pipeline = `pipeline_latency_ms`._

### CPL
- guard_model_escalation_rate: **0.0899**
- judge_escalation_rate: **0.0688**
- request_latency_ms_mean: **1694.16**
- guard_latency_ms_mean: **1612.86**
- pipeline_latency_ms_mean: 1612.91
- blended_latency_ms: **1694.16** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 1478.62
- guard_model_latency_ms_mean: 3084.81
- judge_latency_ms_mean: 2511.97
- escalated_latency_ms_mean: 2836.58
- latency_ms_mean (flat): 1694.16
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **454.63**
- guard_latency_ms_mean: **442.8**
- pipeline_latency_ms_mean: 442.84
- blended_latency_ms: **454.63** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 454.63
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 454.63
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- request_latency_ms_mean: **259.64**
- guard_latency_ms_mean: **230.1**
- pipeline_latency_ms_mean: 232.29
- blended_latency_ms: **259.64** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 259.64
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 259.64
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.0899**
- judge_escalation_rate: **0.0688**
- request_latency_ms_mean: **964.9**
- guard_latency_ms_mean: **920.23**
- pipeline_latency_ms_mean: 924.22
- blended_latency_ms: **964.9** (escalation-weighted client latency)
- fast_path_latency_ms_mean: 831.49
- guard_model_latency_ms_mean: 1605.07
- judge_latency_ms_mean: 1759.39
- escalated_latency_ms_mean: 1671.94
- latency_ms_mean (flat): 964.9
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
- blended_latency_ms_delta: -1239.53
- guard_model_escalation_rate_delta: -0.0899
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: -1239.53

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.2142
- attack_block_rate_delta: -0.1715
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -705.26
- guard_model_escalation_rate_delta: -0.0899
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: -705.26

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -729.26
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -729.26

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
