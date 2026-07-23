"""Tests for tool library loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_compose.tools import ToolLibrary


@pytest.fixture
def tool_lib() -> ToolLibrary:
    """Load tool library from the project's tools/ directory."""
    project_root = Path(__file__).parent.parent
    tools_dir = project_root / "tools"
    return ToolLibrary(tools_dir)


def test_library_loads_all_tools(tool_lib: ToolLibrary) -> None:
    """Verify all 10+ tools load successfully."""
    tools = tool_lib.all_tools
    assert len(tools) >= 10, f"Expected >=10 tools, got {len(tools)}"
    expected = {
        "search_web",
        "fetch_url",
        "calculator",
        "unit_convert",
        "send_email",
        "send_sms",
        "read_file",
        "write_file",
        "get_datetime",
        "calendar_add",
    }
    actual = {t.name for t in tools}
    assert expected.issubset(actual), f"Missing tools: {expected - actual}"


def test_tool_has_required_fields(tool_lib: ToolLibrary) -> None:
    """Every tool must have name, domain, description, parameters, returns."""
    for tool in tool_lib.all_tools:
        assert tool.name
        assert tool.domain
        assert tool.description
        assert tool.parameters
        assert tool.returns


def test_equivalence_groups(tool_lib: ToolLibrary) -> None:
    """Verify equivalence relations for substitutability testing."""
    # search_web, search_news, search_academic should be in same group
    assert tool_lib.is_equivalent("search_web", "search_news")
    assert tool_lib.is_equivalent("search_web", "search_academic")
    # send_email and send_sms should be equivalent (with caveats)
    assert tool_lib.is_equivalent("send_email", "send_sms")
    # calculator and unit_convert should NOT be equivalent
    assert not tool_lib.is_equivalent("calculator", "unit_convert")


def test_domain_classification(tool_lib: ToolLibrary) -> None:
    """Tools should be in 5 distinct domains."""
    domains = {t.domain for t in tool_lib.all_tools}
    assert "information_retrieval" in domains
    assert "computation" in domains
    assert "communication" in domains
    assert "file_io" in domains
    assert "scheduling" in domains


def test_get_unknown_tool(tool_lib: ToolLibrary) -> None:
    """Unknown tool name should raise KeyError."""
    with pytest.raises(KeyError):
        tool_lib.get("nonexistent_tool")
