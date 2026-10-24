"""Tests for evaluation metrics and statistical tests."""

from __future__ import annotations

from agent_compose.env.simulator import ExecutionTrace, ToolCall, ToolResult
from agent_compose.eval.metrics import Evaluator
from agent_compose.eval.statistical_tests import (
    cohens_d,
    friedman_test,
    wilcoxon_test,
)
from agent_compose.generator.tasks import Task


def make_task(template_id: str = "T1_test", chain: list[str] | None = None) -> Task:
    return Task(
        task_id=f"test_{template_id}",
        template_id=template_id,
        natural_language="Test task.",
        expected_chain=chain or ["search_web", "send_email"],
        parameters={"location": "Tokyo", "recipient_email": "alice@example.com"},
        success_criteria=["email sent"],
        split="test",
    )


def make_trace(
    task: Task, calls: list[tuple[str, dict]], all_succeed: bool = True
) -> ExecutionTrace:
    trace = ExecutionTrace(task_id=task.task_id)
    for i, (tool_name, args) in enumerate(calls):
        call = ToolCall(tool_name=tool_name, arguments=args, call_id=f"c{i}")
        result = ToolResult(call_id=f"c{i}", tool_name=tool_name, success=all_succeed, output=None)
        trace.calls.append(call)
        trace.results.append(result)
    return trace


def test_tsr_perfect_match() -> None:
    task = make_task(chain=["search_web", "send_email"])
    trace = make_trace(
        task,
        [
            ("search_web", {"query": "weather Tokyo"}),
            ("send_email", {"to": "alice@example.com", "subject": "x", "body": "y"}),
        ],
    )
    metrics = Evaluator().evaluate_task(task, trace)
    assert metrics.tsr == 1.0


def test_tsr_missing_tool() -> None:
    task = make_task(chain=["search_web", "send_email"])
    trace = make_trace(task, [("search_web", {"query": "x"})])
    metrics = Evaluator().evaluate_task(task, trace)
    assert metrics.tsr == 0.0


def test_coc_correct_order() -> None:
    task = make_task(chain=["search_web", "send_email"])
    trace = make_trace(
        task,
        [
            ("search_web", {"query": "x"}),
            ("send_email", {"to": "a", "subject": "b", "body": "c"}),
        ],
    )
    metrics = Evaluator().evaluate_task(task, trace)
    assert metrics.coc == 1.0


def test_coc_wrong_order() -> None:
    task = make_task(chain=["search_web", "send_email"])
    trace = make_trace(
        task,
        [
            ("send_email", {"to": "a", "subject": "b", "body": "c"}),
            ("search_web", {"query": "x"}),
        ],
    )
    metrics = Evaluator().evaluate_task(task, trace)
    assert metrics.coc < 1.0


def test_aba_argument_binding() -> None:
    task = make_task(chain=["search_web", "send_email"])
    trace = make_trace(
        task,
        [
            ("search_web", {"query": "weather Tokyo"}),
            ("send_email", {"to": "alice@example.com", "subject": "x", "body": "y"}),
        ],
    )
    metrics = Evaluator().evaluate_task(task, trace)
    assert metrics.aba > 0.0  # At least one param was bound


def test_aggregate_split_metrics() -> None:
    task = make_task(chain=["search_web", "send_email"])
    trace1 = make_trace(
        task,
        [
            ("search_web", {"query": "x"}),
            ("send_email", {"to": "alice@example.com", "subject": "x", "body": "y"}),
        ],
    )
    trace2 = make_trace(task, [("search_web", {"query": "y"})])
    task2 = make_task(template_id="T2", chain=["search_web"])
    task2.task_id = "test_T2"

    evaluator = Evaluator()
    metrics_list = [
        evaluator.evaluate_task(task, trace1),
        evaluator.evaluate_task(task2, trace2),
    ]
    split = evaluator.aggregate(metrics_list)
    assert split.n_tasks == 2


def test_wilcoxon_significant() -> None:
    # Clear difference: A always 1.0, B always 0.0
    a = [1.0] * 20
    b = [0.0] * 20
    result = wilcoxon_test(a, b, "AgentA", "AgentB", "tsr")
    assert result.p_value < 0.05
    assert result.significant_at_05


def test_wilcoxon_not_significant() -> None:
    # Same distributions
    a = [0.5, 0.6, 0.7, 0.5, 0.6, 0.7, 0.5, 0.6, 0.7, 0.5]
    b = [0.5, 0.6, 0.7, 0.5, 0.6, 0.7, 0.5, 0.6, 0.7, 0.5]
    result = wilcoxon_test(a, b, "A", "B", "tsr")
    assert not result.significant_at_05


def test_cohens_d() -> None:
    a = [1.0, 1.0, 1.0, 1.0, 1.0]
    b = [0.0, 0.0, 0.0, 0.0, 0.0]
    d = cohens_d(a, b)
    assert d > 1.0  # Large effect


def test_friedman_three_agents() -> None:
    results = {
        "A": [0.8, 0.9, 0.7, 0.85, 0.75, 0.9, 0.8, 0.85, 0.7, 0.9],
        "B": [0.6, 0.7, 0.5, 0.65, 0.55, 0.7, 0.6, 0.65, 0.5, 0.7],
        "C": [0.4, 0.5, 0.3, 0.45, 0.35, 0.5, 0.4, 0.45, 0.3, 0.5],
    }
    result = friedman_test(results, "tsr")
    assert result["test"] == "friedman"
    assert result["n_agents"] == 3
    # Clear ordering A > B > C should be detected
    assert result["p_value"] < 0.05
