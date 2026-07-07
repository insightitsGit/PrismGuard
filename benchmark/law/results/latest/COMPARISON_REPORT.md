# Law Guardrail Benchmark — COMPARISON_REPORT

## Stack summaries (attack block rate first)

### CPL
- attack_block_rate: **1.0**
- false_positive_rate: **0.0**
- task_success_rate: 0.8333
- guard_llm_calls_mean: 0
- latency_ms_mean: 6.25

### CRL
- attack_block_rate: **0.0**
- false_positive_rate: **0.0**
- task_success_rate: 0.8333
- guard_llm_calls_mean: 0
- latency_ms_mean: 0.02

### LNL
- attack_block_rate: **0.0**
- false_positive_rate: **0.0**
- task_success_rate: 0.8333
- guard_llm_calls_mean: 0
- latency_ms_mean: 0.97

### LPL
- attack_block_rate: **1.0**
- false_positive_rate: **0.0**
- task_success_rate: 0.8333
- guard_llm_calls_mean: 0
- latency_ms_mean: 7.06

## Paired comparisons

### CPL_vs_CRL
- attack_block_rate_delta: -1.0
- false_positive_rate_delta: 0.0
- task_success_rate_delta: 0.0
- guard_llm_calls_mean_delta: 0
- latency_ms_mean_delta: -6.23

### LPL_vs_LNL
- attack_block_rate_delta: -1.0
- false_positive_rate_delta: 0.0
- task_success_rate_delta: 0.0
- guard_llm_calls_mean_delta: 0
- latency_ms_mean_delta: -6.09

### CPL_vs_LPL
- attack_block_rate_delta: 0.0
- false_positive_rate_delta: 0.0
- task_success_rate_delta: 0.0
- guard_llm_calls_mean_delta: 0
- latency_ms_mean_delta: 0.81
