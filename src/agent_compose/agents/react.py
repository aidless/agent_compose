"""ReAct agent: Reasoning + Acting in an interleaved loop.

This is a simplified rule-based ReAct that uses templates rather than an LLM,
so it can run without API keys. It demonstrates the baseline reasoning pattern
and serves as a sanity check for the simulator + evaluation pipeline.

For real ReAct with an LLM, see `agents/react_llm.py` (TODO).
"""

from __future__ import annotations

from typing import Any

from agent_compose.agents.base import Agent, AgentStep
from agent_compose.env.simulator import ExecutionTrace, ToolCall
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


class ReActAgent(Agent):
    """Template-based ReAct for offline testing.

    Strategy:
    1. Parse task natural language to identify required tools (heuristic)
    2. Walk the expected_chain tools in order, filling args from context
    3. Return "finish" action when done

    This is NOT a real LLM agent - it uses task.expected_chain as a hint,
    demonstrating the protocol but not the difficulty. For meaningful
    composition generalization evaluation, use an LLM-based agent.
    """

    name = "ReAct-template"

    def __init__(
        self,
        tool_library: ToolLibrary,
        max_steps: int = 8,
        use_oracle: bool = False,
        use_generic_inference: bool = False,
    ) -> None:
        super().__init__(tool_library, max_steps)
        self.use_generic_inference = use_generic_inference
        self.use_oracle = use_oracle
        # If use_oracle=True, agent sees the expected chain (ceiling performance)
        # If use_oracle=False, agent must infer tools from natural language only

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        step_num = len(trace.calls)

        if self.use_oracle:
            # Oracle mode: follow expected_chain exactly
            if step_num >= len(task.expected_chain):
                return AgentStep(thought="Task complete.", action=None)
            next_tool = task.expected_chain[step_num]
        else:
            # Heuristic mode: pick tools from natural language keywords
            next_tool = self._infer_next_tool(task, trace)

        if next_tool is None:
            return AgentStep(thought="Cannot determine next tool. Stopping.", action=None)

        # Build arguments from task parameters + previous results
        args = self._build_arguments(next_tool, task, trace)
        call = ToolCall(tool_name=next_tool, arguments=args, call_id=f"{task.task_id}_s{step_num}")
        thought = f"Step {step_num}: Call {next_tool} with {args}"
        return AgentStep(thought=thought, action=call)

    def _infer_next_tool(self, task: Task, trace: ExecutionTrace) -> str | None:
        """Heuristic: match natural language to tool names."""
        called = {c.tool_name for c in trace.calls}
        nl = task.natural_language.lower()

        if self.use_generic_inference:
            from agent_compose.agents.inference import infer_tool_generic

            return infer_tool_generic(self.library, task.natural_language, called)

        # Simple keyword matching
        keywords = {
            "search_web": ["search", "look up", "find", "query"],
            "fetch_url": ["fetch", "url", "page"],
            "calculator": ["calculate", "compute", "sum", "average", "multiply"],
            "unit_convert": ["convert", "translate", "exchange"],
            "send_email": ["email", "send to"],
            "send_sms": ["sms", "text message", "phone"],
            "read_file": ["read", "open file", "load file"],
            "write_file": ["write", "save", "store"],
            "get_datetime": ["date", "time", "current time", "now"],
            "calendar_add": ["calendar", "schedule", "add event", "reminder"],
        }

        # Score each uncalled tool
        scores: dict[str, int] = {}
        for tool, kws in keywords.items():
            if tool in called:
                continue
            scores[tool] = sum(1 for kw in kws if kw in nl)

        if not scores:
            if self.use_generic_inference:
                from agent_compose.agents.inference import infer_tool_generic

                return infer_tool_generic(self.library, task.natural_language, called)
            return None
        return max(scores, key=scores.get)

    def _build_arguments(self, tool: str, task: Task, trace: ExecutionTrace) -> dict[str, Any]:
        """Build arguments for a tool call from task params and prior results."""
        if self.use_generic_inference:
            from agent_compose.agents.inference import build_args_generic

            return build_args_generic(self.library, tool, task, trace)
        params = task.parameters

        if tool == "search_web":
            return {"query": params.get("location", params.get("query1", "unknown"))}
        if tool == "fetch_url":
            return {"url": params.get("url", "https://example.com")}
        if tool == "calculator":
            return {"expression": "(100 + 200) / 2"}
        if tool == "unit_convert":
            return {
                "value": 100,
                "from_unit": "USD",
                "to_unit": params.get("target_currency", "EUR"),
            }
        if tool == "send_email":
            return {
                "to": params.get("recipient_email", "test@example.com"),
                "subject": "Report",
                "body": "Body content",
            }
        if tool == "send_sms":
            return {
                "phone": params.get("phone_number", "+10000000000"),
                "message": "Alert message",
            }
        if tool == "read_file":
            return {"path": params.get("input_file", "/data/file.csv")}
        if tool == "write_file":
            return {
                "path": params.get("output_file", "/tmp/output.txt"),
                "content": "Result content",
            }
        if tool == "get_datetime":
            return {"timezone": params.get("source_timezone", "UTC")}
        if tool == "calendar_add":
            return {
                "title": "Event",
                "start_time": params.get(
                    "date", params.get("meeting_time", "2026-08-01T10:00:00Z")
                ),
                "duration_minutes": 60,
            }
        return {}
