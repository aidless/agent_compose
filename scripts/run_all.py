"""One-command reproduction of all template-agent AgentCompose results.

Pipelines the full benchmark workflow:

  1. generate.py            → data/generated/{train,val,test_*}.jsonl
  2. evaluate.py --agent X  → results/{agent}_{split}.json  × 5 agents × 4 splits
  3. bootstrap_ci.py        → results/bootstrap_ci.json
  4. statistical_eval.py    → results/statistical_tests.json
  5. make_cd_diagram.py     → figures/fig6_cd_diagram.{pdf,png}
  6. make_figures.py        → figures/fig{1..5}_*.{pdf,png}

Usage:
    python scripts/run_all.py                 # full pipeline incl. DeepSeek aggregation
    python scripts/run_all.py --skip-llm      # skip DeepSeek-only steps
    python scripts/run_all.py --skip-eval     # skip per-agent eval (assume already done)

Each step aborts the pipeline on failure with a non-zero exit code so CI can
catch regressions. Total wall-clock on a single CPU core is ~15-20 minutes
(--skip-llm) or ~3 hours (with DeepSeek N=100, depending on API latency).

DeepSeek API key is loaded from `.env` (gitignored) via `evaluate_llm.py`.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Each step: (label, command template, is_optional)
# - is_optional=False: always runs unless --skip-eval applies
# - is_optional=True:  only runs when --skip-llm is NOT set
STEPS_FULL: list[tuple[str, str, bool]] = [
    ("generate", "python scripts/generate.py --seed 42", False),
    ("eval:react",         "python scripts/evaluate.py --agent react --split all",            False),
    ("eval:native_fc",     "python scripts/evaluate.py --agent native_fc --split all",        False),
    ("eval:reflexion",     "python scripts/evaluate.py --agent reflexion --split all",        False),
    ("eval:plan_execute",  "python scripts/evaluate.py --agent plan_execute --split all",     False),
    ("eval:chain_aware",   "python scripts/evaluate.py --agent chain_aware --split all",      False),
    ("bootstrap_ci",       "python scripts/bootstrap_ci.py",                                  False),
    ("statistical_eval",   "python scripts/statistical_eval.py",                              False),
    ("make_cd_diagram",    "python scripts/make_cd_diagram.py",                               False),
    ("make_figures",       "python scripts/make_figures.py",                                  False),
    # DeepSeek aggregation — assumes per-split DeepSeek runs already
    # completed and results/deepseek_*_summary.json exists. To run the LLM
    # evaluations themselves, use scripts/evaluate_llm.py directly.
    ("aggregate:deepseek_react", "python scripts/aggregate_llm.py --agent deepseek_react",   True),
    ("aggregate:deepseek_fc",    "python scripts/aggregate_llm.py --agent deepseek_fc",      True),
    ("regen_figures_with_llm",   "python scripts/make_figures.py",                            True),
]

AGENT_LIST = ["react", "native_fc", "reflexion", "plan_execute", "chain_aware"]


def run_step(label: str, cmd: str, cwd: Path) -> float:
    """Run a single step. Return elapsed seconds. Raises on non-zero exit."""
    print(f"\n{'=' * 70}")
    print(f"▶ STEP: {label}")
    print(f"  CMD: {cmd}")
    print(f"  CWD: {cwd}")
    print(f"{'=' * 70}")
    start = time.time()
    # Use shlex to safely split; shell=False avoids Windows cmd quoting issues.
    proc = subprocess.run(
        shlex.split(cmd),
        cwd=str(cwd),
        check=False,
    )
    elapsed = time.time() - start
    if proc.returncode != 0:
        print(f"✗ STEP '{label}' FAILED with exit code {proc.returncode}")
        sys.exit(proc.returncode)
    print(f"✓ STEP '{label}' OK ({elapsed:.1f}s)")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full AgentCompose reproduction pipeline.")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip DeepSeek aggregation (steps marked optional).",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip per-agent evaluation (steps 2-6). Use when results/ already populated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without running anything.",
    )
    args = parser.parse_args()

    steps = list(STEPS_FULL)
    if args.skip_eval:
        steps = [s for s in steps if not s[0].startswith("eval:")]
    if args.skip_llm:
        # Skip the optional=True steps (DeepSeek aggregation + regen).
        steps = [s for s in steps if not s[2]]

    total_start = time.time()
    timings: list[tuple[str, float]] = []

    print(f"AgentCompose full reproduction pipeline")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Steps:        {len(steps)}")
    print(f"  Skip LLM:     {args.skip_llm}")
    print(f"  Skip eval:    {args.skip_eval}")

    for label, cmd, _optional in steps:
        if args.dry_run:
            print(f"  [dry-run] {label}: {cmd}")
            continue
        elapsed = run_step(label, cmd, PROJECT_ROOT)
        timings.append((label, elapsed))

    total = time.time() - total_start
    print(f"\n{'=' * 70}")
    print(f"✓ ALL STEPS COMPLETE in {total:.1f}s ({total/60:.1f} min)")
    print(f"{'=' * 70}")
    if timings:
        print("\nStep timings:")
        for label, t in timings:
            print(f"  {label:32s} {t:>8.1f}s")


if __name__ == "__main__":
    main()