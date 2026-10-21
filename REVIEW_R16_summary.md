# AgentCompose - R16 adversarial review summary

## Decision

BLOCKED / major revisions. The canonical package is now mechanically cleaner, but simulator evidence, duplicated heuristic rows, and single-family validation do not support Strong Accept or production-readiness claims.

## Canonical machine gates (2026-08-19)

- Claim ledger: 6 PASS, 0 FAIL, 6 WARN; blocked/inconclusive claims remain explicit.
- Number consistency: 0 stale/inverted CIs, 19 table/prose precision alerts, 167 evidence-only values.
- Statistics: 0 error classes; sample-size declarations include n=0 in a robustness table and require interpretation.
- TMLR compliance: 0 failures.
- Taint: 0 tainted claims and 0 missing-evidence errors.
- Hallucination: two missing script-path references (`scripts/generate.py`, `scripts/run_all.py`) and one strong-claim phrase remain to resolve.
- Compile: 0 errors after replacing cross-file Supplementary `\ref` calls with stable text references; 6 unused section labels remain.

## Required P0 revisions

1. Include the exact generator/runner scripts named in the manuscript or remove those names.
2. Seal split-leakage audit, raw per-task traces, and independent seeds in the submission manifest.
3. Collapse or statistically account for behaviorally duplicated heuristic rows before Friedman ranking; report distinct-behavior sensitivity.
4. Validate EquivAware equivalence groups with independent semantic adjudication and strict-scoring controls.
5. Replicate DeepSeek-V4-Flash results across vendors/models and seeds; keep the current pilot directional.
6. Remove production-readiness language and add a human/safety/deployment audit.
7. Reconcile the 19 precision alerts and remove the 6 unused labels.

Current defensible scope: a simulator benchmark with a single-family LLM pilot, not a general production agent-composition result.

## Revision R17 (2026-08-19)

- Removed external script paths from the anonymous TMLR manuscript and `README_TMLR.md`; the package now explicitly distinguishes frozen evidence artifacts from the de-anonymized source repository.
- Recompiled `paper_tmlr/main.tex` successfully (12 pages, exit code 0; no compile errors).
- Hallucination scan rerun: 0 missing method files, 0 citation errors, 0 arithmetic errors. The remaining strong-claim surface and 210 uncovered numeric literals are scientific/ledger work, not hidden missing-file references.
- The package remains **BLOCKED / major revisions** because raw task traces, distinct-behavior ranking, semantic adjudication, cross-vendor replication, and production-safety validation are still absent.

## Execution status (2026-08-19 continuation)

The package remains **BLOCKED / major revisions**. Current evidence supports a simulator benchmark and directional single-family pilot only; production-readiness and cross-vendor generalization claims remain prohibited until raw traces, independent adjudication, and replicated seeds/models are sealed.
