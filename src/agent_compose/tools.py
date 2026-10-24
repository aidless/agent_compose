"""Tool schema loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class Tool(BaseModel):
    """A single tool definition."""

    name: str
    domain: str
    description: str
    parameters: dict[str, Any]
    # Pydantic evaluates these annotations at runtime, and `X | Y` raises on 3.9.
    returns: Union[dict[str, Any], str]  # noqa: UP007
    side_effects: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    example_call: Optional[dict[str, Any]] = None  # noqa: UP045
    example_output: Any = None


class ToolLibrary:
    """Loader for the tool library on disk."""

    def __init__(self, tools_dir: Path) -> None:
        self.tools_dir = tools_dir
        self._tools: dict[str, Tool] = {}
        self._equivalence: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load all tool JSON files from disk."""
        for json_file in sorted(self.tools_dir.glob("*.json")):
            if json_file.name.startswith("_"):
                # Load metadata files
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if "equivalence_groups" in data:
                    self._equivalence = data
                continue
            data = json.loads(json_file.read_text(encoding="utf-8"))
            tool = Tool(**data)
            self._tools[tool.name] = tool

    @property
    def all_tools(self) -> list[Tool]:
        """Return all loaded tools."""
        return list(self._tools.values())

    def get(self, name: str) -> Tool:
        """Get a tool by name. Raises KeyError if not found."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not in library. Available: {list(self._tools.keys())}")
        return self._tools[name]

    def by_domain(self, domain: str) -> list[Tool]:
        """Get all tools in a domain."""
        return [t for t in self._tools.values() if t.domain == domain]

    @property
    def equivalence_groups(self) -> list[dict[str, Any]]:
        """Return tool equivalence groups for substitutability testing."""
        return self._equivalence.get("equivalence_groups", [])

    def is_equivalent(self, tool_a: str, tool_b: str) -> bool:
        """Check if two tools are functionally equivalent."""
        for group in self.equivalence_groups:
            members = {group["canonical"], *group.get("variants", [])}
            if tool_a in members and tool_b in members:
                return True
        return False

    def variant_of(self, canonical: str) -> list[str]:
        """Get all variants of a canonical tool."""
        for group in self.equivalence_groups:
            if group["canonical"] == canonical:
                return group.get("variants", [])
        return []
