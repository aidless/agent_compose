"""LLM-backed ReAct agent using DeepSeek V4 Flash API.

Implements the standard ReAct loop:
1. Build prompt with task + tool descriptions + history
2. Call LLM
3. Parse tool call from response
4. Execute tool via simulator
5. Append observation to history
6. Repeat until LLM emits "finish" or max steps reached

Uses OpenAI-compatible API (DeepSeek provides /v1/chat/completions).
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests

from agent_compose.agents.base import Agent, AgentStep
from agent_compose.env.simulator import ExecutionTrace, ToolCall
from agent_compose.generator.tasks import Task
from agent_compose.tools import Tool, ToolLibrary


SYSTEM_PROMPT_REACT = """You are an AI agent that solves tasks by calling tools. You have access to the following tools:

{tool_descriptions}

To solve a task, output your reasoning and then a tool call in EXACTLY this format:

Thought: <your reasoning>
Action: <tool_name>(<arg1>=<value1>, <arg2>=<value2>, ...)
Observation: <result will be filled in by the system>

When the task is complete, output:
Thought: Task complete.
Action: finish()

Begin!"""


SYSTEM_PROMPT_FC = """You are an AI agent that solves tasks by calling tools. Respond with a JSON object in this exact format:

{{"thought": "<reasoning>", "action": "<tool_name or 'finish'>", "arguments": {{...}}}}

For 'finish', use action="finish" and arguments={{}}.

Available tools:
{tool_descriptions}"""


class DeepSeekReactAgent(Agent):
    """ReAct agent backed by DeepSeek V4 Flash (text completion style)."""

    name = "DeepSeek-ReAct"

    def __init__(
        self,
        tool_library: ToolLibrary,
        max_steps: int = 8,
        api_key: str | None = None,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.0,
    ) -> None:
        super().__init__(tool_library, max_steps)
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self._total_tokens = 0
        self._step_history: list[str] = []

    def _build_tool_descriptions(self) -> str:
        lines = []
        for tool in self.library.all_tools:
            params = tool.parameters.get("properties", {})
            param_str = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in params.items())
            lines.append(f"- {tool.name}({param_str}): {tool.description}")
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> tuple[str, int]:
        """Call DeepSeek API and return (text_response, tokens_used)."""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 1000,
        }
        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                if resp.status_code == 429 or resp.status_code >= 500:
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", 0)
                self._total_tokens += tokens
                return content, tokens
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise RuntimeError(f"DeepSeek API failed: {e!s}")
                time.sleep(2 ** attempt)
        return "", 0

    def _parse_action(self, response: str) -> tuple[str, dict[str, Any]] | None:
        """Parse 'Action: tool_name(arg1=val1, ...)' from LLM response."""
        # Find Action line
        action_match = re.search(r"Action:\s*([^\n]+)", response)
        if not action_match:
            return None
        action_text = action_match.group(1).strip()
        # Check for finish
        if action_text.startswith("finish") or action_text == "done":
            return ("__finish__", {})
        # Parse tool call: tool_name(arg1=val1, arg2=val2)
        paren_match = re.match(r"(\w+)\((.*)\)\s*$", action_text, re.DOTALL)
        if not paren_match:
            return None
        tool_name = paren_match.group(1)
        args_str = paren_match.group(2)
        # Parse args: split on commas (top-level only)
        args = self._parse_args(args_str)
        return (tool_name, args)

    def _parse_args(self, args_str: str) -> dict[str, Any]:
        """Parse 'key1=val1, key2=val2' into dict."""
        args: dict[str, Any] = {}
        if not args_str.strip():
            return args
        # Simple parser: split on ',' not inside quotes
        parts: list[str] = []
        current: list[str] = []
        depth = 0
        in_str = False
        for ch in args_str:
            if ch == '"' or ch == "'":
                in_str = not in_str
            elif not in_str:
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                elif ch == "," and depth == 0:
                    parts.append("".join(current))
                    current = []
                    continue
            current.append(ch)
        if current:
            parts.append("".join(current))

        for part in parts:
            part = part.strip()
            if "=" not in part:
                continue
            key, _, val = part.partition("=")
            key = key.strip()
            val = val.strip()
            # Strip surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            # Try to coerce
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                pass
            args[key] = val
        return args

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        # Build prompt with full history
        history_str = "\n".join(self._step_history) if self._step_history else ""
        prompt = (
            SYSTEM_PROMPT_REACT.format(tool_descriptions=self._build_tool_descriptions())
            + f"\n\nTask: {task.natural_language}"
            + (f"\n\nHistory:\n{history_str}" if history_str else "")
            + "\n\nThought:"
        )

        try:
            response, _ = self._call_llm(prompt)
        except RuntimeError as e:
            return AgentStep(thought=f"API error: {e}", action=None)

        # Append LLM response to history
        self._step_history.append(f"Thought: {response.strip()}")

        parsed = self._parse_action(response)
        if parsed is None:
            # Could not parse - try to finish or continue
            if "finish" in response.lower() or "done" in response.lower():
                return AgentStep(thought="LLM signaled finish.", action=None)
            return AgentStep(
                thought=response,
                action=None,  # malformed action, end
            )

        tool_name, args = parsed
        if tool_name == "__finish__":
            return AgentStep(thought="LLM signaled finish.", action=None)

        call = ToolCall(
            tool_name=tool_name,
            arguments=args,
            call_id=f"{task.task_id}_llm_s{len(trace.calls)}",
        )
        return AgentStep(thought=response, action=call)

    def observe(self, call: ToolCall, result_success: bool, result_output: Any) -> None:
        """Record the observation in history (called by runner after execution)."""
        obs = f"Observation: success={result_success}, output={json.dumps(result_output)[:300]}"
        self._step_history.append(obs)

    def reset(self) -> None:
        self._step_history = []
        self._total_tokens = 0


class DeepSeekFCAgent(DeepSeekReactAgent):
    """Native function-calling variant: uses JSON output instead of text parsing."""

    name = "DeepSeek-FC"

    def act(self, task: Task, trace: ExecutionTrace) -> AgentStep:
        history_str = "\n".join(self._step_history) if self._step_history else ""
        prompt = (
            SYSTEM_PROMPT_FC.format(tool_descriptions=self._build_tool_descriptions())
            + f"\n\nTask: {task.natural_language}"
            + (f"\n\nPrevious steps:\n{history_str}" if history_str else "")
            + '\n\nRespond with JSON: {"thought": "...", "action": "...", "arguments": {...}}'
        )

        try:
            response, _ = self._call_llm(prompt)
        except RuntimeError as e:
            return AgentStep(thought=f"API error: {e}", action=None)

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            return AgentStep(thought=f"Could not parse JSON: {response[:200]}", action=None)

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return AgentStep(thought=f"Invalid JSON: {response[:200]}", action=None)

        action = data.get("action", "finish")
        if action == "finish":
            return AgentStep(thought=data.get("thought", "Done."), action=None)

        args = data.get("arguments", {})
        call = ToolCall(
            tool_name=action,
            arguments=args,
            call_id=f"{task.task_id}_llmfc_s{len(trace.calls)}",
        )
        thought = data.get("thought", "")
        self._step_history.append(f"Step {len(trace.calls) + 1}: {action}({args})")
        return AgentStep(thought=thought, action=call)

    def observe(self, call: ToolCall, result_success: bool, result_output: Any) -> None:
        obs = f"Observation: success={result_success}, output={json.dumps(result_output)[:300]}"
        self._step_history.append(obs)
