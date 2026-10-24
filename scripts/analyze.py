"""Analyze evaluation results: compare agents, compute CGG, output summary.

Usage:
    python scripts/analyze.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_agent_results(results_dir: Path, agent_name: str, split_name: str) -> list[dict]:
    """Load one agent's results on one split."""
    path = results_dir / f"{agent_name}_{split_name}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("task_metrics", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze AgentCompose results")
    parser.add_argument(
        "--results-dir", type=Path, default=Path(__file__).parent.parent / "results"
    )
    args = parser.parse_args()

    # Discover available results
    summary_files = sorted(args.results_dir.glob("*_summary.json"))
    if not summary_files:
        print("⚠ No summary files found. Run `python scripts/evaluate.py` first.")
        return

    print("=" * 80)
    print("AgentCompose Results Summary")
    print("=" * 80)

    all_summaries: dict[str, dict[str, dict]] = {}
    for sf in summary_files:
        data = json.loads(sf.read_text(encoding="utf-8"))
        agent_name = sf.stem.replace("_summary", "")
        all_summaries[agent_name] = data
        print(f"\n📊 {agent_name}")
        print(f"  {'Split':30s} {'N':>5s} {'TSR':>8s} {'TCA':>8s} {'COC':>8s} {'ABA':>8s}")
        print("  " + "-" * 70)
        for split, m in data.items():
            print(
                f"  {split:30s} {m['n']:>5d} {m['tsr']:>8.3f} {m['tca']:>8.3f} "
                f"{m['coc']:>8.3f} {m['aba']:>8.3f}"
            )

    # Compute CGG matrix
    if len(all_summaries) >= 1:
        print("\n" + "=" * 80)
        print("🎯 Compositional Generalization Gap (TSR drop from val)")
        print("=" * 80)
        for agent, summaries in all_summaries.items():
            if "val" not in summaries:
                continue
            val_tsr = summaries["val"]["tsr"]
            print(f"\n  {agent}:")
            print(f"    val (i.i.d.) baseline: {val_tsr:.3f}")
            for split in ["test_systematicity", "test_productivity", "test_substitutability"]:
                if split in summaries:
                    gap = val_tsr - summaries[split]["tsr"]
                    print(f"    {split:25s} TSR={summaries[split]['tsr']:.3f}  CGG={gap:+.3f}")


if __name__ == "__main__":
    main()
