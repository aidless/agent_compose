"""Ablation experiments.

1. n_synthetic_chains: How does ChainAware's productivity improve with more
   synthetic training chains?
2. failure_rate: Does the gap widen under noisy tools?
3. max_steps: Does budget matter?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_compose.agents.chain_aware import ChainAwareAgent
from agent_compose.agents.native_fc import NativeFCAgent
from agent_compose.env.simulator import ToolSimulator
from agent_compose.eval.metrics import Evaluator
from agent_compose.eval.runner import evaluate_split, load_split
from agent_compose.tools import ToolLibrary


def ablation_n_synthetic(data_dir: Path, output_dir: Path, n_values: list[int]) -> None:
    """Vary number of synthetic chains and measure productivity gap."""
    tools_dir = Path(__file__).parent.parent / "tools"
    library = ToolLibrary(tools_dir)
    simulator = ToolSimulator(library, failure_rate=0.0, seed=42)
    train_tasks = load_split(data_dir / "train.jsonl")
    val_tasks = load_split(data_dir / "val.jsonl")
    prod_tasks = load_split(data_dir / "test_productivity.jsonl")

    results = []
    for n in n_values:
        agent = ChainAwareAgent(library, max_steps=10, n_synthetic_chains=n)
        agent.train_on(train_tasks)

        # Measure on productivity split
        task_metrics, _ = evaluate_split(agent, simulator, prod_tasks, "test_productivity")
        metrics = Evaluator().aggregate(task_metrics)
        results.append(
            {
                "n_synthetic": n,
                "tsr_productivity": metrics.tsr,
                "coc_productivity": metrics.coc,
            }
        )
        print(
            f"  n_synthetic={n:>4d}: TSR={metrics.tsr:.3f}, COC={metrics.coc:.3f}"
        )

    output_path = output_dir / "ablation_n_synthetic.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n✓ Saved to {output_path}")


def ablation_failure_rate(data_dir: Path, output_dir: Path, rates: list[float]) -> None:
    """Vary simulator failure_rate and measure gap."""
    tools_dir = Path(__file__).parent.parent / "tools"
    library = ToolLibrary(tools_dir)
    val_tasks = load_split(data_dir / "val.jsonl")
    prod_tasks = load_split(data_dir / "test_productivity.jsonl")

    results = []
    for rate in rates:
        sim = ToolSimulator(library, failure_rate=rate, seed=42)
        agent = NativeFCAgent(library, max_steps=10)

        val_metrics, _ = evaluate_split(agent, sim, val_tasks, "val")
        prod_metrics, _ = evaluate_split(agent, sim, prod_tasks, "test_productivity")
        v = Evaluator().aggregate(val_metrics)
        p = Evaluator().aggregate(prod_metrics)
        gap = v.tsr - p.tsr
        results.append(
            {
                "failure_rate": rate,
                "tsr_val": v.tsr,
                "tsr_productivity": p.tsr,
                "cgg_productivity": gap,
            }
        )
        print(
            f"  failure_rate={rate:.2f}: val_TSR={v.tsr:.3f}, prod_TSR={p.tsr:.3f}, CGG={gap:+.3f}"
        )

    output_path = output_dir / "ablation_failure_rate.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n✓ Saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ablation experiments")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent.parent / "data" / "generated")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent.parent / "results")
    args = parser.parse_args()

    print("=" * 80)
    print("Ablation 1: ChainAware n_synthetic_chains vs Productivity TSR")
    print("=" * 80)
    ablation_n_synthetic(args.data_dir, args.output_dir, n_values=[0, 10, 25, 50, 100])

    print("\n" + "=" * 80)
    print("Ablation 2: failure_rate vs Compositional Gap (NativeFC)")
    print("=" * 80)
    ablation_failure_rate(args.data_dir, args.output_dir, rates=[0.0, 0.1, 0.2, 0.3])


if __name__ == "__main__":
    main()
