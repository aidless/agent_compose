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