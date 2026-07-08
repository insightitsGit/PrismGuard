# Law Guardrail Benchmark — COMPARISON_REPORT

## Cost / speed (blended latency first)

### CPL
- guard_model_escalation_rate: **0.0899**
- judge_escalation_rate: **0.0688**
- blended_latency_ms: **1388.86**
- fast_path_latency_ms_mean: 1258.79
- guard_model_latency_ms_mean: 1996.0
- judge_latency_ms_mean: 2185.85
- escalated_latency_ms_mean: 2078.27
- latency_ms_mean (flat): 1388.86
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0.0688

### CGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- blended_latency_ms: **255.09**
- fast_path_latency_ms_mean: 255.09
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 255.09
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LGL
- guard_model_escalation_rate: **0.0**
- judge_escalation_rate: **0.0**
- blended_latency_ms: **280.74**
- fast_path_latency_ms_mean: 280.74
- guard_model_latency_ms_mean: None
- judge_latency_ms_mean: None
- escalated_latency_ms_mean: None
- latency_ms_mean (flat): 280.74
- guard_classifier_calls_mean: 1
- guard_generative_llm_calls_mean: 0

### LPL
- guard_model_escalation_rate: **0.0899**
- judge_escalation_rate: **0.0688**
- blended_latency_ms: **1198.98**
- fast_path_latency_ms_mean: 1046.89
- guard_model_latency_ms_mean: 1909.47
- judge_latency_ms_mean: 2129.96
- escalated_latency_ms_mean: 2005.02
- latency_ms_mean (flat): 1198.98
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
- blended_latency_ms_delta: -1133.77
- guard_model_escalation_rate_delta: -0.0899
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: -1133.77

### LPL_vs_LGL
- holdout_attack_block_rate_delta: -0.2142
- attack_block_rate_delta: -0.1715
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -918.24
- guard_model_escalation_rate_delta: -0.0899
- judge_escalation_rate_delta: -0.0688
- latency_ms_mean_delta: -918.24

### CPL_vs_LPL
- holdout_attack_block_rate_delta: 0.0
- attack_block_rate_delta: 0.0
- normal_scenario_pass_rate_delta: 0.0
- guard_classifier_calls_mean_delta: 0.0
- blended_latency_ms_delta: -189.88
- guard_model_escalation_rate_delta: 0.0
- judge_escalation_rate_delta: 0.0
- latency_ms_mean_delta: -189.88

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
