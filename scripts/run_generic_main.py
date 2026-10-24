#!/usr/bin/env python3
"""run_generic_main.py - main benchmark with library-agnostic (generic) inference."""

import json
import shlex
import subprocess
import sys
from pathlib import Path

agents = ["react", "native_fc", "reflexion", "plan_execute", "chain_aware"]
root = Path(__file__).resolve().parents[1]
out = root / "results" / "generic_main"
out.mkdir(parents=True, exist_ok=True)
for a in agents:
    cmd = (
        f"python scripts/evaluate.py --agent {a} --split all "
        f"--output-dir results/generic_main --seed 42 --use-generic-inference"
    )
    print("$", cmd, flush=True)
    p = subprocess.run(shlex.split(cmd), cwd=str(root), check=False)
    if p.returncode != 0:
        sys.exit(f"FAILED {cmd}")
summ = {}
for a in agents:
    f = out / f"{a}_summary.json"
    if f.exists():
        summ[a] = json.loads(f.read_text(encoding="utf-8"))
(out / "generic_main_summary.json").write_text(
    json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("DONE", flush=True)
