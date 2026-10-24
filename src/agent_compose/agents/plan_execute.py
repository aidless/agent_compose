"""Plan-and-Execute agent: first generates a full plan, then executes step-by-step.

Strategy:
1. Plan phase: enumerate all tools that might be needed (based on task + library)
2. Order phase: arrange tools into a plausible chain
3. Execute phase: call each tool with sensible arguments

Compared to ReAct:
- ReAct: interleaves reasoning with action (online decisions)
- Plan-Execute: commits to a plan upfront, executes mechanically (offline decisions)
"""

from __future__ import annotations

from typing import Any

from agent_compose.agents.base import Agent, AgentStep
from agent_compose.env.simulator import ExecutionTrace, ToolCall
from agent_compose.generator.tasks import Task
from agent_compose.tools import ToolLibrary


class PlanExecuteAgent(Agent):
    """Plan-then-execute agent with template-based planning."""

    name = "PlanExecute-template"

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
        self._plan: list[str] = []
        self._planned = False

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        # Plan once on first step
        if not self._planned:
            self._plan = self._make_plan(task)
            self._planned = True

        step_num = len(trace.calls)
        if step_num >= len(self._plan):
            return AgentStep(thought="Plan complete.", action=None)

        next_tool = self._plan[step_num]
        args = self._build_args(next_tool, task, trace)
        call = ToolCall(
            tool_name=next_tool,
            arguments=args,
            call_id=f"{task.task_id}_plan_s{step_num}",
        )
        return AgentStep(
            thought=f"Executing plan step {step_num + 1}/{len(self._plan)}: {next_tool}",
            action=call,
        )

    def _make_plan(self, task: Task) -> list[str]:
        """Generate a tool plan from natural language keywords."""
        if self.use_oracle:
            return list(task.expected_chain)

        nl = task.natural_language.lower()
        plan: list[str] = []

        if self.use_generic_inference:
            from agent_compose.agents.inference import infer_tool_generic

            first = infer_tool_generic(self.library, task.natural_language, [])
            if first:
                plan.append(first)
            second = infer_tool_generic(self.library, task.natural_language, plan)
            if second and second not in plan:
                plan.append(second)
            return plan

        # Common workflow patterns
        if any(kw in nl for kw in ["weather", "temperature", "forecast"]):
            plan.append("search_web")
        if any(kw in nl for kw in ["stock", "price", "ticker"]):
            plan.append("search_web")
        if "convert" in nl or "usd" in nl or "eur" in nl:
            plan.append("unit_convert")
        if "calculate" in nl or "compute" in nl or "sum" in nl or "average" in nl:
            plan.append("calculator")
        if "fetch" in nl or "url" in nl:
            plan.append("fetch_url")
        if "read" in nl and "file" in nl:
            plan.append("read_file")
        if "write" in nl or "save" in nl or "report" in nl:
            plan.append("write_file")
        if "email" in nl or "send to" in nl:
            plan.append("send_email")
        if "sms" in nl or "text" in nl or "phone" in nl:
            plan.append("send_sms")
        if "calendar" in nl or "schedule" in nl or "reminder" in nl:
            plan.append("calendar_add")
        if "time" in nl or "today" in nl:
            plan.append("get_datetime")

        if not plan:
            plan.append("search_web")  # default fallback

        if self.use_generic_inference:
            from agent_compose.agents.inference import infer_tool_generic

            generic = infer_tool_generic(self.library, task.natural_language, [])
            if generic and generic not in plan:
                plan.insert(0, generic)
            second = infer_tool_generic(self.library, task.natural_language, plan)
            if second and second not in plan:
                plan.append(second)
            if plan == ["search_web"]:
                plan = []

        return plan

    def _build_args(self, tool: str, task: Task, trace: ExecutionTrace) -> dict[str, Any]:
        """Same heuristic argument construction as ReAct."""
        if self.use_generic_inference:
            from agent_compose.agents.inference import build_args_generic

            return build_args_generic(self.library, tool, task, trace)
        params = task.parameters
        last_output = trace.results[-1].output if trace.results else None

        if tool == "search_web":
            q = params.get("location", params.get("query1", params.get("stock_ticker", "info")))
            return {"query": q, "max_results": 3}
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
            body = str(last_output)[:200] if last_output else "Report attached."
            return {
                "to": params.get("recipient_email", "test@example.com"),
                "subject": "Report",
                "body": body,
            }
        if tool == "send_sms":
            return {
                "phone": params.get("phone_number", "+10000000000"),
                "message": f"Alert: {last_output if last_output else '100'}",
            }
        if tool == "read_file":
            return {"path": params.get("input_file", "/data/file.csv")}
        if tool == "write_file":
            return {
                "path": params.get("output_file", "/tmp/result.txt"),
                "content": str(last_output) if last_output else "result",
            }
        if tool == "get_datetime":
            return {"timezone": params.get("source_timezone", "UTC")}
        if tool == "calendar_add":
            return {
                "title": "Reminder",
                "start_time": params.get("date", "2026-08-01T10:00:00Z"),
                "duration_minutes": 60,
            }
        return {}

    def reset(self) -> None:
        self._plan = []
        self._planned = False
