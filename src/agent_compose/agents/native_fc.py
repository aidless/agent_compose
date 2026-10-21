"""Native Function Calling agent: simulates GPT-4 / Claude structured output.

This is a simulation that:
- Constructs a structured "tool call" decision based on heuristics
- Outputs in the same JSON format as OpenAI/Anthropic function calling
- Allows testing the eval pipeline without API keys

For real native FC, integrate with openai>=1.0 or anthropic>=0.18.
"""

from __future__ import annotations

import json
from typing import Any

from agent_compose.agents.base import Agent, AgentStep
from agent_compose.env.simulator import ExecutionTrace, ToolCall
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


class NativeFCAgent(Agent):
    """Simulated native function-calling agent.

    Like ReAct template, this uses heuristics. In a real setup, replace the
    `_decide_next_call` method with an actual LLM call.
    """

    name = "NativeFC-template"

    def __init__(
        self,
        tool_library: ToolLibrary,
        max_steps: int = 8,
        use_oracle: bool = False,
        use_generic_inference: bool = False,
    ) -> None:
        super().__init__(tool_library, max_steps)
        self.use_oracle = use_oracle
        self.use_generic_inference = use_generic_inference

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        step_num = len(trace.calls)

        if self.use_oracle and step_num < len(task.expected_chain):
            next_tool = task.expected_chain[step_num]
        else:
            next_tool = self._decide_tool(task, trace)

        if next_tool is None or step_num >= self.max_steps:
            return AgentStep(thought="Stopping.", action=None)

        args = self._build_args(next_tool, task, trace)
        # Structured output mimics OpenAI FC format
        structured = {
            "tool": next_tool,
            "arguments": args,
        }
        call = ToolCall(
            tool_name=next_tool,
            arguments=args,
            call_id=f"{task.task_id}_fc_s{step_num}",
        )
        return AgentStep(
            thought=f"Selected {next_tool} via native FC. Structured: {json.dumps(structured)}",
            action=call,
        )

    def _decide_tool(self, task: Task, trace: ExecutionTrace) -> str | None:
        """Heuristic tool selection based on natural language + call history."""
        called = [c.tool_name for c in trace.calls]
        nl = task.natural_language.lower()

        if self.use_generic_inference:
            from agent_compose.agents.inference import infer_tool_generic
            return infer_tool_generic(self.library, task.natural_language, called)

        # Priority tool patterns
        patterns = [
            (["weather", "temperature"], "search_web"),
            (["stock", "price", "ticker"], "search_web"),
            (["email", "send to"], "send_email"),
            (["text", "sms", "phone"], "send_sms"),
            (["convert", "exchange", "usd", "eur"], "unit_convert"),
            (["calculate", "compute", "sum", "average"], "calculator"),
            (["read", "load file"], "read_file"),
            (["write", "save", "report"], "write_file"),
            (["calendar", "schedule", "event"], "calendar_add"),
            (["time", "date", "today"], "get_datetime"),
            (["url", "fetch", "page"], "fetch_url"),
        ]

        # Skip tools already called
        for keywords, tool in patterns:
            if tool in called:
                continue
            if any(kw in nl for kw in keywords):
                return tool

        if self.use_generic_inference:
            from agent_compose.agents.inference import infer_tool_generic
            return infer_tool_generic(self.library, task.natural_language, called)

        return None

    def _build_args(self, tool: str, task: Task, trace: ExecutionTrace) -> dict[str, Any]:
        """Build args from task params + prior results (with proper binding)."""
        if self.use_generic_inference:
            from agent_compose.agents.inference import build_args_generic
            return build_args_generic(self.library, tool, task, trace)
        params = task.parameters

        # Mimic real FC by binding previous outputs
        last_output = None
        if trace.results:
            last_output = trace.results[-1].output

        if tool == "search_web":
            query = params.get("location", params.get("query1", params.get("stock_ticker", "info")))
            return {"query": query, "max_results": 3}
        if tool == "search_news":
            return {"headline_query": params.get("query1", "news"), "max_articles": 3}
        if tool == "search_academic":
            return {"research_query": params.get("query1", "research"), "top_k": 3}
        if tool == "fetch_url":
            return {"url": params.get("url", "https://example.com")}
        if tool == "calculator":
            # Try to use values from prior read_file
            if isinstance(last_output, str) and "," in last_output:
                nums = [float(x) for x in last_output.replace("\n", ",").split(",") if x.strip()]
                if nums:
                    return {"expression": str(sum(nums))}
            return {"expression": "100"}
        if tool == "unit_convert":
            return {
                "value": 100,
                "from_unit": "USD",
                "to_unit": params.get("target_currency", "EUR"),
            }
        if tool == "send_email":
            body = self._compose_email_body(params, last_output)
            return {
                "to": params.get("recipient_email", "test@example.com"),
                "subject": f"Report for {params.get('location', 'task')}",
                "body": body,
            }
        if tool == "send_sms":
            return {
                "phone": params.get("phone_number", "+10000000000"),
                "message": f"Alert: 100",
            }
        if tool == "read_file":
            return {"path": params.get("input_file", "/data/numbers_a.csv")}
        if tool == "write_file":
            content = str(last_output) if last_output is not None else "result"
            return {"path": params.get("output_file", "/tmp/result.txt"), "content": content}
        if tool == "get_datetime":
            return {"timezone": params.get("source_timezone", "UTC")}
        if tool == "calendar_add":
            return {
                "title": "Reminder",
                "start_time": params.get("date", "2026-08-01T10:00:00Z"),
                "duration_minutes": 60,
            }
        return {}

    def _compose_email_body(self, params: dict[str, Any], last_output: Any) -> str:
        """Try to use the previous tool's output as email body."""
        if last_output is None:
            return "Report attached."
        if isinstance(last_output, list) and last_output:
            return f"Search results: {len(last_output)} items found. First: {last_output[0]}"
        if isinstance(last_output, (int, float)):
            return f"Computed value: {last_output}"
        return str(last_output)[:500]
