#!/usr/bin/env python3
"""external_validity.py - second tool-library external validity check.

Generates tasks from templates_ext with the tools_ext library, evaluates the
5 template agents (+ ChainAware), and compares the compositional gap (CGG)
ordering against the main 30-tool benchmark.

Usage:
  python scripts/external_validity.py            # full run (~3-5 min)
  python scripts/external_validity.py --smoke    # tiny run for CI
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS = ["react", "native_fc", "reflexion", "plan_execute", "chain_aware"]
SPLITS = ["val", "test_systematicity", "test_productivity", "test_substitutability"]
MAX_TASKS = {"val": 100, "test_systematicity": 150, "test_productivity": 150, "test_substitutability": 50}


def run(cmd: str) -> None:
    print(f"$ {cmd}", flush=True)
    proc = subprocess.run(shlex.split(cmd), cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"FAILED ({proc.returncode}): {cmd}")


def load_summary(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    gen_args = ["python", "scripts/generate.py",
                "--templates", "templates_ext/task_templates.yaml",
                "--output", "data/generated_ext", "--seed", "42",
                "--tail-tools", "send_invoice,send_alert,print_label,book_courier",
                "--head-tools", "send_invoice,send_alert,toggle_light,set_thermostat,play_announcement,book_courier,transfer_funds,generate_report",
                "--train-templates", "X1_quote_invoice,X2_convert_reconcile,X3_sensor_thermostat,X4_quote_convert,X5_sensor_alert,X6_lock_alert"]
    if args.smoke:
        gen_args += []
    run(" ".join(gen_args))

    out_dir = PROJECT_ROOT / "results" / "external"
    out_dir.mkdir(parents=True, exist_ok=True)
    for agent in AGENTS:
        for split in SPLITS:
            cmd = (f"python scripts/evaluate.py --agent {agent} --split {split} "
                   f"--data-dir data/generated_ext --tools-dir tools_ext "
                   f"--output-dir results/external --max-tasks {MAX_TASKS[split]} --seed 42 --use-generic-inference")
            run(cmd)
    # val summary per agent (evaluate.py writes summary only for --split all)
    for agent in AGENTS:
        run(f"python scripts/evaluate.py --agent {agent} --split val "
            f"--data-dir data/generated_ext --tools-dir tools_ext "
            f"--output-dir results/external --max-tasks {MAX_TASKS['val']} --seed 42 --use-generic-inference")

    # Aggregate
    report: dict = {"agents": {}}
    main_order: dict = {}
    for agent in AGENTS:
        per_split = {}
        for split in SPLITS:
            f = out_dir / f"{agent}_{split}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            tsrs = [t["tsr"] for t in d["task_metrics"]]
            per_split[split] = round(sum(tsrs) / len(tsrs), 4) if tsrs else None
        report["agents"][agent] = per_split
        # CGG = val - split
        val = per_split.get("val")
        cgg = {k: (round(val - v, 4) if val is not None and v is not None else None)
               for k, v in per_split.items() if k != "val"}
        report["agents"][agent]["cgg"] = cgg
        main_sum = load_summary(PROJECT_ROOT / "results" / f"{agent}_summary.json")
        if main_sum:
            mval = main_sum["val"]["tsr"]
            main_order[agent] = {k: round(mval - main_sum[k]["tsr"], 4)
                                 for k in SPLITS if k != "val" and k in main_sum}
    report["main_benchmark_cgg"] = main_order

    # Spearman rank correlation of CGG ordering across libraries (per split)
    try:
        from scipy.stats import spearmanr
    except ImportError:
        spearmanr = None
    corr = {}
    for split in ["test_systematicity", "test_productivity", "test_substitutability"]:
        ext = [report["agents"][a]["cgg"].get(split) for a in AGENTS]
        main_ = [main_order[a].get(split) for a in AGENTS if a in main_order]
        valid = [(e, m) for e, m in zip(ext, main_) if e is not None and m is not None]
        if len(valid) >= 3 and spearmanr is not None:
            r, p = spearmanr([e for e, _ in valid], [m for _, m in valid])
            corr[split] = {"spearman_r": round(float(r), 3), "p": round(float(p), 4), "n": len(valid)}
        else:
            corr[split] = None
    report["cgg_ordering_correlation"] = corr

    out = PROJECT_ROOT / "results" / "external_validity.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())