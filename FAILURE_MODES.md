# FAILURE_MODES

What a green run can hide, and what the committed numbers do not support.

## False greens

- **Static badges.** Shields that say "41/41 passing", "3000 tasks", or "30 tools" stay green without executing anything. Those badges are removed. The only status images in the README are GitHub Actions badges for the offline test workflow and the linter.
- **Skipped dataset check.** `tests/test_smoke.py` used to skip when `data/generated/val.jsonl` was missing. A fresh clone then passed without building the dataset. That skip is gone. `tests/test_drift.py` regenerates the seed-42 set and checks its hash. The JSONL stays gitignored.
- **Pipeline exit code.** `scripts/run_all.py --skip-llm` can exit 0 while writing new summaries that differ from the committed files. It is not a CI job, and it does not compare against `results/*_summary.json`.
- **Missing split plotted as zero.** `scripts/make_figures.py` used to draw a compositional gap of 0 when a summary lacked a split. DeepSeek summary files are partial, so a figure built that way can show an unmeasured gap as zero. The plotting code now omits missing splits. The committed `figures/fig1_cgg_bar.*` files were **not** regenerated after that change. Do not read bars in those files as a fresh measurement.
- **Equivalence credit.** With a tool library loaded, task success treats an author-declared variant as a hit. ChainAware also rewrites its chain when the prompt mentions a variant. Substitutability TSR of 1.0 in the chain-aware rows is that mechanism, not an independent judgment that two tools are interchangeable.
- **Tied heuristic agents.** ReAct and Reflexion share the same committed TSR on every split in the historical summaries. A Friedman test on those rows can be "significant" while several systems are copies of each other at the metric that was tested.
- **Hash-seeded set order.** ChainAware used to pick a synthetic-chain bridge with `next(iter(set))`. That order follows `PYTHONHASHSEED`, so a rerun could change argument-binding scores without any code change. The bridge is now `min(shared)`. The 13-cell gap versus the historical summaries is still there after that fix, so set order is not a full explanation of the old files.
- **`statistical_tests.json` is not strict JSON.** It contains bare `NaN` tokens (ties in the Wilcoxon routine). Python's `json` loader accepts them; a strict parser does not.
- **Template paths that look absolute.** Task templates use strings such as `/data/numbers_a.csv` and `/tmp/result_a.txt` as fictional arguments. They are not paths on the machine that ran the benchmark.

## What the results do not support

- They do not support a claim about GPT-4, Claude, or any named live model. The committed per-split files store an agent label (`DeepSeek-ReAct`, `DeepSeek-FC`) and traces. **model, date, and seed are UNKNOWN.** The string `deepseek-v4-flash` in `llm_react.py` is a client default, not a field in those files.
- They do not support the older README table that reported DeepSeek at N=100 with TSR values 0.13 / 0.06 / 0.04 / 0.14 and 0.10 / 0.08 / 0.07. Those figures are not what the committed traces average to. The trace means are in `results/live_llm_observed.json`.
- They do not support reading `deepseek_*_summary.json` as a four-split result. The ReAct summary has only `val`. The FC summary has only `test_substitutability`.
- They do not support "the committed simulator JSON is bitwise recomputable." A seed-42 recompute on 2026-11-09 disagrees with the historical summaries in 13 metric cells. See `results/recompute_seed42.json`.
- They do not support production readiness, real HTTP/email/SQL behavior, or safety of tool use. The environment is a JSON simulator.
- They do not support a paper acceptance, a leaderboard rank, or an external user base. Package version `0.1.0` is an alpha. The `0.2.0` string inside `tools/_equivalence.json` is a file-local counter.
- ChainAware's validation TSR of 1.0 does not support compositional generalization. The agent is trained on the training split's chains and replays them. Validation tasks are short chains from the same generator.
- Author-declared equivalence, including `calendar_add` with `calendar_list`, is not a human adjudication. A perfect substitutability score does not mean a person agreed the tools match.
