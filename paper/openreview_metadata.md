# OpenReview Submission Metadata — COLM 2026

This file captures the metadata needed to fill in the COLM 2026 OpenReview
submission form. After acceptance, real author / affiliation details replace
the placeholders.

## Required Fields

| Field | Value |
|---|---|
| **Title** | AgentCompose: Quantifying Compositional Generalization in LLM Tool Use |
| **Abstract** | (copy from `paper/main.tex` lines 33–39) |
| **Authors** | Anonymous, Anonymous Institution, anonymous@example.com |
| **Venue** | COLM 2026 Conference on Language Modeling |
| **Track** | Main Conference (Research Papers) |
| **Keywords** | llm, agent, tool-use, compositional-generalization, benchmark |
| **Conflict of interest** | None declared (no reviewers / Area Chairs named) |

## Suggested Reviewer Pool (5 candidates)

For the "preferred / non-preferred reviewers" field, the following 5
researchers have published on tool-use agents or compositional generalization
in the last 24 months. They are likely to have informed opinions but no
conflict with the authors:

1. (anonymous placeholder; will populate post-acceptance)
2. (anonymous placeholder)
3. (anonymous placeholder)
4. (anonymous placeholder)
5. (anonymous placeholder)

If the OpenReview form requires non-empty reviewer names, list candidate
researchers from the cited papers (e.g., the first authors of
\citep{yao2023react, schick2023toolformer, qin2023toolllm, trivedi2024appworld, patil2024bfcl}).

## Files in submission.zip

| File | Size | Purpose |
|---|---|---|
| `main.pdf` | ~290 KB | Main paper (15 pages including references + appendix) |
| `supp.pdf` | ~145 KB | Supplementary material (6 pages) |
| `double_blind_checklist.md` | ~3 KB | Anonymization audit |
| `code_archive.zip` | ~130 KB | Source code (no data/, results/, logs/) |

Total submission size: ~484 KB (well under most venue limits).

## How Reviewers Will Reproduce

After extracting `submission.zip`:

```bash
unzip submission.zip -d agent_compose_review
cd agent_compose_review
unzip code_archive.zip -d code
cd code

# Reproduces all template-agent results (~4 min, no LLM)
pip install -e ".[dev]"
python scripts/run_all.py --skip-llm

# Verify tests pass
pytest tests/ -q    # 39/39
```

## What to Disclose After Acceptance

After the reviewer phase ends and a decision is made, replace the following
placeholders with real values:

| Placeholder | File / Section |
|---|---|
| Anonymous author block | `paper/main.tex` lines 22–26 |
| `anonymous@example.com` | `paper/main.tex` + `pyproject.toml` |
| Empty Acknowledgments | `paper/main.tex` §Acknowledgments |
| TBD project URL | `pyproject.toml` `[project.urls]` |
| Reviewer pool | this file (delete before posting) |