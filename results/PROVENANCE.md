# Result provenance

Scores under `results/` are not a leaderboard. Read this file before quoting them.

| Path | Status | Model | Date | Seed | What it is |
|---|---|---|---|---|---|
| `results/{react,native_fc,reflexion,plan_execute,chain_aware}_summary.json` | OBSERVED snapshot | none (heuristic) | UNKNOWN | UNKNOWN (not stored in the file; `evaluate.py` defaults to 42) | Historical simulator summaries. A 2026-11-09 recompute does not match every cell. |
| `results/recompute_seed42.json` | OBSERVED | none | 2026-11-09 | 42 | Fresh heuristic eval pinned by `tests/test_drift.py`. failure_rate 0, equivalence scoring on. |
| `results/deepseek_react_*.json` and `results/deepseek_fc_*.json` | OBSERVED traces | UNKNOWN | UNKNOWN | UNKNOWN | Per-split traces. Means are `results/live_llm_observed.json`. N=200 per split. |
| `results/deepseek_react_summary.json` | OBSERVED, partial | UNKNOWN | UNKNOWN | UNKNOWN | Only `val`. Not a four-split table. |
| `results/deepseek_fc_summary.json` | OBSERVED, partial | UNKNOWN | UNKNOWN | UNKNOWN | Only `test_substitutability`. |
| `results/llm_seed1/`, `results/llm_seed2/` | OBSERVED, partial | UNKNOWN | UNKNOWN | directory name only | Substitutability fragments (N=100). Not a multi-seed study. |
| `results/statistical_tests.json` | OBSERVED | n/a | UNKNOWN | UNKNOWN | Contains bare `NaN`. Not strict JSON. |
| `results/bootstrap_ci.json` and `figures/` | OBSERVED artifacts | n/a | UNKNOWN | UNKNOWN | Not regenerated in the honesty pass. `fig1` may still show unmeasured gaps as zero. |

`scripts/evaluate_llm.py` now writes a `_provenance` object on new summaries (model = the client setting of that process, date = UNKNOWN). Older files were not rewritten.
