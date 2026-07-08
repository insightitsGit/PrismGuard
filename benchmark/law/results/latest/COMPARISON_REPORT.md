# Law Guardrail Benchmark — COMPARISON_REPORT (Bug3)

## Cost / speed (blended latency first)

### CPL
- guard_model_escalation_rate: **0.3175**
- judge_escalation_rate: **0.0053**
- blended_latency_ms: **1226.33**
- fast_path_latency_ms_mean: 1139.23
- guard_model_latency_ms_mean: 1408.61
- judge_latency_ms_mean: 1438.27
- escalated_latency_ms_mean: 1409.1
- latency_ms_mean (flat): 1226.33
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0053

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- blended_latency_ms: **637.53**
- fast_path_latency_ms_mean: 637.53
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 637.53
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- blended_latency_ms: **633.41**
- fast_path_latency_ms_mean: 633.41
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 633.41
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.3175**
- judge_escalation_rate: **0.0053**
- blended_latency_ms: **1347.49**
- fast_path_latency_ms_mean: 1231.33
- guard_model_latency_ms_mean: 1586.45
- judge_latency_ms_mean: 1878.86
- escalated_latency_ms_mean: 1591.25
- latency_ms_mean (flat): 1347.49
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0053

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
- legal_overlay_holdout: **0.5714**
- legal_overlay_seeded: 1.0
- bundled_full: 0.6623
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0053

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
- legal_overlay_holdout: **0.5714**
- legal_overlay_seeded: 1.0
- bundled_full: 0.6623
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0053

## Paired comparisons

### CPL_vs_CGL
- holdout_attack_block_rate_delta: 0.0715
- attack_block_rate_delta: 0.0381
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -588.8
- guard_model_escalation_rate_delta: -0.3175
- judge_escalation_rate_delta: -0.0053
- latency_ms_mean_delta: -588.8

### LPL_vs_LGL
- holdout_attack_block_rate_delta: 0.0715
- attack_block_rate_delta: 0.0381
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -714.08
- guard_model_escalation_rate_delta: -0.3175
- judge_escalation_rate_delta: -0.0053
- latency_ms_mean_delta: -714.08

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: 121.16
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: 121.16

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
- corpus_match: 34
- fusion_allow: 7
- fusion_block: 3
- guard_model: 24
- guard_model_first: 13
- llm_judge: 1
- structural: 8
- tier1_rule: 15

### CGL
- llm_guard_prompt_injection: 105

### LGL
- llm_guard_prompt_injection: 105

### LPL
- corpus_match: 34
- fusion_allow: 7
- fusion_block: 3
- guard_model: 24
- guard_model_first: 13
- llm_judge: 1
- structural: 8
- tier1_rule: 15
