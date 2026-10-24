"""Tests for additional agents (Reflexion, PlanExecute)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_compose.agents.plan_execute import PlanExecuteAgent
from agent_compose.agents.reflexion import ReflexionAgent
from agent_compose.env.simulator import ExecutionTrace, ToolCall, ToolResult, ToolSimulator
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


@pytest.fixture
def tool_lib() -> ToolLibrary:
    return ToolLibrary(Path(__file__).parent.parent / "tools")


@pytest.fixture
def simulator(tool_lib: ToolLibrary) -> ToolSimulator:
    return ToolSimulator(tool_lib, failure_rate=0.0, seed=42)


def make_task(chain: list[str]) -> Task:
    return Task(
        task_id="t1",
        template_id="T1",
        natural_language="Look up weather in Tokyo and email alice@example.com.",
        expected_chain=chain,
        parameters={"location": "Tokyo", "recipient_email": "alice@example.com"},
        success_criteria=["email sent"],
        split="test",
    )


def test_reflexion_creates_reflection(tool_lib: ToolLibrary, simulator: ToolSimulator) -> None:
    agent = ReflexionAgent(tool_lib, max_steps=5)
    task = make_task(["search_web", "send_email"])
    trace = ExecutionTrace(task_id="t1")
    # Simulate a failed call
    trace.calls.append(ToolCall(tool_name="bad_tool", arguments={}, call_id="c1"))
    trace.results.append(
        ToolResult(
            call_id="c1", tool_name="bad_tool", success=False, error="Unknown tool: bad_tool"
        )
    )
    step = agent.act(task, trace)
    assert step.action is not None
    assert "search_web" == step.action.tool_name or "retry" in (step.thought or "").lower()


def test_reflexion_resets(tool_lib: ToolLibrary) -> None:
    agent = ReflexionAgent(tool_lib)
    agent.reflections.append("test")
    agent.reset()
    assert agent.reflections == []


def test_plan_execute_makes_plan(tool_lib: ToolLibrary, simulator: ToolSimulator) -> None:
    agent = PlanExecuteAgent(tool_lib, max_steps=5)
    task = make_task(["search_web", "send_email"])
    trace = ExecutionTrace(task_id="t1")
    step = agent.act(task, trace)
    assert step.action is not None
    assert step.action.tool_name in {"search_web", "send_email"}


def test_plan_execute_follows_oracle(tool_lib: ToolLibrary) -> None:
    agent = PlanExecuteAgent(tool_lib, max_steps=5, use_oracle=True)
    task = make_task(["read_file", "calculator", "write_file"])
    trace = ExecutionTrace(task_id="t1")
    steps = []
    for _ in range(5):
        step = agent.act(task, trace)
        if step.action is None:
            break
        steps.append(step.action.tool_name)
        # Mark as executed
        trace.calls.append(step.action)
        trace.results.append(
            ToolResult(call_id=step.action.call_id, tool_name=step.action.tool_name, success=True)
        )
    assert steps == ["read_file", "calculator", "write_file"]


def test_plan_execute_resets(tool_lib: ToolLibrary) -> None:
    agent = PlanExecuteAgent(tool_lib)
    agent._planned = True
    agent._plan = ["a", "b"]
    agent.reset()
    assert agent._plan == []
    assert not agent._planned
