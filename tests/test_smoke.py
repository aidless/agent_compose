"""End-to-end smoke tests for AgentCompose.

These tests verify that the full reproduction pipeline produces the expected
output artefacts. Designed to run in CI without DeepSeek API access.

Run with:
    pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


def _load_summary(agent: str) -> dict | None:
    """Load results/{agent}_summary.json if present."""
    path = PROJECT_ROOT / "results" / f"{agent}_summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_all_help() -> None:
    """run_all.py is executable and accepts --help."""
    proc = subprocess.run(
        [sys.executable, "scripts/run_all.py", "--help"],
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "AgentCompose" in proc.stdout or "reproduction" in proc.stdout.lower()


def test_run_all_dry_run_lists_steps() -> None:
    """--dry-run prints the plan without executing anything."""
    proc = subprocess.run(
        [sys.executable, "scripts/run_all.py", "--dry-run", "--skip-llm"],
        cwd=str(PROJECT_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "generate" in proc.stdout
    assert "make_figures" in proc.stdout


@pytest.mark.skipif(
    not (PROJECT_ROOT / "data" / "generated" / "val.jsonl").exists(),
    reason="val split not yet generated; run `python scripts/generate.py` first",
)
def test_val_split_exists_and_is_valid_jsonl() -> None:
    """The val.jsonl file should parse as one-JSON-per-line."""
    val_path = PROJECT_ROOT / "data" / "generated" / "val.jsonl"
    assert val_path.exists()
    n = 0
    for line in val_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)  # raises on malformed JSON
        assert "task_id" in d
        assert "expected_chain" in d
        assert isinstance(d["expected_chain"], list)
        n += 1
    assert n >= 100, f"val split should have ≥100 tasks, got {n}"


@pytest.mark.skipif(
    not (PROJECT_ROOT / "results" / "chain_aware_summary.json").exists(),
    reason="chain_aware results not yet produced",
)
def test_chain_aware_summary_has_all_splits() -> None:
    """chain_aware_summary.json should contain all 4 evaluation splits."""
    summary = _load_summary("chain_aware")
    assert summary is not None
    for split in ("val", "test_systematicity", "test_productivity", "test_substitutability"):
        assert split in summary, f"missing split {split}"
        assert "tsr" in summary[split], f"{split} missing tsr"
        assert 0.0 <= summary[split]["tsr"] <= 1.0


@pytest.mark.skipif(
    not (PROJECT_ROOT / "figures" / "fig1_cgg_bar.pdf").exists(),
    reason="figures not yet generated",
)
def test_figures_exist() -> None:
    """All 6 figures (pdf + png) should exist after `make_figures.py` + CD diagram."""
    for fig in (
        "fig1_cgg_bar",
        "fig2_metrics_heatmap",
        "fig3_error_breakdown",
        "fig4_ablation",
        "fig5_chain_length_dist",
        "fig6_cd_diagram",
    ):
        for ext in ("pdf", "png"):
            p = PROJECT_ROOT / "figures" / f"{fig}.{ext}"
            assert p.exists(), f"missing figure: {p}"
            assert p.stat().st_size > 1000, f"{p.name} suspiciously small ({p.stat().st_size} B)"


def test_llm_vendor_registry() -> None:
    """LLM_VENDORS exposes at least DeepSeek + OpenAI + Anthropic configs."""
    from agent_compose.agents.llm_react import LLM_VENDORS

    assert "deepseek" in LLM_VENDORS
    assert "openai" in LLM_VENDORS
    assert "anthropic" in LLM_VENDORS
    for v in LLM_VENDORS.values():
        assert "env_var" in v
        assert "base_url" in v
        assert "default_model" in v
        assert "display_name" in v


def test_llm_agent_raises_without_api_key(monkeypatch) -> None:
    """DeepSeekReactAgent must raise ValueError when no API key is set."""
    from pathlib import Path

    from agent_compose.agents.llm_react import DeepSeekReactAgent
    from agent_compose.tools import ToolLibrary

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    library = ToolLibrary(Path(PROJECT_ROOT / "tools"))
    for vendor in ("deepseek", "openai", "anthropic"):
        with pytest.raises(ValueError, match="not set"):
            DeepSeekReactAgent(library, max_steps=2, vendor=vendor)
