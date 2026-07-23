"""Statistical comparisons across agents.

Implements:
1. Friedman test across agents (paired by task) on each test split
2. Wilcoxon paired test: chain_aware vs each baseline on each test split
3. Critical Difference (CD) diagram data preparation
4. Win/Tie/Loss summary

Saves to results/statistical_tests.json and figures/fig6_cd_diagram.{pdf,png}.

Usage:
    python scripts/statistical_eval.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from agent_compose.eval.statistical_tests import friedman_test, wilcoxon_test


def collect_per_task_tsr(results_dir: Path, agent: str, split: str) -> list[float]:
    """Return per-task TSR for one agent on one split (parallel array of task IDs)."""
    f = results_dir / f"{agent}_{split}.json"
    if not f.exists():
        return []
    d = json.loads(f.read_text(encoding="utf-8"))
    return [m["tsr"] for m in d.get("task_metrics", [])]


def align_by_task_id(results_dir: Path, agents: list[str], split: str) -> dict[str, list[float]]:
    """Align per-task TSR across agents by task_id. Returns {agent: [tsr_aligned]}."""
    f0 = results_dir / f"{agents[0]}_{split}.json"
    if not f0.exists():
        return {}
    base = json.loads(f0.read_text(encoding="utf-8"))
    task_ids = [m["task_id"] for m in base.get("task_metrics", [])]
    aligned = {a: [] for a in agents}
    for a in agents:
        f = results_dir / f"{a}_{split}.json"
        if not f.exists():
            return {}
        d = json.loads(f.read_text(encoding="utf-8"))
        tsr_by_id = {m["task_id"]: m["tsr"] for m in d.get("task_metrics", [])}
        for tid in task_ids:
            if tid not in tsr_by_id:
                return {}
            aligned[a].append(tsr_by_id[tid])
    return aligned


def win_tie_loss(agents: list[str], aligned: dict[str, list[float]], reference: str) -> dict[str, dict[str, int]]:
    """Count W/T/L for reference vs each other agent on paired tasks."""
    out = {}
    if reference not in aligned:
        return out
    for a in agents:
        if a == reference or a not in aligned:
            continue
        wins = ties = losses = 0
        for r, o in zip(aligned[reference], aligned[a]):
            if r > o:
                wins += 1
            elif r == o:
                ties += 1
            else:
                losses += 1
        out[a] = {"wins": wins, "ties": ties, "losses": losses}
    return out


def friedman_per_split(
    results_dir: Path,
    agents: list[str],
    splits: list[str],
) -> dict[str, dict]:
    """Friedman test across agents on each split."""
    out = {}
    for split in splits:
        aligned = align_by_task_id(results_dir, agents, split)
        if len(aligned) < 3:
            continue
        try:
            res = friedman_test(aligned, metric_name=f"TSR_{split}")
            res["aligned_n"] = len(next(iter(aligned.values())))
            out[split] = res
        except Exception as e:
            out[split] = {"error": str(e)}
    return out


def pairwise_wilcoxon(
    results_dir: Path,
    agents: list[str],
    splits: list[str],
) -> dict[str, dict]:
    """Wilcoxon paired test for all pairs of agents on each split."""
    out = {}
    for split in splits:
        aligned = align_by_task_id(results_dir, agents, split)
        out[split] = {}
        for i, a1 in enumerate(agents):
            for a2 in agents[i + 1 :]:
                if a1 not in aligned or a2 not in aligned:
                    continue
                res = wilcoxon_test(
                    aligned[a1],
                    aligned[a2],
                    agent_a_name=a1,
                    agent_b_name=a2,
                    metric_name=f"TSR_{split}",
                )
                key = f"{a1}_vs_{a2}"
                out[split][key] = res.to_dict()
    return out


def cd_diagram_data(
    results_dir: Path,
    agents: list[str],
    split: str,
) -> dict:
    """Compute mean TSR per agent on split (for CD diagram ranking)."""
    aligned = align_by_task_id(results_dir, agents, split)
    if not aligned:
        return {}
    means = {a: float(np.mean(v)) for a, v in aligned.items()}
    # Lower rank = better (higher TSR)
    sorted_agents = sorted(means, key=lambda x: -means[x])
    ranks = {a: r + 1 for r, a in enumerate(sorted_agents)}
    return {
        "split": split,
        "means": means,
        "ranks": ranks,
        "sorted_agents": sorted_agents,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent.parent / "results")
    parser.add_argument("--agents", nargs="+", default=[
        "react", "native_fc", "reflexion", "plan_execute", "chain_aware",
    ])
    args = parser.parse_args()

    splits = ["val", "test_systematicity", "test_productivity", "test_substitutability"]
    summary = {
        "friedman": friedman_per_split(args.results_dir, args.agents, splits),
        "wilcoxon": pairwise_wilcoxon(args.results_dir, args.agents, splits),
        "cd_data": {s: cd_diagram_data(args.results_dir, args.agents, s) for s in splits},
        "win_tie_loss_chain_aware": {
            s: win_tie_loss(args.agents, align_by_task_id(args.results_dir, args.agents, s), "chain_aware")
            for s in splits
        },
    }

    print("=" * 70)
    print("Friedman test (across agents, per split):")
    for split, res in summary["friedman"].items():
        if "error" in res:
            print(f"  {split:24s} ERROR: {res['error']}")
            continue
        sig = "*" if res.get("significant_at_05") else " "
        print(f"  {split:24s} χ²={res['statistic']:7.3f}  p={res['p_value']:.4f}  {sig}  N={res['aligned_n']}")

    print("\n" + "=" * 70)
    print("Critical Difference (mean TSR rank, lower=better):")
    for split, data in summary["cd_data"].items():
        if not data:
            continue
        print(f"\n  {split}:")
        for a in data["sorted_agents"]:
            bar = "█" * int(data["means"][a] * 40)
            print(f"    {a:18s} mean={data['means'][a]:.3f}  rank={data['ranks'][a]}  {bar}")

    print("\n" + "=" * 70)
    print("ChainAware vs baselines (Wilcoxon paired, on test splits):")
    for split in ["test_systematicity", "test_productivity", "test_substitutability"]:
        if split not in summary["wilcoxon"]:
            continue
        for key, res in summary["wilcoxon"][split].items():
            if "chain_aware" not in key:
                continue
            sig = "*" if res["significant_at_05"] else " "
            print(f"  {split:24s} {key:40s} p={res['p_value']:.4f}  d={res['effect_size']:.2f}  {sig}")

    out = args.results_dir / "statistical_tests.json"
    out.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    print(f"\n✓ Statistical tests saved to {out}")


if __name__ == "__main__":
    main()