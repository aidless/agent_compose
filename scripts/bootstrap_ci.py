"""Bootstrap confidence intervals for TSR and CGG.

For each agent x split combination, compute 95% CI for TSR via 1000 bootstrap
resamples. Saves results to results/bootstrap_ci.json.

Usage:
    python scripts/bootstrap_ci.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def bootstrap_ci(values: list[float], n_iter: int = 1000, alpha: float = 0.05) -> dict[str, float]:
    """Compute bootstrap CI for the mean of `values`."""
    arr = np.array(values, dtype=float)
    n = len(arr)
    if n == 0:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_iter):
        sample = rng.choice(arr, size=n, replace=True)
        means.append(sample.mean())
    means_arr = np.array(means)
    return {
        "mean": float(arr.mean()),
        "ci_low": float(np.percentile(means_arr, 100 * alpha / 2)),
        "ci_high": float(np.percentile(means_arr, 100 * (1 - alpha / 2))),
        "n": int(n),
    }


def compute_cgg_ci(agent: str, per_split: dict[str, list[float]]) -> dict[str, dict]:
    """For one agent, compute TSR CI per split + CGG = TSR_val - TSR_test CI."""
    results: dict[str, dict] = {}
    val_arr = np.array(per_split.get("val", []), dtype=float)
    for split in ["test_systematicity", "test_productivity", "test_substitutability"]:
        test_arr = np.array(per_split.get(split, []), dtype=float)
        if len(val_arr) == 0 or len(test_arr) == 0:
            continue
        # Bootstrap CGG: resample val and test independently, compute diff
        rng = np.random.default_rng(42)
        n_iter = 1000
        diffs = []
        for _ in range(n_iter):
            v = rng.choice(val_arr, size=len(val_arr), replace=True).mean()
            t = rng.choice(test_arr, size=len(test_arr), replace=True).mean()
            diffs.append(v - t)
        diffs_arr = np.array(diffs)
        results[split] = {
            "tsr_val": float(val_arr.mean()),
            "tsr_test": float(test_arr.mean()),
            "cgg": float(val_arr.mean() - test_arr.mean()),
            "cgg_ci_low": float(np.percentile(diffs_arr, 2.5)),
            "cgg_ci_high": float(np.percentile(diffs_arr, 97.5)),
            "n_val": len(val_arr),
            "n_test": len(test_arr),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent.parent / "results")
    parser.add_argument("--agents", nargs="+", default=[
        "react", "native_fc", "reflexion", "plan_execute", "chain_aware",
        "deepseek_react", "deepseek_fc",
    ])
    args = parser.parse_args()

    summary: dict[str, dict] = {}

    for agent in args.agents:
        agent_data: dict[str, list[float]] = {}
        for split in ["val", "test_systematicity", "test_productivity", "test_substitutability"]:
            f = args.results_dir / f"{agent}_{split}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            tsr_values = [m["tsr"] for m in d.get("task_metrics", [])]
            agent_data[split] = tsr_values
        if not agent_data:
            continue
        # Per-split CI
        split_cis = {s: bootstrap_ci(v) for s, v in agent_data.items()}
        # Per-CGG CI (val vs each test)
        cgg_cis = compute_cgg_ci(agent, agent_data)
        summary[agent] = {
            "tsr_ci": split_cis,
            "cgg_ci": cgg_cis,
        }
        print(f"\n{agent}:")
        for split, ci in split_cis.items():
            print(f"  {split:24s} TSR={ci['mean']:.3f}  95%CI=[{ci['ci_low']:.3f}, {ci['ci_high']:.3f}]  N={ci['n']}")
        for split, cgg in cgg_cis.items():
            print(f"  CGG_{split.replace('test_', ''):14s} = {cgg['cgg']:+.3f}  95%CI=[{cgg['cgg_ci_low']:+.3f}, {cgg['cgg_ci_high']:+.3f}]")

    out = args.results_dir / "bootstrap_ci.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n✓ Bootstrap CI saved to {out}")


if __name__ == "__main__":
    main()