"""Generate the AgentCompose dataset.

Usage:
    python scripts/generate.py --output data/generated/ --seed 42
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_compose.generator.tasks import TaskGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AgentCompose benchmark tasks")
    parser.add_argument(
        "--templates",
        type=Path,
        default=Path(__file__).parent.parent / "templates" / "task_templates.yaml",
        help="Path to task templates YAML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "generated",
        help="Output directory for generated JSONL files",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    print(f"Generating tasks with seed={args.seed}...")
    gen = TaskGenerator(templates_path=args.templates, seed=args.seed)
    splits = gen.generate_all()
    paths = gen.save_splits(splits, args.output)

    print("\n✓ Generation complete")
    print(f"  Output directory: {args.output}")
    for split_name, file_path in paths.items():
        print(f"  {split_name:30s} → {file_path.name} ({file_path.stat().st_size} bytes)")

    stats = gen.statistics(splits)
    print("\n✓ Statistics:")
    print(f"  {'Split':30s} {'N':>6s} {'AvgLen':>8s} {'MaxLen':>8s} {'Tools':>8s}")
    print("  " + "-" * 60)
    for split_name, s in stats.items():
        print(
            f"  {split_name:30s} {s['n_tasks']:>6d} "
            f"{s['avg_chain_length']:>8.2f} {s['max_chain_length']:>8d} "
            f"{s['unique_tools_used']:>8d}"
        )

    # Save statistics as well
    stats_path = args.output / "statistics.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\n✓ Statistics saved to {stats_path}")


if __name__ == "__main__":
    main()
