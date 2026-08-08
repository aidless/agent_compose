#!/usr/bin/env python3
"""run_threeway_ablation.py - ChainAware three-way ablation (training x detector x scoring).

Runs substitutability and productivity splits under:
  full           : trained + detector + equivalence-aware scoring
  no_training    : ChainAware without chain-pattern training
  no_detector    : ChainAware with detector disabled
  strict_scoring : equivalence-aware scoring disabled (evaluator strict)
  react_strict   : ReAct under strict scoring (scoring-factor control)
"""
from __future__ import annotations
import json, shlex, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CELLS = [
    ("chain_aware", "full",          []),
    ("chain_aware", "no_training",   ["--no-chain-training"]),
    ("chain_aware", "no_detector",   ["--no-equiv-detector"]),
    ("chain_aware", "strict_scoring",["--no-equiv-eval"]),
    ("react",       "react_strict",  ["--no-equiv-eval"]),
]
SPLITS = ["test_substitutability", "test_productivity"]


def run(cmd: str):
    print(f"$ {cmd}", flush=True)
    p = subprocess.run(shlex.split(cmd), cwd=str(ROOT))
    if p.returncode != 0:
        sys.exit(f"FAILED: {cmd}")


def load_tsr(out, agent, split):
    f = out / f"{agent}_{split}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    m = d["task_metrics"]
    return round(sum(t["tsr"] for t in m) / len(m), 4) if m else None


def main() -> int:
    out = ROOT / "results" / "ablation_threeway"
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for agent, cell, extra in CELLS:
        report[cell] = {}
        for split in SPLITS:
            base = ["python", "scripts/evaluate.py", "--agent", agent, "--split", split,
                    "--data-dir", "data/generated", "--tools-dir", "tools",
                    "--output-dir", "results/ablation_threeway", "--seed", "42"] + extra
            run(" ".join(base))
            report[cell][split] = load_tsr(out, agent, split)
            print(f"{cell} {split}: {report[cell][split]}", flush=True)
    json_path = ROOT / "results" / "ablation_threeway.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())