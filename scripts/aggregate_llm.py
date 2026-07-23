"""Merge per-split summary fragments into a single agent summary.

After running `evaluate_llm.py --split <one>` multiple times, each call overwrites
the {agent}_summary.json. To accumulate, read the per-split json files and re-write.

Usage:
    python scripts/aggregate_llm.py --agent deepseek_react
    python scripts/aggregate_llm.py --agent deepseek_fc
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SPLITS = ["val", "test_systematicity", "test_productivity", "test_substitutability"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate LLM agent summary")
    parser.add_argument("--agent", required=True, choices=["deepseek_react", "deepseek_fc"])
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent.parent / "results")
    args = parser.parse_args()

    summary: dict[str, dict] = {}
    for split in SPLITS:
        path = args.results_dir / f"{args.agent}_{split}.json"
        if not path.exists():
            print(f"  ⚠ missing {path.name}")
            continue
        # The per-split file is the full save_results dump — re-aggregate from raw
        data = json.loads(path.read_text(encoding="utf-8"))
        # Layout: {"agent": "...", "split": "...", "task_metrics": [...], "traces": [...]}
        task_metrics = data.get("task_metrics", [])
        tsr_count = sum(1 for m in task_metrics if m.get("tsr") == 1.0)
        coc_count = sum(1 for m in task_metrics if m.get("coc") == 1.0)
        # ABA = mean of call count / max_steps averaged per trace
        if task_metrics:
            tsr = tsr_count / len(task_metrics)
            coc = coc_count / len(task_metrics)
        else:
            tsr = coc = 0.0
        # Pull tokens/time from the most recent run summary if available
        summary_path = args.results_dir / f"{args.agent}_summary.json"
        prev = {}
        if summary_path.exists():
            try:
                prev = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                prev = {}

        tokens = prev.get(split, {}).get("tokens", 0) if isinstance(prev.get(split), dict) else 0
        time_s = prev.get(split, {}).get("time_s", 0.0) if isinstance(prev.get(split), dict) else 0.0

        summary[split] = {
            "tsr": tsr,
            "coc": coc,
            "n": len(task_metrics),
            "tokens": tokens,
            "time_s": time_s,
        }
        print(f"  ✓ {split:24s}  TSR={tsr:.3f}  COC={coc:.3f}  N={len(task_metrics)}")

    if "val" in summary and "test_productivity" in summary:
        cgg = summary["val"]["tsr"] - summary["test_productivity"]["tsr"]
        print(f"\n  CGG (val - productivity): {cgg:+.3f}")
        summary["cgg_productivity"] = round(cgg, 4)
    if "val" in summary and "test_systematicity" in summary:
        cgg_sys = summary["val"]["tsr"] - summary["test_systematicity"]["tsr"]
        summary["cgg_systematicity"] = round(cgg_sys, 4)
        print(f"  CGG (val - systematicity): {cgg_sys:+.3f}")
    if "val" in summary and "test_substitutability" in summary:
        cgg_sub = summary["val"]["tsr"] - summary["test_substitutability"]["tsr"]
        summary["cgg_substitutability"] = round(cgg_sub, 4)
        print(f"  CGG (val - substitutability): {cgg_sub:+.3f}")

    out = args.results_dir / f"{args.agent}_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n✓ Aggregated → {out}")


if __name__ == "__main__":
    main()