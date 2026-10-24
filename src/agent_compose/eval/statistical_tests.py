"""Statistical tests for comparing agents across splits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from scipy import stats


@dataclass
class ComparisonResult:
    """Result of comparing two sets of metric values."""

    agent_a: str
    agent_b: str
    metric_name: str
    mean_a: float
    mean_b: float
    mean_diff: float
    statistic: float
    p_value: float
    significant_at_05: bool
    effect_size: float  # Cohen's d
    test_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "metric": self.metric_name,
            "mean_a": self.mean_a,
            "mean_b": self.mean_b,
            "mean_diff": self.mean_diff,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "significant_at_05": self.significant_at_05,
            "effect_size": self.effect_size,
            "test_name": self.test_name,
        }


def cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Compute Cohen's d effect size."""
    if len(group_a) < 2 or len(group_b) < 2:
        return 0.0
    mean_a = sum(group_a) / len(group_a)
    mean_b = sum(group_b) / len(group_b)
    var_a = sum((x - mean_a) ** 2 for x in group_a) / (len(group_a) - 1)
    var_b = sum((x - mean_b) ** 2 for x in group_b) / (len(group_b) - 1)
    pooled_std = math.sqrt((var_a + var_b) / 2)
    if pooled_std == 0:
        # Degenerate: zero variance. If means differ, return a large sentinel.
        return float("inf") if mean_a != mean_b else 0.0
    return (mean_a - mean_b) / pooled_std


def wilcoxon_test(
    values_a: list[float],
    values_b: list[float],
    agent_a_name: str = "A",
    agent_b_name: str = "B",
    metric_name: str = "score",
) -> ComparisonResult:
    """Paired Wilcoxon signed-rank test (non-parametric, paired samples).

    Use when the same tasks are run on two agents.
    """
    if len(values_a) != len(values_b):
        raise ValueError("Wilcoxon requires paired samples of equal length")

    if len(values_a) < 10:
        # Fall back to paired t-test for small samples
        result = stats.ttest_rel(values_a, values_b)
        statistic = float(result.statistic)
        p_value = float(result.pvalue)
        test_name = "paired_t_test"
    else:
        try:
            result = stats.wilcoxon(values_a, values_b, alternative="two-sided")
            statistic = float(result.statistic)
            p_value = float(result.pvalue)
            test_name = "wilcoxon"
        except ValueError:
            # All differences are zero
            statistic = 0.0
            p_value = 1.0
            test_name = "wilcoxon_degenerate"

    mean_a = sum(values_a) / len(values_a) if values_a else 0.0
    mean_b = sum(values_b) / len(values_b) if values_b else 0.0

    return ComparisonResult(
        agent_a=agent_a_name,
        agent_b=agent_b_name,
        metric_name=metric_name,
        mean_a=mean_a,
        mean_b=mean_b,
        mean_diff=mean_a - mean_b,
        statistic=statistic,
        p_value=p_value,
        significant_at_05=p_value < 0.05,
        effect_size=cohens_d(values_a, values_b),
        test_name=test_name,
    )


def friedman_test(
    results_by_agent: dict[str, list[float]], metric_name: str = "score"
) -> dict[str, Any]:
    """Friedman test: compare multiple agents across the same tasks.

    results_by_agent: {agent_name: [metric_per_task]}
    """
    agent_names = list(results_by_agent.keys())
    # Stack into matrix: n_tasks x n_agents
    matrix = [list(row) for row in zip(*results_by_agent.values())]
    statistic, p_value = stats.friedmanchisquare(*matrix)

    return {
        "test": "friedman",
        "metric": metric_name,
        "n_agents": len(agent_names),
        "n_tasks": len(matrix),
        "statistic": float(statistic),
        "p_value": float(p_value),
        "significant_at_05": p_value < 0.05,
        "agent_names": agent_names,
    }
