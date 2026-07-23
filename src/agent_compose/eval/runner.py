"""Evaluation runner: orchestrates agent execution across a split."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agent_compose.agents.base import Agent, AgentRunResult
from agent_compose.env.simulator import ExecutionTrace, ToolSimulator
from agent_compose.eval.metrics import Evaluator, SplitMetrics, TaskMetrics
from agent_compose.generator.tasks import Task


def load_split(file_path: Path) -> list[Task]:
    """Load tasks from a JSONL file."""
    tasks = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            tasks.append(
                Task(
                    task_id=data["task_id"],
                    template_id=data["template_id"],
                    natural_language=data["natural_language"],
                    expected_chain=data["expected_chain"],
                    parameters=data["parameters"],
                    success_criteria=data["success_criteria"],
                    split=data.get("split", "unknown"),
                    metadata=data.get("metadata", {}),
                )
            )
    return tasks


def run_task(agent: Agent, simulator: ToolSimulator, task: Task) -> tuple[ExecutionTrace, int]:
    """Run one task through the agent loop. Returns (trace, total_steps)."""
    simulator.reset_state()
    # Reset any agent-level state (e.g., Reflexion memory, Plan-Execute plan)
    if hasattr(agent, "reset"):
        agent.reset()
    trace = ExecutionTrace(task_id=task.task_id)
    total_steps = 0

    for step_num in range(agent.max_steps):
        step = agent.act(task, trace)
        if step.action is None:
            trace.termination_reason = "agent_stopped"
            break
        # Execute the action
        result = simulator.execute(step.action)
        trace.calls.append(step.action)
        trace.results.append(result)
        total_steps += 1
        # Track final state from side-effect tools
        if simulator.state.get("sent_emails"):
            trace.final_state["last_email"] = simulator.state["sent_emails"][-1]
        if simulator.state.get("written_files"):
            trace.final_state["last_file"] = list(simulator.state["written_files"].keys())[-1]
        if simulator.state.get("calendar_events"):
            trace.final_state["last_event"] = simulator.state["calendar_events"][-1]
    else:
        trace.termination_reason = "max_steps_reached"

    # Mark success based on final state matching success criteria
    trace.success = _evaluate_trace_success(task, trace)
    return trace, total_steps


def _evaluate_trace_success(task: Task, trace: ExecutionTrace) -> bool:
    """Heuristic: trace is successful if all expected tools were called and no errors."""
    expected = set(task.expected_chain)
    actual = {c.tool_name for c in trace.calls}
    if not expected.issubset(actual):
        return False
    # No critical errors (ignore synthetic failures)
    for r in trace.results:
        if not r.success and not r.failed_injected:
            return False
    return True


def evaluate_split(
    agent: Agent,
    simulator: ToolSimulator,
    tasks: list[Task],
    split_name: str,
    max_tasks: int | None = None,
) -> tuple[list[TaskMetrics], list[ExecutionTrace]]:
    """Run an agent on a split and return metrics + traces."""
    evaluator = Evaluator()
    task_metrics_list: list[TaskMetrics] = []
    traces: list[ExecutionTrace] = []

    task_iter = tasks[:max_tasks] if max_tasks else tasks
    for task in task_iter:
        trace, _ = run_task(agent, simulator, task)
        metrics = evaluator.evaluate_task(task, trace)
        task_metrics_list.append(metrics)
        traces.append(trace)

    return task_metrics_list, traces


def save_results(
    output_path: Path,
    task_metrics: list[TaskMetrics],
    traces: list[ExecutionTrace],
    agent_name: str,
    split_name: str,
) -> None:
    """Save evaluation results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "agent": agent_name,
        "split": split_name,
        "n_tasks": len(task_metrics),
        "task_metrics": [
            {
                "task_id": m.task_id,
                "template_id": m.template_id,
                "split": m.split,
                "tsr": m.tsr,
                "tca": m.tca,
                "coc": m.coc,
                "aba": m.aba,
                "n_calls": m.n_calls,
                "expected_chain": m.expected_chain,
            }
            for m in task_metrics
        ],
        "traces": [
            {
                "task_id": t.task_id,
                "calls": [{"tool": c.tool_name, "args": c.arguments} for c in t.calls],
                "results": [{"success": r.success, "output": r.output} for r in t.results],
                "success": t.success,
                "termination_reason": t.termination_reason,
            }
            for t in traces
        ],
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
