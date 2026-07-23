"""Run error analysis on all agent results.

Usage:
    python scripts/analyze_errors.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from agent_compose.eval.error_analysis import (
    ErrorType,
    analyze_task_errors,
    error_rates,
)
from agent_compose.eval.runner import load_split


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent.parent / "data" / "generated")
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent.parent / "results")
    parser.add_argument("--agents", nargs="+", default=["react", "native_fc", "reflexion", "plan_execute"])
    args = parser.parse_args()

    print("=" * 80)
    print("Error Analysis: 4-Error-Type Breakdown")
    print("=" * 80)

    all_reports = {}
    for agent in args.agents:
        print(f"\n📊 {agent}")
        agent_reports = []
        for split in ["val", "test_systematicity", "test_productivity", "test_substitutability"]:
            split_file = args.data_dir / f"{split}.jsonl"
            results_file = args.results_dir / f"{agent}_{split}.json"
            if not results_file.exists():
                continue
            tasks = load_split(split_file)
            results_data = json.loads(results_file.read_text(encoding="utf-8"))
            traces_by_id = {t["task_id"]: t for t in results_data["traces"]}

            split_reports = []
            for task in tasks:
                if task.task_id not in traces_by_id:
                    continue
                trace_dict = traces_by_id[task.task_id]
                # Reconstruct minimal trace
                from agent_compose.env.simulator import ExecutionTrace, ToolCall, ToolResult

                trace = ExecutionTrace(task_id=task.task_id)
                for i, call_dict in enumerate(trace_dict["calls"]):
                    trace.calls.append(
                        ToolCall(
                            tool_name=call_dict["tool"],
                            arguments=call_dict["args"],
                            call_id=f"c{i}",
                        )
                    )
                    res = trace_dict["results"][i]
                    trace.results.append(
                        ToolResult(
                            call_id=f"c{i}",
                            tool_name=call_dict["tool"],
                            success=res["success"],
                            output=res["output"],
                        )
                    )
                report = analyze_task_errors(task, trace)
                split_reports.append(report)
                agent_reports.append(report)

            if split_reports:
                rates = error_rates(split_reports)
                print(f"  {split}:")
                for et, rate in sorted(rates[split].items(), key=lambda x: -x[1]):
                    n = sum(1 for r in split_reports if r.error_type.value == et)
                    print(f"    {et:20s} {rate:>6.1%}  ({n}/{len(split_reports)})")

        all_reports[agent] = agent_reports

    # Save detailed report
    output_path = args.results_dir / "error_analysis.json"
    output_data = {}
    for agent, reports in all_reports.items():
        output_data[agent] = {
            "rates": error_rates(reports),
            "totals": {split: {et.value: 0 for et in ErrorType} for split in set(r.split for r in reports)},
        }
        for r in reports:
            output_data[agent]["totals"].setdefault(r.split, {}).setdefault(r.error_type.value, 0)
            output_data[agent]["totals"][r.split][r.error_type.value] += 1
    output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(f"\n✓ Saved to {output_path}")


if __name__ == "__main__":
    main()
