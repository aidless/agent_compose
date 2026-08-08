# External Validity — Second Tool Library (2026-08-08)

**Status**: infrastructure ready; full comparison NOT yet valid (honest negative).

## What was built
- `tools_ext/` — second tool library: 20 tools (finance / iot / logistics), 3 equivalence groups
- `templates_ext/task_templates.yaml` — 12 task templates (2-tool minimal chains + 3-tool extensions)
- `scripts/external_validity.py` — driver: generate ext tasks, evaluate 6 agents, compare CGG ordering vs main benchmark
- Generator parameterization: `--tail-tools` / `--head-tools` (extension pools no longer hardcoded to the main library)
- `evaluate.py --tools-dir` — evaluate against an alternate library

## Result (honest)
- Baseline template agents achieve **TCA ≈ 0 / TSR ≈ 0** on the second library, and the
  productivity split cannot be populated by the current generator at the configured sizes.
- This is a **floor effect**: the simple template agents cannot reliably select the
  second library's tools (names/descriptions differ from their tuned prompts), so the
  run does not yet constitute a valid external-validity comparison of CGG ordering.
- `results/external_validity.json` captures the run; its Spearman rows are not
  interpretable because of the floor effect.

## Open items (before external validity can be claimed)
1. Tune agent tool-selection prompts for generic libraries (or report agent tuning as part of the comparison).
2. Enrich tool descriptions so baseline selection is non-trivial (target val TSR >= 0.15-0.25).
3. Verify productivity generation at scale for the second library (check `data/generated_ext/test_productivity.jsonl`).
4. Re-run `python scripts/external_validity.py` and only then interpret CGG ordering.

## Repro
```
python scripts/external_validity.py
```
---

## Update (2026-08-08, phase 2): library-agnostic inference

Root cause of the phase-1 floor effect: all template agents used hardcoded
main-library keyword maps for tool selection. We added a flag-gated,
library-agnostic inference path (`agents/inference.py`,
`--use-generic-inference`; default OFF, so main-benchmark results are
unchanged).

With generic inference on the second library:

| Agent | Val | Systematicity | Substitutability |
|---|---|---|---|
| ReAct / Reflexion | 0.00 | 0.19-0.20 | 0.92-0.95 |
| Native FC | 0.00 | 0.19 | 0.95 |
| Plan-Execute | 0.00 | 0.19 | 0.92 |
| ChainAware | 0.10 | 0.54 | 1.00 |

- Systematicity and substitutability are now non-degenerate and
  ChainAware remains best on both — qualitatively consistent with the main
  benchmark's ranking.
- **Productivity remains structurally empty** on the second library: all 12
  external templates supply 2-tool minimal chains that enter the training
  set, so no productivity chain can avoid training pairs (generator
  constraint). A valid productivity split needs a template pool partitioned
  into train vs non-train families.
- Val stays near zero: generic argument binding is imperfect; agents need a
  task-parameter→schema binding pass (open item).
- A fair main-benchmark comparison under the same generic inference is
  running (`scripts/run_generic_main.py` → `results/generic_main/`); CGG
  ordering correlation should be recomputed from it, not from the original
  hardcoded-heuristic numbers.

## Next steps (precise)
1. Split external templates into train (subset) vs test (superset) families
   so productivity is constructible.
2. Improve generic argument binding (parameter-name synonyms + NL value extraction).
3. Recompute main-vs-external CGG correlation once both use generic inference.
---

## Update (2026-08-09): train/test template split attempted; final verdict

- Added generator support for train/test template splits (`--train-templates`):
  external templates X1-X6 train, X7-X12 test-only. This makes the
  productivity split constructible (previously empty).
- Re-ran with library-agnostic inference: systematicity and productivity now
  produce numbers, but the validation split remains at TSR ~0.0 for the
  generic agents, and CGG-ordering correlations are negative/NaN.
- **Final honest verdict**: this second-library mini-benchmark is still not a
  valid external-validity comparison. The validation floor (generic argument
  binding cannot yet solve the external 2-tool tasks) invalidates the
  baseline against which the compositional gap is measured. A valid run
  requires: (1) a generic parameter→schema binding pass with NL value
  extraction, and (2) a larger, carefully matched second library.
- Infrastructure (tools_ext, templates_ext, generator split, drivers) is
  complete and committed; the comparison itself is **not claimable**.