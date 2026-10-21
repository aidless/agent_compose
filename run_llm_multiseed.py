# -*- coding: utf-8 -*-
"""DeepSeek-ReAct multiseed (seed 1,2) on compositional splits, N=100 each.
Outputs to results/llm_seed{seed}/ to avoid overwriting the N=200 seed-42 files."""
import subprocess, sys, time

SEEDS = [1, 2]
SPLITS = ["test_systematicity", "test_productivity", "test_substitutability"]
TIMEOUT_S = 50 * 60
for seed in SEEDS:
    for split in SPLITS:
        for attempt in (1, 2):
            print(f"=== seed{seed} {split} N=100 attempt {attempt} ===", flush=True)
            t0 = time.time()
            try:
                r = subprocess.run([sys.executable, "scripts/evaluate_llm.py", "--agent", "deepseek_react",
                                    "--split", split, "--max-tasks", "100", "--seed", str(seed),
                                    "--output-dir", f"results/llm_seed{seed}"],
                                   capture_output=True, text=True, timeout=TIMEOUT_S)
                print(r.stdout[-500:], flush=True)
                if r.returncode != 0:
                    print("RC:", r.returncode, r.stderr[-300:], flush=True)
                    continue
                print(f"=== seed{seed} {split} OK in {(time.time()-t0)/60:.1f} min ===", flush=True)
                break
            except subprocess.TimeoutExpired:
                print(f"!!! seed{seed} {split} TIMEOUT", flush=True)
                continue
print("ALL DONE", flush=True)