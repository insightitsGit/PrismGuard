# Law Guardrail Benchmark — COMPARISON_REPORT (Bug3)

## Cost / speed (blended latency first)

### CPL
- guard_model_escalation_rate: **0.1005**
- judge_escalation_rate: **0.0688**
- blended_latency_ms: **1258.66**
- fast_path_latency_ms_mean: 1127.57
- guard_model_latency_ms_mean: 1842.45
- judge_latency_ms_mean: 1988.67
- escalated_latency_ms_mean: 1901.85
- latency_ms_mean (flat): 1258.66
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- blended_latency_ms: **243.54**
- fast_path_latency_ms_mean: 243.54
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 243.54
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- blended_latency_ms: **220.66**
- fast_path_latency_ms_mean: 220.66
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 220.66
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.1005**
- judge_escalation_rate: **0.0688**
- blended_latency_ms: **976.05**
- fast_path_latency_ms_mean: 840.55
- guard_model_latency_ms_mean: 1577.88
- judge_latency_ms_mean: 1732.9
- escalated_latency_ms_mean: 1640.86
- latency_ms_mean (flat): 976.05
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
- blended_latency_ms_delta: -1015.12
- guard_model_escalation_rate_delta: -0.1005
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: -1015.12

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.2142
- attack_block_rate_delta: -0.1715
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -755.39
- guard_model_escalation_rate_delta: -0.1005
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: -755.39

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -282.61
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -282.61

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
