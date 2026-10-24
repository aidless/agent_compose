"""Reflexion agent: ReAct + verbal self-reflection on failure.

Implementation:
1. Try to solve the task with ReAct-style reasoning
2. If a tool call fails, reflect on WHY it failed and produce a different next action
3. Keep a memory of reflections to avoid repeating the same mistake

For the heuristic version: detect failure types (unknown tool, missing param,
wrong chain order) and emit a templated reflection.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_compose.agents.base import Agent, AgentStep
from agent_compose.agents.react import ReActAgent
from agent_compose.env.simulator import ExecutionTrace, ToolCall
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


@dataclass
class Reflection:
    """A self-reflection memory entry."""

    failure_pattern: str  # e.g., "unknown_tool", "wrong_order"
    insight: str
    suggested_fix: str


class ReflexionAgent(Agent):
    """ReAct + verbal reflection on failures."""

    name = "Reflexion-template"

    def __init__(
        self,
        tool_library: ToolLibrary,
        max_steps: int = 8,
        max_reflections: int = 3,
        use_oracle: bool = False,
        use_generic_inference: bool = False,
    ) -> None:
        super().__init__(tool_library, max_steps)
        self.inner_agent = ReActAgent(
            tool_library,
            max_steps,
            use_oracle=use_oracle,
            use_generic_inference=use_generic_inference,
        )
        self.max_reflections = max_reflections
        self.reflections: list[Reflection] = []

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        # Inspect the last result for failure
        if trace.results:
            last_result = trace.results[-1]
            if not last_result.success:
                reflection = self._reflect_on_failure(last_result, trace)
                if reflection is not None and len(self.reflections) < self.max_reflections:
                    self.reflections.append(reflection)
                    # Produce an alternative action based on the reflection
                    alt = self._alternative_action(task, trace, reflection)
                    if alt is not None:
                        return AgentStep(
                            thought=f"Reflection: {reflection.insight} → trying {alt.tool_name}",
                            action=alt,
                        )
        # Fall back to inner ReAct agent
        return self.inner_agent.act(task, trace)

    def _reflect_on_failure(self, result, trace: ExecutionTrace) -> Reflection | None:
        """Generate a reflection based on failure mode."""
        if "Unknown tool" in (result.error or ""):
            return Reflection(
                failure_pattern="unknown_tool",
                insight="I called a tool that doesn't exist. I should only use tools in the library.",
                suggested_fix="check_tool_name",
            )
        if "network" in (result.error or "") or "rate" in (result.error or ""):
            return Reflection(
                failure_pattern="transient",
                insight="Tool failed transiently. Retry the same tool.",
                suggested_fix="retry",
            )
        if "syntax" in (result.error or "") or "Invalid" in (result.error or ""):
            return Reflection(
                failure_pattern="bad_args",
                insight="My arguments were malformed. I need to fix them.",
                suggested_fix="fix_args",
            )
        # Detect order error: called send_email before getting data
        if trace.calls and trace.calls[-1].tool_name == "send_email":
            return Reflection(
                failure_pattern="premature_action",
                insight="I sent email too early. I should fetch data first.",
                suggested_fix="reorder",
            )
        return None

    def _alternative_action(
        self, task: Task, trace: ExecutionTrace, reflection: Reflection
    ) -> ToolCall | None:
        """Produce an alternative tool call based on the reflection."""
        if reflection.suggested_fix == "retry":
            last_call = trace.calls[-1]
            return ToolCall(
                tool_name=last_call.tool_name,
                arguments=last_call.arguments,
                call_id=f"{task.task_id}_retry",
            )
        if reflection.suggested_fix == "reorder":
            # If we prematurely sent email, try fetching data first
            called = {c.tool_name for c in trace.calls}
            if "search_web" not in called:
                return ToolCall(
                    tool_name="search_web",
                    arguments={"query": task.parameters.get("location", "info")},
                    call_id=f"{task.task_id}_r",
                )
        if reflection.suggested_fix == "check_tool_name":
            # Replace unknown tool with a valid one
            last_call = trace.calls[-1]
            replacement = self._suggest_replacement(last_call.tool_name)
            if replacement:
                return ToolCall(
                    tool_name=replacement,
                    arguments=last_call.arguments,
                    call_id=f"{task.task_id}_fix",
                )
        return None

    def _suggest_replacement(self, bad_tool: str) -> str | None:
        """Map a hallucinated/typo'd tool name to a valid one."""
        mapping = {
            "search": "search_web",
            "email": "send_email",
            "calc": "calculator",
            "calculate": "calculator",
            "convert": "unit_convert",
            "datetime": "get_datetime",
            "calendar": "calendar_add",
            "read": "read_file",
            "write": "write_file",
        }
        return mapping.get(bad_tool)

    def reset(self) -> None:
        self.reflections = []
