# -*- coding: utf-8 -*-
"""robust FC N=200 runner: per-split subprocess with timeout + one retry."""
import subprocess, sys, time

SPLITS = ["val", "test_systematicity", "test_productivity", "test_substitutability"]
TIMEOUT_S = 90 * 60

for split in SPLITS:
    for attempt in (1, 2):
        print(f"=== {split} N=200 attempt {attempt} ===", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, "scripts/evaluate_llm.py", "--agent", "deepseek_fc",
                                "--split", split, "--max-tasks", "200", "--seed", "42"],
                               capture_output=True, text=True, timeout=TIMEOUT_S)
            print(r.stdout[-600:], flush=True)
            if r.returncode != 0:
                print("RC:", r.returncode, r.stderr[-300:], flush=True)
                continue
            print(f"=== {split} OK in {(time.time()-t0)/60:.1f} min ===", flush=True)
            break
        except subprocess.TimeoutExpired:
            print(f"!!! {split} attempt {attempt} TIMEOUT after {TIMEOUT_S/60:.0f} min", flush=True)
            continue
print("ALL DONE", flush=True)