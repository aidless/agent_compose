"""Error analysis: categorize failures into 4 types.

Error types:
1. WRONG_TOOL: called a tool not in the expected chain
2. WRONG_ORDER: called the right tools but in wrong order
3. MISSING_TOOL: failed to call one of the expected tools
4. BAD_ARGUMENT: called right tool with wrong/missing arguments
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from agent_compose.env.simulator import ExecutionTrace
from agent_compose.generator.tasks import Task


class ErrorType(Enum):
    NONE = "none"
    WRONG_TOOL = "wrong_tool"
    WRONG_ORDER = "wrong_order"
    MISSING_TOOL = "missing_tool"
    BAD_ARGUMENT = "bad_argument"


@dataclass
class ErrorReport:
    """Per-task error breakdown."""

    task_id: str
    split: str
    error_type: ErrorType
    expected_chain: list[str]
    actual_chain: list[str]
    details: dict[str, Any]


def analyze_task_errors(task: Task, trace: ExecutionTrace) -> ErrorReport:
    """Identify the dominant error type for one task execution."""
    expected = task.expected_chain
    actual = [c.tool_name for c in trace.calls]
    expected_set = set(expected)
    actual_set = set(actual)

    # 1. Missing tool: any expected tool not called
    missing = expected_set - actual_set
    if missing:
        return ErrorReport(
            task_id=task.task_id,
            split=task.split,
            error_type=ErrorType.MISSING_TOOL,
            expected_chain=expected,
            actual_chain=actual,
            details={"missing_tools": list(missing)},
        )

    # 2. Wrong tool: called extra tools not in expected chain
    extra = actual_set - expected_set
    if extra:
        return ErrorReport(
            task_id=task.task_id,
            split=task.split,
            error_type=ErrorType.WRONG_TOOL,
            expected_chain=expected,
            actual_chain=actual,
            details={"extra_tools": list(extra)},
        )

    # 3. Wrong order: tools present but not in expected sequence
    # Use longest common subsequence
    lcs_len = _lcs_length(expected, actual)
    if lcs_len < len(expected):
        return ErrorReport(
            task_id=task.task_id,
            split=task.split,
            error_type=ErrorType.WRONG_ORDER,
            expected_chain=expected,
            actual_chain=actual,
            details={"lcs_length": lcs_len, "expected_length": len(expected)},
        )

    # 4. Check argument binding
    param_hit_rate = _argument_binding(task, trace)
    if param_hit_rate < 0.5:
        return ErrorReport(
            task_id=task.task_id,
            split=task.split,
            error_type=ErrorType.BAD_ARGUMENT,
            expected_chain=expected,
            actual_chain=actual,
            details={"param_hit_rate": param_hit_rate},
        )

    return ErrorReport(
        task_id=task.task_id,
        split=task.split,
        error_type=ErrorType.NONE,
        expected_chain=expected,
        actual_chain=actual,
        details={},
    )


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longest common subsequence length."""
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def _argument_binding(task: Task, trace: ExecutionTrace) -> float:
    """Fraction of task parameters that appear in any tool call's arguments."""
    params = task.parameters
    if not params:
        return 1.0
    all_args = " ".join(str(c.arguments).lower() for c in trace.calls)
    hits = 0
    total = 0
    for val in params.values():
        if isinstance(val, (str, int, float)):
            total += 1
            if str(val).lower() in all_args:
                hits += 1
    return hits / total if total else 1.0


def aggregate_errors(reports: list[ErrorReport]) -> dict[str, dict[str, int]]:
    """Aggregate error counts by split and error type."""
    out: dict[str, dict[str, int]] = {}
    for r in reports:
        out.setdefault(r.split, {}).setdefault(r.error_type.value, 0)
        out[r.split][r.error_type.value] += 1
    return out


def error_rates(reports: list[ErrorReport]) -> dict[str, dict[str, float]]:
    """Compute error rates (fraction of tasks) by split and error type."""
    counts = aggregate_errors(reports)
    rates: dict[str, dict[str, float]] = {}
    for split, type_counts in counts.items():
        total = sum(type_counts.values())
        rates[split] = {t: c / total for t, c in type_counts.items()}
    return rates
