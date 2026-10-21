import subprocess, sys, time
splits = ["test_systematicity", "test_productivity", "test_substitutability"]
for split in splits:
    print(f"=== {split} N=200 ===", flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, "scripts/evaluate_llm.py", "--agent", "deepseek_react",
                        "--split", split, "--max-tasks", "200", "--seed", "42"], capture_output=True, text=True)
    print(r.stdout[-1500:], flush=True)
    if r.returncode != 0:
        print("ERR:", r.stderr[-500:], flush=True)
    print(f"=== {split} done in {(time.time()-t0)/60:.1f} min ===", flush=True)
print("ALL DONE", flush=True)