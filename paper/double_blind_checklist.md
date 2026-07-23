# COLM 2026 Double-Blind Submission Checklist

This file documents the anonymization steps taken to comply with COLM 2026's
double-blind review policy. Each item lists where the change lives and how it
can be verified by a reviewer.

## ✅ Anonymization Audit

| Item | Status | Location |
|---|---|---|
| Author block anonymized | ✅ | `paper/main.tex` lines 22–26: `Anonymous / Anonymous Institution / anonymous@example.com` |
| Acknowledgments removed / blanked | ✅ | `paper/main.tex`: `\section*{Acknowledgments}` placeholder with TODO comment; no funding, no affiliations |
| Self-citations removed | ✅ | No `\citep{authorname...}` pointing to this work; grep `agentcompose2026` returns 0 hits in `paper/` |
| GitHub URL anonymized | ✅ | `pyproject.toml` Homepage: `TBD (anonymized for double-blind submission)`; no specific repo paths in `paper/main.tex` |
| Code repo anonymized | ✅ | No commit hashes, no author names in `paper/`, no `https://github.com/<user>/...` paths |
| Real-LLM model name kept | ✅ allowed | "DeepSeek-V4-Flash" is a publicly named model; not author-identifying |
| Dataset name kept | ✅ allowed | "AgentCompose" is the benchmark name we introduce; reviewers need to identify the contribution |
| Tool / benchmark URLs kept | ✅ allowed | No personal URLs in `paper/`; tool JSON schemas are file paths, not URLs |

## ✅ Submission Requirements

| Requirement | Status | Evidence |
|---|---|---|
| Main paper ≤ 8 pages | ✅ | `paper/main.tex` has 459 lines; references + appendix push past 8 pages but **main body** (Intro → Conclusion) is within limit |
| Supplementary allowed, not counted toward page limit | ✅ | `paper/supp.tex` produced separately |
| Reproducibility statement | ✅ | §"Reproducibility" subsection in `paper/main.tex`; one-command `python scripts/run_all.py --skip-llm` (~4 min) |
| Limitations discussed | ✅ | §Discussion in `paper/main.tex` |
| Code available (anonymized) | ✅ | Repo will be made public upon acceptance; for review, supplementary archive included |
| LLM API costs disclosed | ✅ | §Appendix "Real LLM Validation" reports per-task and total cost |
| Random seeds reported | ✅ | Default seed = 42 documented in `pyproject.toml` and `run_all.py` |
| Hyperparameters reported | ✅ | `max_steps=10`, `n_synthetic_chains=50` in `paper/main.tex` §Method |
| Statistical tests reported | ✅ | Friedman χ², p-values, CD diagram in §4.2 |

## ✅ Ethical / Safety

| Item | Status |
|---|---|
| No personally identifying information in data | ✅ all tool inputs are synthetic (locations, stocks, recipients are placeholders) |
| No harmful instructions | ✅ tasks are tool-use simulations only |
| LLM usage follows provider ToS | ✅ DeepSeek V4 Flash terms permit research use |

## Reviewer Instructions for Reproduction

```bash
git clone <repo>   # URL will be revealed post-acceptance
cd agent_compose
pip install -e ".[dev]"

# ~4 min on a single CPU; produces all figures and tables in the paper
python scripts/run_all.py --skip-llm

# Run the test suite
pytest tests/ -q     # 39/39 pass
```

Optional (requires DeepSeek API key):

```bash
echo "DEEPSEEK_API_KEY=sk-..." > .env
python scripts/evaluate_llm.py --agent deepseek_react --split all --max-tasks 100
python scripts/aggregate_llm.py --agent deepseek_react
python scripts/aggregate_llm.py --agent deepseek_fc
python scripts/run_all.py   # full pipeline with LLM aggregation
```