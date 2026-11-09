# Claim ledger - AgentCompose

| ID | Claim | Evidence | Values | Verification | Status |
|---|---|---|---|---|---|
| C01 | Benchmark uses 36 tool schemas and a seed-42 generator that emits 3,000 tasks | `benchmark_manifest.json`, `tests/test_drift.py` | tools=36; tasks=3000; JSONL gitignored | Hash checked in offline pytest | generator count verified; JSONL not committed |
| C02 | ChainAware improves systematicity/productivity in simulation | results | aggregate effects | Add raw task traces and independent seeds | inconclusive |
| C03 | EquivAware reaches 1.000 substitutability | results | score=1.000 | Validate equivalence groups and semantic adjudication | inconclusive |
| C04 | Friedman ranking is interpretable with duplicated heuristic rows | evidence/gaps_agentcompose.md | duplicated behavior | Distinct-behavior analysis and multiplicity plan | blocked |
| C05 | DeepSeek-V4-Flash pilot generalizes to real LLMs | external_validity | N=100/split; one family | Cross-vendor multi-seed replication | inconclusive |
| C06 | Benchmark success implies production readiness | evidence/gaps_agentcompose.md | simulator-only | Human/safety/deployment validation | blocked |

Simulator and single-family pilot evidence cannot support production-wide conclusions.
