"""Agent interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agent_compose.env.simulator import ExecutionTrace, ToolCall, ToolResult
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


@dataclass
class AgentStep:
    """One step of an agent's reasoning loop."""

    thought: str = ""
    action: ToolCall | None = None
    observation: ToolResult | None = None


@dataclass
class AgentRunResult:
    """Final result of running an agent on a task."""

    task_id: str
    trace: ExecutionTrace
    steps: list[AgentStep] = field(default_factory=list)
    total_tokens_used: int = 0
    wall_time_seconds: float = 0.0


class Agent(ABC):
    """Abstract base class for all agents."""

    name: str = "BaseAgent"

    def __init__(self, tool_library: ToolLibrary, max_steps: int = 8) -> None:
        self.library = tool_library
        self.max_steps = max_steps

    @abstractmethod
    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        """Produce next step (thought + action) given task and history.

        Implementations should NOT execute the action - the runner does that.
        Returning action=None signals task completion.
        """
        ...

    def describe_tools(self) -> str:
        """Human-readable tool descriptions for prompt construction."""
        lines = []
        for tool in self.library.all_tools:
            lines.append(f"- {tool.name}: {tool.description}")
            if tool.parameters.get("properties"):
                params = ", ".join(tool.parameters["properties"].keys())
                lines.append(f"  parameters: {params}")
        return "\n".join(lines)
