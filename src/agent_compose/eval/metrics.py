"""Evaluation metrics for AgentCompose.

Metrics:
- TSR (Task Success Rate): end-to-end task success
- TCA (Tool Call Accuracy): correct tool selection
- CGG (Compositional Generalization Gap): TSR_drop from i.i.d. to compositional
- COC (Chain Order Correctness): tool chain order matches expected
- ABA (Argument Binding Accuracy): argument values correctly propagated
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_compose.env.simulator import ExecutionTrace
from agent_compose.generator.tasks import Task


def _trace_satisfies_task(task: Task, trace: ExecutionTrace, library=None) -> bool:
    """Check whether the trace satisfies the task, with substitutability support.

    An expected tool is considered 'called' if it appears in the trace OR an
    equivalent tool (from the same equivalence group) appears.
    """
    expected = set(task.expected_chain)
    actual = {c.tool_name for c in trace.calls}

    equiv_groups: list[set[str]] = []
    if library is not None:
        for group in library.equivalence_groups:
            members = {group["canonical"], *group.get("variants", [])}
            equiv_groups.append(members)

    def is_satisfied(exp_tool: str) -> bool:
        if exp_tool in actual:
            return True
        for group in equiv_groups:
            if exp_tool in group and (group & actual):
                return True
        return False

    for exp_tool in expected:
        if not is_satisfied(exp_tool):
            return False
    # No critical errors (ignore synthetic failures)
    for r in trace.results:
        if not r.success and not r.failed_injected:
            return False
    return True


@dataclass
class TaskMetrics:
    """Per-task metrics."""

    task_id: str
    template_id: str
    split: str
    tsr: float  # 1.0 if success else 0.0
    tca: float  # fraction of tool calls that were correct
    coc: float  # 1.0 if order matches expected chain
    aba: float  # fraction of arguments that match expectations
    n_calls: int
    expected_chain: list[str] = field(default_factory=list)


@dataclass
class SplitMetrics:
    """Aggregated metrics for one split."""

    split_name: str
    n_tasks: int
    tsr: float
    tca: float
    coc: float
    aba: float
    tsr_std: float = 0.0


@dataclass
class CompositionalGap:
    """The compositional generalization gap analysis."""

    iid_metrics: SplitMetrics
    systematicity_metrics: SplitMetrics
    productivity_metrics: SplitMetrics
    substitutability_metrics: SplitMetrics

    @property
    def systematicity_gap(self) -> float:
        return self.iid_metrics.tsr - self.systematicity_metrics.tsr

    @property
    def productivity_gap(self) -> float:
        return self.iid_metrics.tsr - self.productivity_metrics.tsr

    @property
    def substitutability_gap(self) -> float:
        return self.iid_metrics.tsr - self.substitutability_metrics.tsr


class Evaluator:
    """Compute evaluation metrics from agent execution traces."""

    def evaluate_task(self, task: Task, trace: ExecutionTrace) -> TaskMetrics:
        """Compute metrics for a single task execution."""
        expected_chain = task.expected_chain
        actual_chain = [c.tool_name for c in trace.calls]

        # TSR: check side effects match success criteria (substitutability-aware)
        tsr = 1.0 if _trace_satisfies_task(task, trace) else 0.0

        # TCA: fraction of calls matching expected tools (set comparison)
        expected_set = set(expected_chain)
        actual_set = set(actual_chain)
        if expected_set:
            tca = len(expected_set & actual_set) / len(expected_set)
        else:
            tca = 0.0

        # COC: order correctness (Longest Common Subsequence-based)
        coc = self._chain_order_score(expected_chain, actual_chain)

        # ABA: argument binding accuracy
        aba = self._argument_binding_score(task, trace)

        return TaskMetrics(
            task_id=task.task_id,
            template_id=task.template_id,
            split=task.split,
            tsr=tsr,
            tca=tca,
            coc=coc,
            aba=aba,
            n_calls=len(trace.calls),
            expected_chain=expected_chain,
        )

    def _check_success(self, task: Task, trace: ExecutionTrace) -> bool:
        """Check if the trace satisfies the task's success criteria (heuristic)."""
        # A trace is successful if:
        # 1. All expected tools were called at least once
        # 2. The trace terminated naturally (no error)
        expected_set = set(task.expected_chain)
        actual_set = {c.tool_name for c in trace.calls}
        if not expected_set.issubset(actual_set):
            return False
        # Check no critical errors
        for result in trace.results:
            if not result.success and not result.failed_injected:
                # Real execution error (not synthetic)
                return False
        return True

    def _chain_order_score(self, expected: list[str], actual: list[str]) -> float:
        """Fraction of expected tools appearing in the correct relative order."""
        if not expected:
            return 0.0
        # Find positions of expected tools in actual
        positions: list[int] = []
        for exp_tool in expected:
            for i, act_tool in enumerate(actual):
                if act_tool == exp_tool:
                    positions.append(i)
                    break
        if len(positions) != len(expected):
            return 0.0
        # Check monotonicity
        is_monotonic = all(positions[i] <= positions[i + 1] for i in range(len(positions) - 1))
        return 1.0 if is_monotonic else 0.5

    def _argument_binding_score(self, task: Task, trace: ExecutionTrace) -> float:
        """Check if arguments to each tool reference task parameters."""
        params = task.parameters
        if not trace.calls:
            return 0.0
        scores = []
        for call in trace.calls:
            args_str = str(call.arguments).lower()
            # Check if any task parameter value appears in arguments
            hits = 0
            total = 0
            for param_val in params.values():
                if isinstance(param_val, (str, int, float)):
                    total += 1
                    if str(param_val).lower() in args_str:
                        hits += 1
            scores.append(hits / total if total > 0 else 0.0)
        return sum(scores) / len(scores) if scores else 0.0

    def aggregate(self, task_metrics_list: list[TaskMetrics]) -> SplitMetrics:
        """Aggregate task-level metrics into split-level summary."""
        if not task_metrics_list:
            return SplitMetrics(split_name="empty", n_tasks=0, tsr=0, tca=0, coc=0, aba=0)

        n = len(task_metrics_list)
        tsr_vals = [m.tsr for m in task_metrics_list]
        tca_vals = [m.tca for m in task_metrics_list]
        coc_vals = [m.coc for m in task_metrics_list]
        aba_vals = [m.aba for m in task_metrics_list]

        import statistics

        return SplitMetrics(
            split_name=task_metrics_list[0].split,
            n_tasks=n,
            tsr=sum(tsr_vals) / n,
            tca=sum(tca_vals) / n,
            coc=sum(coc_vals) / n,
            aba=sum(aba_vals) / n,
            tsr_std=statistics.stdev(tsr_vals) if n > 1 else 0.0,
        )

    def compute_gap(
        self,
        val_metrics: SplitMetrics,
        sys_metrics: SplitMetrics,
        prod_metrics: SplitMetrics,
        sub_metrics: SplitMetrics,
    ) -> CompositionalGap:
        """Compute the compositional generalization gap."""
        return CompositionalGap(
            iid_metrics=val_metrics,
            systematicity_metrics=sys_metrics,
            productivity_metrics=prod_metrics,
            substitutability_metrics=sub_metrics,
        )
