"""Evaluate LLM-backed agent on AgentCompose splits.

Usage:
    python scripts/evaluate_llm.py --agent deepseek_react --split val --max-tasks 30
    python scripts/evaluate_llm.py --agent deepseek_react --split all --max-tasks 50
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from agent_compose.agents.llm_react import DeepSeekFCAgent, DeepSeekReactAgent
from agent_compose.env.simulator import ToolSimulator
from agent_compose.eval.metrics import Evaluator
from agent_compose.eval.runner import evaluate_split, load_split, save_results
from agent_compose.tools import ToolLibrary


AGENT_REGISTRY = {
    "deepseek_react": DeepSeekReactAgent,
    "deepseek_fc": DeepSeekFCAgent,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LLM-backed agent")
    parser.add_argument("--agent", choices=list(AGENT_REGISTRY.keys()), default="deepseek_react")
    parser.add_argument(
        "--split",
        choices=["train", "val", "test_systematicity", "test_productivity", "test_substitutability", "all"],
        default="all",
    )
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent.parent / "data" / "generated")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent.parent / "results")
    parser.add_argument("--max-tasks", type=int, default=None, help="Limit tasks per split")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--model", type=str, default="deepseek-v4-flash")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tools_dir = Path(__file__).parent.parent / "tools"
    library = ToolLibrary(tools_dir)
    simulator = ToolSimulator(library, failure_rate=0.0, seed=args.seed)

    agent_cls = AGENT_REGISTRY[args.agent]
    agent = agent_cls(library, max_steps=args.max_steps, model=args.model)

    splits = (
        ["val", "test_systematicity", "test_productivity", "test_substitutability"]
        if args.split == "all"
        else [args.split]
    )

    summary: dict[str, dict] = {}
    for split_name in splits:
        file_path = args.data_dir / f"{split_name}.jsonl"
        if not file_path.exists():
            print(f"⚠ {file_path} not found")
            continue

        tasks = load_split(file_path)
        if args.max_tasks:
            tasks = tasks[: args.max_tasks]

        print(f"\n▶ Running {args.agent} on {split_name} ({len(tasks)} tasks)...")
        t0 = time.time()
        task_metrics, traces = evaluate_split(agent, simulator, tasks, split_name)
        elapsed = time.time() - t0

        eval_ = Evaluator()
        agg = eval_.aggregate(task_metrics)
        output_path = args.output_dir / f"{args.agent}_{split_name}.json"
        save_results(output_path, task_metrics, traces, agent.name, split_name)

        print(f"  TSR: {agg.tsr:.3f} | COC: {agg.coc:.3f} | ABA: {agg.aba:.3f}")
        print(f"  Tokens: {agent._total_tokens} | Time: {elapsed:.1f}s ({elapsed/len(tasks):.1f}s/task)")
        # DeepSeek V4 Flash pricing (estimate): $0.14/M input, $0.28/M output
        cost_est = agent._total_tokens * 0.00000021  # avg of input/output
        print(f"  Est. cost: ${cost_est:.4f}")

        summary[split_name] = {
            "tsr": agg.tsr,
            "coc": agg.coc,
            "aba": agg.aba,
            "n": agg.n_tasks,
            "tokens": agent._total_tokens,
            "time_s": elapsed,
        }

    if summary and "val" in summary and "test_productivity" in summary:
        cgg = summary["val"]["tsr"] - summary["test_productivity"]["tsr"]
        print(f"\n🎯 CGG (val - productivity): {cgg:+.3f}")

    if summary:
        summary_path = args.output_dir / f"{args.agent}_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\n✓ Summary → {summary_path}")


if __name__ == "__main__":
    main()
