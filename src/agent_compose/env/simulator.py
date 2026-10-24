"""Deterministic JSON API simulator for tool calls.

The simulator never touches the network or the filesystem. Every side effect is
recorded in ``state`` so the evaluation runner can inspect it after a task, and
failures are drawn deterministically from ``call_id`` + ``seed`` so a rerun with
the same arguments reproduces the same trace.
"""

from __future__ import annotations

import ast
import hashlib
import operator
from dataclasses import dataclass, field
from typing import Any

from agent_compose.tools import Tool, ToolLibrary

_USD_PER_UNIT = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "CNY": 0.14,
    "INR": 0.012,
}
_METRES_PER_UNIT = {
    "M": 1.0,
    "KM": 1000.0,
    "CM": 0.01,
    "MM": 0.001,
    "MI": 1609.344,
    "FT": 0.3048,
    "IN": 0.0254,
    "YD": 0.9144,
}
_GRAMS_PER_UNIT = {
    "KG": 1000.0,
    "G": 1.0,
    "LB": 453.59237,
    "OZ": 28.349523125,
    "T": 1_000_000.0,
}
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


@dataclass
class ToolCall:
    """One requested tool invocation."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""


@dataclass
class ToolResult:
    """Outcome of executing one ToolCall."""

    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str = ""
    failed_injected: bool = False


@dataclass
class ExecutionTrace:
    """Everything an agent did on one task."""

    task_id: str
    calls: list[ToolCall] = field(default_factory=list)
    results: list[ToolResult] = field(default_factory=list)
    termination_reason: str = ""
    success: bool = False
    final_state: dict[str, Any] = field(default_factory=dict)


class ToolSimulator:
    """Execute tool calls against an in-memory mock environment."""

    def __init__(
        self,
        library: ToolLibrary,
        failure_rate: float = 0.0,
        seed: int = 42,
    ) -> None:
        if not 0.0 <= failure_rate <= 1.0:
            raise ValueError("failure_rate must be in [0, 1]")
        self.library = library
        self.failure_rate = failure_rate
        self.seed = seed
        self.state: dict[str, Any] = {}
        self.reset_state()

    def reset_state(self) -> None:
        """Clear every recorded side effect."""
        self.state = {
            "sent_emails": [],
            "sent_sms": [],
            "sent_messages": [],
            "written_files": {},
            "deleted_files": [],
            "calendar_events": [],
        }

    def execute(self, call: ToolCall) -> ToolResult:
        """Run one call and record its result."""
        try:
            tool = self.library.get(call.tool_name)
        except KeyError:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"Unknown tool: {call.tool_name}",
            )
        if self._should_fail(call.call_id):
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error="Injected failure",
                failed_injected=True,
            )
        try:
            output = self._dispatch(tool, call.arguments or {})
        except Exception as exc:  # noqa: BLE001 - tool errors are reported as results, not raised
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            success=True,
            output=output,
        )

    def _should_fail(self, call_id: str) -> bool:
        if self.failure_rate <= 0.0:
            return False
        digest = hashlib.sha256(f"{self.seed}:{call_id}".encode()).digest()
        return int.from_bytes(digest[:8], "big") / 2**64 < self.failure_rate

    def _dispatch(self, tool: Tool, args: dict[str, Any]) -> Any:
        name = tool.name
        if name == "calculator":
            return self._calculate(args)
        if name == "unit_convert":
            return self._convert(args)
        if name == "read_file":
            return self._read_file(args)
        if name == "write_file":
            return self._write_file(args)
        if name == "append_file":
            return self._append_file(args)
        if name == "delete_file":
            return self._delete_file(args)
        if name == "list_files":
            return sorted(self.state["written_files"]) or ["/data/numbers_a.csv"]
        if name == "send_email":
            return self._record_message("sent_emails", args, "email")
        if name == "send_sms":
            return self._record_message("sent_sms", args, "sms")
        if name in {"send_push", "send_slack"}:
            return self._record_message("sent_messages", args, name)
        if name == "calendar_add":
            return self._calendar_add(args)
        if name == "calendar_list":
            return list(self.state["calendar_events"])
        if name == "get_datetime":
            return {
                "datetime": "2026-07-23T20:15:00+09:00",
                "timezone": "Asia/Tokyo",
                "weekday": "Wednesday",
            }
        if tool.example_output is not None:
            return tool.example_output
        return {"status": "ok"}

    def _calculate(self, args: dict[str, Any]) -> float:
        expression = str(args.get("expression", "")).strip()
        if not expression:
            raise ValueError("calculator requires a non-empty expression")
        tree = ast.parse(expression, mode="eval")
        return float(self._eval_node(tree.body))

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            return _BIN_OPS[type(node.op)](self._eval_node(node.left), self._eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](self._eval_node(node.operand))
        raise ValueError(f"unsupported expression element: {type(node).__name__}")

    def _convert(self, args: dict[str, Any]) -> float:
        value = float(args["value"])
        src = str(args.get("from_unit", "")).upper()
        dst = str(args.get("to_unit", "")).upper()
        if src == dst:
            return value
        for table in (_USD_PER_UNIT, _METRES_PER_UNIT, _GRAMS_PER_UNIT):
            if src in table and dst in table:
                return round(value * table[src] / table[dst], 4)
        if src in {"C", "F", "K"} and dst in {"C", "F", "K"}:
            return round(self._convert_temperature(value, src, dst), 4)
        raise ValueError(f"unsupported unit conversion: {src} -> {dst}")

    @staticmethod
    def _convert_temperature(value: float, src: str, dst: str) -> float:
        celsius = {
            "C": value,
            "F": (value - 32.0) * 5.0 / 9.0,
            "K": value - 273.15,
        }[src]
        return {
            "C": celsius,
            "F": celsius * 9.0 / 5.0 + 32.0,
            "K": celsius + 273.15,
        }[dst]

    def _read_file(self, args: dict[str, Any]) -> str:
        path = str(args.get("path", ""))
        if path.endswith(".csv"):
            return "10,20\n30,40\n"
        if path.endswith(".json"):
            return '{"items": [10, 20, 30]}'
        return "name,value\nalice,42\nbob,17\n"

    def _write_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = str(args["path"])
        content = str(args.get("content", ""))
        self.state["written_files"][path] = content
        return {"status": "written", "path": path, "bytes": len(content)}

    def _append_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = str(args["path"])
        content = str(args.get("content", ""))
        previous = self.state["written_files"].get(path, "")
        self.state["written_files"][path] = previous + content
        return {"status": "appended", "path": path, "bytes": len(content)}

    def _delete_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = str(args["path"])
        self.state["written_files"].pop(path, None)
        self.state["deleted_files"].append(path)
        return {"status": "deleted", "path": path}

    def _record_message(self, table: str, args: dict[str, Any], kind: str) -> dict[str, Any]:
        message_id = f"{kind}_{len(self.state[table]) + 1:04d}"
        self.state[table].append(
            {
                "message_id": message_id,
                "to": args.get("to", ""),
                "subject": args.get("subject", ""),
                "body": args.get("body", args.get("message", "")),
            }
        )
        return {"status": "sent", "message_id": message_id}

    def _calendar_add(self, args: dict[str, Any]) -> dict[str, Any]:
        event_id = f"evt_{len(self.state['calendar_events']) + 1:04d}"
        event = {
            "event_id": event_id,
            "title": args.get("title", args.get("summary", "")),
            "start": args.get("start", args.get("start_time", "")),
            "end": args.get("end", args.get("end_time", "")),
        }
        self.state["calendar_events"].append(event)
        return {"status": "added", **event}
