# AgentCompose

STATUS: WORK-IN-PROGRESS — not A yet

[![Offline tests](https://github.com/aidless/agent_compose/actions/workflows/test.yml/badge.svg)](https://github.com/aidless/agent_compose/actions/workflows/test.yml)
[![Lint](https://github.com/aidless/agent_compose/actions/workflows/lint.yml/badge.svg)](https://github.com/aidless/agent_compose/actions/workflows/lint.yml)

AgentCompose measures whether agents reuse a fixed synthetic tool library in held-out combinations: systematicity (longer chains that still contain a pair seen in training), productivity (adjacent pairs absent from training), and substitutability (one tool swapped for an author-declared equivalent).
It does not measure real APIs, production workflows, or live model quality, and it does not claim a leaderboard, a package release, external users, or a paper acceptance.
STATUS: WORK-IN-PROGRESS — not A yet. The gap list is below. False greens are in [FAILURE_MODES.md](FAILURE_MODES.md).

Package version **0.1.0** (alpha, `Development Status :: 3 - Alpha`). The `0.2.0` string in `tools/_equivalence.json` is a file-local counter, not this package version.

## Two paths

**Offline (no API key).** This is what [`.github/workflows/test.yml`](.github/workflows/test.yml) runs. It does not call a model.

```bash
pip install -e ".[dev]"
pytest -q
```

`pytest` regenerates the seed-42 task set, checks the hash in `benchmark_manifest.json`, and re-scores the five heuristic agents. Collected test count is `n_test_functions` in that manifest (the suite does not use parametrize). One local run of this suite, after dependencies are installed, finishes in seconds. `pip install` is the slow step; a fresh clone with a warm cache stays inside 15 minutes.

**Live models (not CI).** `scripts/evaluate_llm.py` needs `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` in a gitignored `.env`. Nothing in GitHub Actions calls it. A new summary written by that script records the client model string and leaves the date UNKNOWN.

```bash
python scripts/evaluate_llm.py --agent deepseek_react --split val --max-tasks 30
```

`python scripts/run_all.py --skip-llm` reruns the simulator pipeline locally. It is not a CI job, and a zero exit code does not mean the new files match the committed summaries.

## Observed numbers

<!-- OBSERVED:START -->
Pinned by `benchmark_manifest.json` and `tests/test_drift.py`:
36 JSON tool schemas, 25 templates, 8 domains, 6 author-declared equivalence groups, seed 42.
Split sizes: train 1200, val 400, test_systematicity 600, test_productivity 600, test_substitutability 200 (3000 tasks).
Dataset SHA-256: `bcb0902888c206b2754c6cf3d19e9e7defd1b04ff339da9d3828294fbdd3e0e4`.
The JSONL is gitignored. A fresh clone regenerates it; it is not a committed artifact.

### Simulator snapshots

Committed `results/{agent}_summary.json` files do not store a model, date, or seed. Provenance of those files: **UNKNOWN**. They are historical snapshots.
`results/recompute_seed42.json` is an OBSERVED recompute dated 2026-11-09 with seed 42, failure_rate 0, equivalence-tolerant scoring on, and ChainAware's equivalence detector on. Model: none (heuristic agents in the JSON simulator).

| Agent | Split | Committed TSR | Recompute TSR | N |
|---|---|---:|---:|---:|
| react | val | 0.2675 | 0.2675 | 400 |
| react | test_systematicity | 0.428333333333 | 0.428333333333 | 600 |
| react | test_productivity | 0.541666666667 | 0.533333333333 | 600 |
| react | test_substitutability | 0.25 | 0.25 | 200 |
| native_fc | val | 0.2675 | 0.2675 | 400 |
| native_fc | test_systematicity | 0.145 | 0.145 | 600 |
| native_fc | test_productivity | 0.2 | 0.191666666667 | 600 |
| native_fc | test_substitutability | 0.25 | 0.25 | 200 |
| reflexion | val | 0.2675 | 0.2675 | 400 |
| reflexion | test_systematicity | 0.428333333333 | 0.428333333333 | 600 |
| reflexion | test_productivity | 0.541666666667 | 0.533333333333 | 600 |
| reflexion | test_substitutability | 0.25 | 0.25 | 200 |
| plan_execute | val | 0.2675 | 0.2675 | 400 |
| plan_execute | test_systematicity | 0.145 | 0.145 | 600 |
| plan_execute | test_productivity | 0.106666666667 | 0.0983333333333 | 600 |
| plan_execute | test_substitutability | 0.25 | 0.25 | 200 |
| chain_aware | val | 1 | 1 | 400 |
| chain_aware | test_systematicity | 0.438333333333 | 0.438333333333 | 600 |
| chain_aware | test_productivity | 0.451666666667 | 0.443333333333 | 600 |
| chain_aware | test_substitutability | 1 | 1 | 200 |

The recompute differs from the committed summaries in 13 metric cells (TSR, TCA, COC, ABA, or N). The full list is `mismatches_vs_committed_summaries` in `results/recompute_seed42.json`. Do not collapse the two columns into one leaderboard.

### Live LLM fragments

OBSERVED means of `task_metrics` in the committed per-split files. **model: UNKNOWN. date: UNKNOWN. seed: UNKNOWN.**
`deepseek_react_summary.json` contains only `val`. `deepseek_fc_summary.json` contains only `test_substitutability`. Those summary files are not a four-split result.

| File agent field | Split | N | TSR | TCA | COC | ABA |
|---|---|---:|---:|---:|---:|---:|
| DeepSeek-ReAct | val | 200 | 0.125 | 0.475 | 0.12 | 0.469305555556 |
| DeepSeek-ReAct | test_systematicity | 200 | 0.055 | 0.385083333333 | 0.055 | 0.426770833333 |
| DeepSeek-ReAct | test_productivity | 200 | 0.01 | 0.32125 | 0 | 0.308120039683 |
| DeepSeek-ReAct | test_substitutability | 200 | 0.125 | 0.2525 | 0 | 0.471666666667 |
| DeepSeek-FC | val | 200 | 0.155 | 0.4675 | 0.155 | 0.47375 |
| DeepSeek-FC | test_systematicity | 200 | 0.07 | 0.410166666667 | 0.07 | 0.441111111111 |
| DeepSeek-FC | test_productivity | 200 | 0.02 | 0.325416666667 | 0 | 0.327430555556 |
| DeepSeek-FC | test_substitutability | 200 | 0.16 | 0.2475 | 0 | 0.471805555556 |

Each live split above has N=200 stored traces, not the full generated split (val 400, systematicity 600, productivity 600, substitutability 200). Substitutability is the only live split that covers its full generated size, and only by coincidence of that size being 200.
<!-- OBSERVED:END -->

Domain membership and equivalence groups live in `tools/_equivalence.json`. The drift test checks that list against the schema files. Groups are author-declared. They are not an independent adjudication. `calendar_add` / `calendar_list` is one of those groups.

Heuristic agents live under `src/agent_compose/agents/`. ChainAware stores chains from the training split and can swap in an equivalence variant. It is not a trained neural model.

## What this is not yet

STATUS stays WORK-IN-PROGRESS — not A yet, because:

1. No committed live run records model id, date, seed, temperature, and a pre-specified analysis. Trace means above are UNKNOWN on model, date, and seed, and each file holds 200 tasks.
2. The historical simulator summaries and the 2026-11-09 recompute disagree in 13 metric cells. The drift is pinned, not explained.
3. Substitutability success uses author-declared groups plus equivalence-tolerant scoring. A TSR of 1 is not a human judgment that two tools match.
4. ChainAware validation TSR of 1 is replay of training chains, not evidence of compositional generalization.
5. `results/statistical_tests.json` contains bare NaN, and some heuristic agents tie. Those p-values are not a ranking of distinct systems.
6. `figures/` was not regenerated after the plotting code stopped treating a missing split as a gap of 0.
7. There is no package release, no external user report, and no paper acceptance. Drafts under `paper/` and `paper_tmlr/` are manuscripts only.

## Development

```bash
pytest -q
python scripts/check_drift.py
pre-commit run --all-files
```

Lint CI is [`.github/workflows/lint.yml`](.github/workflows/lint.yml) (ruff and black on `src/`, `scripts/`, `tests/`). It does not run the benchmark.

License: MIT.
