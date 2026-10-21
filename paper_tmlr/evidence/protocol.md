# Evidence protocol — AgentCompose

- Evidence scope: synthetic simulator benchmark, ChainAware training, EquivAware evaluator, and a single-family DeepSeek pilot.
- Every result must record task split, tool library version, simulator seed, agent configuration, model/API version, prompt, raw per-task trace, and analysis script/hash.
- Current package contains aggregate metrics and some per-split artifacts; the DeepSeek validation is single-family and not an external replication.
- No human subjects or PII are used. Side-effect tool tasks are simulated; deployment safety is not inferred from benchmark success.
- dataset: AgentCompose synthetic simulator/tasks, license: repository MIT (verify release URL before submission).
- hardware: CPU/GPU configuration recorded in run metadata; runtime: record wall-clock hours for each sealed run.
