"""Drift guards for counts, the seed-42 dataset, and README claims.

No API key. No network. A skip here would be a false green, so nothing is skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_compose.invariants import (
    LIVE_AGENTS,
    aggregate_committed_live,
    cgg_or_none,
    count_test_functions,
    dataset_fingerprint,
    load_manifest,
    recompute_template_agents,
    render_observed_section,
    tool_inventory,
)

ROOT = Path(__file__).resolve().parents[1]


def _dump(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_tool_inventory_matches_manifest() -> None:
    """Tool count, domain list, and equivalence metadata stay aligned."""
    manifest = load_manifest(ROOT)
    inventory = tool_inventory(ROOT)
    assert inventory["n_tools"] == manifest["n_tools"]
    assert inventory["meta_total_tools"] == manifest["n_tools"]
    assert inventory["listed_names"] == inventory["names"] or set(inventory["listed_names"]) == set(
        inventory["names"]
    )
    assert sorted(inventory["listed_names"]) == inventory["names"]
    assert inventory["n_domains"] == manifest["n_domains"]
    assert inventory["domains"] == manifest["domains"]
    assert inventory["n_equivalence_groups"] == manifest["n_equivalence_groups"]


def test_dataset_fingerprint_matches_manifest() -> None:
    """Regenerating seed 42 reproduces the committed task-set hash and sizes."""
    manifest = load_manifest(ROOT)
    finger = dataset_fingerprint(ROOT, seed=manifest["seed"])
    assert finger["n_templates"] == manifest["n_templates"]
    assert finger["sizes"] == manifest["splits"]
    assert finger["n_tasks"] == manifest["n_tasks"]
    assert finger["sha256"] == manifest["dataset_sha256"]


def test_readme_has_no_static_count_badges() -> None:
    """Passing-count and inventory badges must not be frozen shields."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    forbidden = (
        "img.shields.io/badge/tests",
        "img.shields.io/badge/tasks",
        "img.shields.io/badge/tools",
        "img.shields.io/badge/CI",
        "41/41",
        "39/39",
        "39 / 39",
        "N=100",
    )
    for snippet in forbidden:
        assert snippet not in text, snippet
    assert "img.shields.io/badge/" not in text


def test_readme_status_and_observed_block() -> None:
    """The README status line and the observed number block match the files."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "STATUS: WORK-IN-PROGRESS — not A yet" in text
    assert "FAILURE_MODES.md" in text
    start = "<!-- OBSERVED:START -->\n"
    end = "\n<!-- OBSERVED:END -->"
    assert start in text and end in text
    block = text.split(start, 1)[1].split(end, 1)[0]
    assert block == render_observed_section(ROOT).rstrip("\n")


def test_template_recompute_matches_pin() -> None:
    """Current heuristic agents match the pinned recompute, not a hidden edit."""
    fresh = recompute_template_agents(ROOT)
    pinned = ROOT / "results" / "recompute_seed42.json"
    assert _dump(fresh) == pinned.read_text(encoding="utf-8")
    mismatches = fresh["mismatches_vs_committed_summaries"]
    assert mismatches
    assert fresh["provenance"]["model"] == "none"
    assert fresh["provenance"]["status"] == "OBSERVED"


def test_live_aggregate_matches_pin() -> None:
    """DeepSeek tables in the README are means of committed traces, not new runs."""
    fresh = aggregate_committed_live(ROOT)
    pinned = ROOT / "results" / "live_llm_observed.json"
    assert _dump(fresh) == pinned.read_text(encoding="utf-8")
    assert fresh["provenance"]["model"] == "UNKNOWN"
    assert fresh["provenance"]["date"] == "UNKNOWN"
    assert fresh["provenance"]["seed"] == "UNKNOWN"
    for agent in LIVE_AGENTS:
        for split_name, row in fresh["agents"][agent].items():
            assert row["n"] == 200, (agent, split_name, row["n"])


def test_deepseek_summary_files_stay_partial() -> None:
    """The committed summary files are incomplete. Do not treat them as full tables."""
    react = json.loads(
        (ROOT / "results" / "deepseek_react_summary.json").read_text(encoding="utf-8")
    )
    fc = json.loads((ROOT / "results" / "deepseek_fc_summary.json").read_text(encoding="utf-8"))
    assert set(react) == {"val"}
    assert set(fc) == {"test_substitutability"}
    assert "model" not in react["val"]
    assert "seed" not in fc["test_substitutability"]


def test_test_function_count_matches_manifest() -> None:
    """Pytest collection count is pinned. Tests are plain functions."""
    manifest = load_manifest(ROOT)
    assert count_test_functions(ROOT) == manifest["n_test_functions"]
    blob = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "tests").glob("test_*.py")
    )
    # Split so this source file does not contain the decorator spelling.
    forbidden = "mark." + "parametrize"
    assert forbidden not in blob


def test_package_version_is_alpha() -> None:
    """The package version stays the declared alpha, not an implied release."""
    import agent_compose

    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert agent_compose.__version__ == "0.1.0"
    assert 'version = "0.1.0"' in text
    assert "Development Status :: 3 - Alpha" in text


def test_statistical_tests_file_is_not_strict_json() -> None:
    """The committed stats file contains bare NaN tokens."""
    raw = (ROOT / "results" / "statistical_tests.json").read_text(encoding="utf-8")
    assert "NaN" in raw
    prose = (ROOT / "FAILURE_MODES.md").read_text(encoding="utf-8")
    assert "NaN" in prose


def test_missing_split_is_not_a_zero_gap() -> None:
    """A summary that never ran a split must not become a CGG of 0."""
    partial = {"val": {"tsr": 0.125}}
    assert cgg_or_none(partial, "test_productivity") is None
    assert (
        cgg_or_none({"val": {"tsr": 0.5}, "test_productivity": {"tsr": 0.25}}, "test_productivity")
        == 0.25
    )


def test_ci_workflow_does_not_call_live_models() -> None:
    """GitHub Actions covers the offline suite only."""
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    code = "\n".join(line for line in workflow.splitlines() if not line.strip().startswith("#"))
    assert "evaluate_llm" not in code
    assert "DEEPSEEK" not in code
    assert "run_all.py" not in code
    assert "offline" in workflow.lower()
