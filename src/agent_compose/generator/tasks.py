"""Task generation: turn YAML templates into concrete task instances.

Generates the three generalization splits (Systematicity, Productivity, Substitutability)
with strict guarantees about tool chain co-occurrence in training data.

Usage:
    from agent_compose.generator.tasks import TaskGenerator
    gen = TaskGenerator(seed=42)
    splits = gen.generate_all()
    gen.save_splits(splits, "data/generated/")
"""

from __future__ import annotations

import itertools
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Task:
    """A single benchmark task instance."""

    task_id: str
    template_id: str
    natural_language: str
    expected_chain: list[str]
    parameters: dict[str, Any]
    success_criteria: list[str]
    split: str = "train"  # train | val | test_systematicity | test_productivity | test_substitutability
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "task_id": self.task_id,
            "template_id": self.template_id,
            "natural_language": self.natural_language,
            "expected_chain": self.expected_chain,
            "parameters": self.parameters,
            "success_criteria": self.success_criteria,
            "split": self.split,
            "metadata": self.metadata,
        }


class TaskGenerator:
    """Generate task instances from templates with controlled generalization splits."""

    def __init__(
        self,
        templates_path: Path,
        seed: int = 42,
        # Splits sizes. Train/Val are constrained to 2-tool chains (only T1 and T5
        # templates have such chains; other templates' 3-4 tool chains are reserved
        # for compositional test splits).
        n_train: int = 1200,
        n_val: int = 400,
        n_test_systematicity: int = 600,
        n_test_productivity: int = 600,
        n_test_substitutability: int = 200,
        # Substitutability: fraction of tasks where search_web -> search_news
        sub_substitution_rate: float = 0.5,
        # Extension tool pools (must be tools present in the tool library).
        # Override these for alternate tool libraries (external validity).
        tail_tools: Optional[Sequence[str]] = None,
        candidate_heads_pool: Optional[Sequence[str]] = None,
        # Templates allowed to enter the train/val pools (test-only templates
        # keep productivity constructible in external libraries).
        train_template_ids: Optional[Sequence[str]] = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.templates_path = Path(templates_path)
        self.seed = seed
        self.tail_tools = list(tail_tools) if tail_tools else ["send_email", "send_sms", "write_file", "calendar_add"]
        self.train_template_ids = set(train_template_ids) if train_template_ids else None
        self.candidate_heads_pool = list(candidate_heads_pool) if candidate_heads_pool else ["send_email", "send_sms", "write_file", "calendar_add", "read_file", "calculator", "unit_convert"]
        self.n_train = n_train
        self.n_val = n_val
        self.n_test_systematicity = n_test_systematicity
        self.n_test_productivity = n_test_productivity
        self.n_test_substitutability = n_test_substitutability
        self.sub_substitution_rate = sub_substitution_rate

        self._templates: list[dict[str, Any]] = []
        self._load_templates()

    def _load_templates(self) -> None:
        """Load task templates from YAML."""
        data = yaml.safe_load(self.templates_path.read_text(encoding="utf-8"))
        self._templates = data["templates"]

    def _instantiate_template(self, template: dict[str, Any]) -> Task:
        """Create one concrete task from a template by sampling parameter values."""
        params: dict[str, Any] = {}
        for param_name, choices in template["parameters"].items():
            params[param_name] = self.rng.choice(choices)

        # Fill natural language template
        nl = template["natural_language"].format(**params)

        # Format success criteria
        criteria = [c.format(**params) for c in template["success_criteria"]]

        return Task(
            task_id=f"{template['id']}_{self.rng.randint(10000, 99999)}",
            template_id=template["id"],
            natural_language=nl,
            expected_chain=list(template["minimal_chain"]),
            parameters=params,
            success_criteria=criteria,
        )

    def _generate_base_pool(self, n: int) -> list[Task]:
        """Generate n base tasks by sampling from templates uniformly."""
        tasks: list[Task] = []
        for _ in range(n):
            template = self.rng.choice(self._templates)
            tasks.append(self._instantiate_template(template))
        return tasks

    def _chain_pairs(self, chain: list[str]) -> set[tuple[str, str]]:
        """Get all 2-tool sub-chains (adjacent pairs) from a chain."""
        return {(chain[i], chain[i + 1]) for i in range(len(chain) - 1)}

    def _all_chain_pairs(self, tasks: list[Task]) -> set[tuple[str, str]]:
        """Get all 2-tool sub-chains across a set of tasks."""
        pairs: set[tuple[str, str]] = set()
        for task in tasks:
            pairs.update(self._chain_pairs(task.expected_chain))
        return pairs

    def _tools_used_in_train(self, tasks: list[Task]) -> list[str]:
        """Return list of unique tools used in the training tasks (sorted)."""
        tools: set[str] = set()
        for task in tasks:
            tools.update(task.expected_chain)
        return sorted(tools)

    def generate_all(self) -> dict[str, list[Task]]:
        """Generate all splits with controlled generalization guarantees.

        Returns dict with keys: train, val, test_systematicity, test_productivity, test_substitutability
        """
        # Step 1: Generate train + val from "easy" templates (2-tool minimal chains)
        # Step 2: Generate test_systematicity (3-tool chains with at least one seen pair)
        # Step 3: Generate test_productivity (3-tool chains where NO 2-subchain seen in train)
        # Step 4: Generate test_substitutability (apply schema substitutions to val set)

        # Oversample heavily because only 2/10 templates have 2-tool minimal chains.
        # Sampling uniformly gives ~20% of pool as 2-tool. We oversample 10x.
        train_candidates = self._generate_base_pool(self.n_train * 10)
        val_candidates = self._generate_base_pool(self.n_val * 10)
        if self.train_template_ids is not None:
            train_candidates = [t for t in train_candidates if t.template_id in self.train_template_ids]
            val_candidates = [t for t in val_candidates if t.template_id in self.train_template_ids]

        # Train: 2-tool minimal chains only. Longer chains in train would leak test info.
        train_tasks = [t for t in train_candidates if len(t.expected_chain) == 2][: self.n_train]
        val_tasks = [t for t in val_candidates if len(t.expected_chain) == 2][: self.n_val]

        # Mark them
        for t in train_tasks:
            t.split = "train"
        for t in val_tasks:
            t.split = "val"

        # Track training distribution for systematicity/productivity constraints
        train_pairs = self._all_chain_pairs(train_tasks)

        # --- Systematicity test ---
        # Extend 2-tool train chains to 3 tools by appending a common tail tool.
        # The resulting chain's sub-pairs include the original train pair (in train_pairs).
        sys_candidates = self._generate_base_pool(self.n_test_systematicity * 3)
        sys_test: list[Task] = []
        # Common tail tools to extend chains (in train_pairs via training extensions)
        tail_tools = self.tail_tools
        for task in sys_candidates:
            # Pick a tail tool that, when appended, keeps at least one sub-pair in train_pairs
            base_chain = list(task.expected_chain)
            for tail in tail_tools:
                extended = base_chain + [tail]
                extended_pairs = self._chain_pairs(extended)
                if extended_pairs & train_pairs:
                    # Success: extension preserves at least one trained pair
                    task.expected_chain = extended
                    task.metadata["extended_for_systematicity"] = True
                    task.metadata["tail_tool"] = tail
                    task.split = "test_systematicity"
                    sys_test.append(task)
                    break
            if len(sys_test) >= self.n_test_systematicity:
                break
        sys_test = sys_test[: self.n_test_systematicity]

        # --- Productivity test ---
        # 3-tool chains where NO 2-subchain appears in training.
        # Strategy: pair two 2-tool chains whose middle tool makes (last_tool, head) absent
        # from train_pairs. Use a curated list of "compositional heads" that are tools not
        # commonly adjacent to last_tool in train.
        prod_candidates = self._generate_base_pool(self.n_test_productivity * 10)
        prod_test: list[Task] = []
        # All tools available for head-position (must not duplicate last_tool)
        candidate_heads_pool = self.candidate_heads_pool
        for task in prod_candidates:
            base_chain = list(task.expected_chain)
            last_tool = base_chain[-1]
            # Find a head where (last_tool, head) NOT in train_pairs
            for head in candidate_heads_pool:
                if head == last_tool:
                    continue
                extended = base_chain + [head]
                extended_pairs = self._chain_pairs(extended)
                if not (extended_pairs & train_pairs):
                    task.expected_chain = extended
                    task.metadata["extended_for_productivity"] = True
                    task.metadata["head_tool"] = head
                    task.split = "test_productivity"
                    prod_test.append(task)
                    break
            if len(prod_test) >= self.n_test_productivity:
                break
        prod_test = prod_test[: self.n_test_productivity]

        # --- Substitutability test ---
        # Take val tasks, substitute canonical tool with variant
        sub_test: list[Task] = []
        for task in val_tasks[: self.n_test_substitutability]:
            new_task = Task(
                task_id=f"sub_{task.task_id}",
                template_id=task.template_id,
                natural_language=task.natural_language,
                expected_chain=list(task.expected_chain),
                parameters=dict(task.parameters),
                success_criteria=list(task.success_criteria),
                split="test_substitutability",
                metadata={**task.metadata, "substitution_applied": True},
            )
            # Apply substitution to first occurrence of a substitutable tool
            substitution_map = {
                "search_web": "search_news",
                "send_email": "send_sms",
                "sql_query": "csv_filter",
                "image_classify": "ocr_extract",
                "send_slack": "send_push",
                "calendar_add": "calendar_list",
            }
            new_chain = []
            substituted = False
            substituted_from = None
            substituted_to = None
            for tool in new_task.expected_chain:
                if not substituted and tool in substitution_map:
                    substituted_from = tool
                    substituted_to = substitution_map[tool]
                    new_chain.append(substituted_to)
                    substituted = True
                else:
                    new_chain.append(tool)
            new_task.expected_chain = new_chain
            if substituted:
                new_task.metadata["substituted_tool"] = substituted_to
                new_task.metadata["original_tool"] = substituted_from
            else:
                new_task.metadata["substituted_tool"] = None
            sub_test.append(new_task)

        return {
            "train": train_tasks,
            "val": val_tasks,
            "test_systematicity": sys_test,
            "test_productivity": prod_test,
            "test_substitutability": sub_test,
        }

    def save_splits(self, splits: dict[str, list[Task]], output_dir: Path) -> dict[str, Path]:
        """Save each split as a JSONL file. Returns dict of split_name -> file_path."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        for split_name, tasks in splits.items():
            file_path = output_dir / f"{split_name}.jsonl"
            with file_path.open("w", encoding="utf-8") as f:
                for task in tasks:
                    f.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")
            paths[split_name] = file_path
        return paths

    def statistics(self, splits: dict[str, list[Task]]) -> dict[str, Any]:
        """Compute summary statistics for each split."""
        stats: dict[str, Any] = {}
        for split_name, tasks in splits.items():
            chain_lengths = [len(t.expected_chain) for t in tasks]
            all_tools = sorted({tool for t in tasks for tool in t.expected_chain})
            stats[split_name] = {
                "n_tasks": len(tasks),
                "avg_chain_length": sum(chain_lengths) / len(chain_lengths) if chain_lengths else 0,
                "max_chain_length": max(chain_lengths) if chain_lengths else 0,
                "unique_tools_used": len(all_tools),
                "tools": all_tools,
            }
        return stats
