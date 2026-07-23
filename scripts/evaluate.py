"""Evaluate an agent on AgentCompose splits.

Usage:
    python scripts/evaluate.py --agent react --split test_productivity --max-tasks 30
    python scripts/evaluate.py --agent native_fc --split all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_compose.agents.chain_aware import ChainAwareAgent
from agent_compose.agents.native_fc import NativeFCAgent
from agent_compose.agents.plan_execute import PlanExecuteAgent
from agent_compose.agents.react import ReActAgent
from agent_compose.agents.reflexion import ReflexionAgent
from agent_compose.env.simulator import ToolSimulator
from agent_compose.eval.metrics import Evaluator
from agent_compose.eval.runner import evaluate_split, load_split, save_results
from agent_compose.tools import ToolLibrary


AGENT_REGISTRY = {
    "react": ReActAgent,
    "native_fc": NativeFCAgent,
    "reflexion": ReflexionAgent,
    "plan_execute": PlanExecuteAgent,
    "chain_aware": ChainAwareAgent,
}


def make_chain_aware(tasks: list, agent_cls):
    """Special factory: ChainAware needs training data."""
    return agent_cls


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate an agent on AgentCompose")
    parser.add_argument(
        "--agent",
        choices=list(AGENT_REGISTRY.keys()),
        default="react",
        help="Agent to evaluate",
    )
    parser.add_argument(
        "--split",
        choices=["train", "val", "test_systematicity", "test_productivity", "test_substitutability", "all"],
        default="all",
    )
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent.parent / "data" / "generated")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent.parent / "results")
    parser.add_argument("--max-tasks", type=int, default=None, help="Limit tasks per split (for testing)")
    parser.add_argument("--use-oracle", action="store_true", help="Use oracle chain (upper bound)")
    parser.add_argument("--failure-rate", type=float, default=0.0, help="Tool failure injection rate")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Load tools
    tools_dir = Path(__file__).parent.parent / "tools"
    library = ToolLibrary(tools_dir)

    # Build agent + simulator
    agent_cls = AGENT_REGISTRY[args.agent]
    agent = agent_cls(library, max_steps=10, use_oracle=args.use_oracle)
    simulator = ToolSimulator(library, failure_rate=args.failure_rate, seed=args.seed)

    # Special: ChainAware needs training first
    if args.agent == "chain_aware":
        train_file = args.data_dir / "train.jsonl"
        if train_file.exists():
            train_tasks = load_split(train_file)
            agent.train_on(train_tasks)
            print(f"✓ ChainAware: trained on {len(train_tasks)} tasks (+synthetic chains)")

    # Determine splits to run
    if args.split == "all":
        splits = ["val", "test_systematicity", "test_productivity", "test_substitutability"]
    else:
        splits = [args.split]

    evaluator = Evaluator()
    results_summary = {}

    for split_name in splits:
        file_path = args.data_dir / f"{split_name}.jsonl"
        if not file_path.exists():
            print(f"⚠ Split file not found: {file_path}")
            print("  Run `python scripts/generate.py` first.")
            continue

        tasks = load_split(file_path)
        task_metrics, traces = evaluate_split(
            agent, simulator, tasks, split_name,
            max_tasks=args.max_tasks, library=library,
        )
        split_metrics = evaluator.aggregate(task_metrics)

        # Save
        output_path = args.output_dir / f"{args.agent}_{split_name}.json"
        save_results(output_path, task_metrics, traces, agent.name, split_name)

        print(f"\n{args.agent} on {split_name}:")
        print(f"  N tasks: {split_metrics.n_tasks}")
        print(f"  TSR:     {split_metrics.tsr:.3f} ± {split_metrics.tsr_std:.3f}")
        print(f"  TCA:     {split_metrics.tca:.3f}")
        print(f"  COC:     {split_metrics.coc:.3f}")
        print(f"  ABA:     {split_metrics.aba:.3f}")
        print(f"  → saved to {output_path}")

        results_summary[split_name] = {
            "tsr": split_metrics.tsr,
            "tca": split_metrics.tca,
            "coc": split_metrics.coc,
            "aba": split_metrics.aba,
            "n": split_metrics.n_tasks,
        }

    # Save summary
    if results_summary:
        summary_path = args.output_dir / f"{args.agent}_summary.json"
        summary_path.write_text(json.dumps(results_summary, indent=2), encoding="utf-8")
        print(f"\n✓ Summary saved to {summary_path}")

        # Compute CGG if we have all splits
        if "val" in results_summary and "test_productivity" in results_summary:
            cgg = results_summary["val"]["tsr"] - results_summary["test_productivity"]["tsr"]
            print(f"\n🎯 Compositional Generalization Gap (val - productivity): {cgg:+.3f}")


if __name__ == "__main__":
    main()
