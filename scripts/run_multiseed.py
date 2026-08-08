#!/usr/bin/env python3
"""run_multiseed.py - run the 5 template agents across independent seeds.

For each requested seed S:
  1. python scripts/generate.py --seed S      (regenerates data/generated with seed S)
  2. for each agent: python scripts/evaluate.py --agent A --split all \
       --output-dir results/seed{S} --seed S
After the loop, regenerate the canonical seed-42 dataset and compute
seed-level TSR stats across results/ (seed 42) and results/seed{S}/.

Usage:
  python scripts/run_multiseed.py --seeds 1 2 3 4
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
CANONICAL_SEED = 42


def run(cmd: str) -> None:
    print(f"$ {cmd}", flush=True)
    proc = subprocess.run(shlex.split(cmd), cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        raise SystemExit(f"FAILED ({proc.returncode}): {cmd}")


def load_summary(seed_dir: Path, agent: str):
    f = seed_dir / f"{agent}_summary.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--agents", nargs="+", default=AGENTS)
    args = parser.parse_args()

    for seed in args.seeds:
        print(f"\n===== SEED {seed} =====", flush=True)
        run(f"python scripts/generate.py --seed {seed}")
        for agent in args.agents:
            run(f"python scripts/evaluate.py --agent {agent} --split all "
                f"--output-dir results/seed{seed} --seed {seed}")

    # Restore canonical data
    run(f"python scripts/generate.py --seed {CANONICAL_SEED}")

    # Seed-level stats across results/ (seed 42) + results/seed{S}/
    dirs = [PROJECT_ROOT / "results"] + [PROJECT_ROOT / "results" / f"seed{s}" for s in args.seeds]
    out: dict = {}
    for agent in args.agents:
        per_agent = {}
        for split in SPLITS:
            tsrs = []
            for d in dirs:
                s = load_summary(d, agent)
                if s and split in s:
                    tsrs.append(float(s[split]["tsr"]))
            if tsrs:
                arr = sorted(tsrs)
                n = len(arr)
                mean = sum(arr) / n
                lo, hi = arr[0], arr[-1]
                per_agent[split] = {
                    "n_seeds": n,
                    "mean": round(mean, 4),
                    "min": round(lo, 4),
                    "max": round(hi, 4),
                    "per_seed": [round(x, 4) for x in tsrs],
                }
        out[agent] = per_agent
    out_path = PROJECT_ROOT / "results" / "seed_variance.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())