"""Tests for task generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_compose.generator.tasks import TaskGenerator


@pytest.fixture
def generator() -> TaskGenerator:
    project_root = Path(__file__).parent.parent
    templates_path = project_root / "templates" / "task_templates.yaml"
    return TaskGenerator(templates_path=templates_path, seed=42)


def test_generator_loads_templates(generator: TaskGenerator) -> None:
    assert len(generator._templates) == 10, "Expected 10 task templates"


def test_generate_all_splits(generator: TaskGenerator) -> None:
    splits = generator.generate_all()
    assert set(splits.keys()) == {
        "train",
        "val",
        "test_systematicity",
        "test_productivity",
        "test_substitutability",
    }


def test_split_sizes(generator: TaskGenerator) -> None:
    splits = generator.generate_all()
    assert len(splits["train"]) == 250
    assert len(splits["val"]) == 100
    assert len(splits["test_systematicity"]) == 200
    assert len(splits["test_productivity"]) == 200
    assert len(splits["test_substitutability"]) == 100


def test_train_chains_are_short(generator: TaskGenerator) -> None:
    """Training tasks should have 1-2 tool chains (so test sets can compose them)."""
    splits = generator.generate_all()
    for task in splits["train"]:
        assert len(task.expected_chain) <= 2


def test_productivity_no_overlap_with_train(generator: TaskGenerator) -> None:
    """Productivity test: no 2-subchain should appear in training."""
    splits = generator.generate_all()
    train_pairs = generator._all_chain_pairs(splits["train"])
    for task in splits["test_productivity"]:
        task_pairs = generator._chain_pairs(task.expected_chain)
        overlap = task_pairs & train_pairs
        assert len(overlap) == 0, f"Task {task.task_id} shares {overlap} with train"


def test_substitutability_applies_substitution(generator: TaskGenerator) -> None:
    """Substitutability test should have at least one substituted tool."""
    splits = generator.generate_all()
    sub_applied = [
        t for t in splits["test_substitutability"] if t.metadata.get("substituted_tool")
    ]
    assert len(sub_applied) > 0


def test_save_and_load_roundtrip(generator: TaskGenerator, tmp_path: Path) -> None:
    splits = generator.generate_all()
    paths = generator.save_splits(splits, tmp_path)
    assert all(p.exists() for p in paths.values())
    # Spot-check one file
    sample = tmp_path / "train.jsonl"
    lines = sample.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 250
