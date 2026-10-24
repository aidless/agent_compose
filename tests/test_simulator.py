"""Tests for the JSON API simulator."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_compose.env.simulator import ToolCall, ToolSimulator
from agent_compose.tools import ToolLibrary


@pytest.fixture
def simulator() -> ToolSimulator:
    tools_dir = Path(__file__).parent.parent / "tools"
    library = ToolLibrary(tools_dir)
    return ToolSimulator(library, failure_rate=0.0, seed=42)


def test_search_web_returns_results(simulator: ToolSimulator) -> None:
    result = simulator.execute(
        ToolCall(tool_name="search_web", arguments={"query": "weather Tokyo"}, call_id="c1")
    )
    assert result.success
    assert isinstance(result.output, list)
    assert len(result.output) > 0


def test_calculator_evaluates(simulator: ToolSimulator) -> None:
    result = simulator.execute(
        ToolCall(tool_name="calculator", arguments={"expression": "(10 + 20) * 3"}, call_id="c2")
    )
    assert result.success
    assert result.output == 90.0


def test_unit_convert_currency(simulator: ToolSimulator) -> None:
    result = simulator.execute(
        ToolCall(
            tool_name="unit_convert",
            arguments={"value": 100, "from_unit": "USD", "to_unit": "EUR"},
            call_id="c3",
        )
    )
    assert result.success
    assert 90 < result.output < 100


def test_send_email_records_side_effect(simulator: ToolSimulator) -> None:
    simulator.reset_state()
    simulator.execute(
        ToolCall(
            tool_name="send_email",
            arguments={"to": "alice@example.com", "subject": "Hi", "body": "Body"},
            call_id="c4",
        )
    )
    assert len(simulator.state["sent_emails"]) == 1
    assert simulator.state["sent_emails"][0]["to"] == "alice@example.com"


def test_unknown_tool_returns_error(simulator: ToolSimulator) -> None:
    result = simulator.execute(ToolCall(tool_name="does_not_exist", arguments={}, call_id="c5"))
    assert not result.success
    assert "Unknown tool" in result.error


def test_failure_injection_deterministic() -> None:
    """Same call_id should produce same failure outcome."""
    tools_dir = Path(__file__).parent.parent / "tools"
    library = ToolLibrary(tools_dir)
    sim1 = ToolSimulator(library, failure_rate=0.5, seed=42)
    sim2 = ToolSimulator(library, failure_rate=0.5, seed=99)
    # Same call_id, different seeds - both should be deterministic
    r1a = sim1.execute(ToolCall(tool_name="search_web", arguments={"query": "x"}, call_id="FIXED"))
    r1b = sim1.execute(ToolCall(tool_name="search_web", arguments={"query": "x"}, call_id="FIXED"))
    assert r1a.success == r1b.success  # Deterministic for same call_id
    r2a = sim2.execute(ToolCall(tool_name="search_web", arguments={"query": "x"}, call_id="FIXED"))
    r2b = sim2.execute(ToolCall(tool_name="search_web", arguments={"query": "x"}, call_id="FIXED"))
    assert r2a.success == r2b.success  # Same holds for a different seed


def test_read_file_returns_mock_content(simulator: ToolSimulator) -> None:
    result = simulator.execute(
        ToolCall(tool_name="read_file", arguments={"path": "/data/numbers_a.csv"}, call_id="c6")
    )
    assert result.success
    assert "10,20" in result.output
