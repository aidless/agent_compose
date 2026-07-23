"""Generate publication-quality figures from AgentCompose results.

Outputs (PDF + PNG):
1. fig1_cgg_bar.pdf — Compositional Generalization Gap across agents (the headline figure)
2. fig2_metrics_heatmap.pdf — Per-agent per-split metric heatmap
3. fig3_error_breakdown.pdf — 4-error-type stacked bar
4. fig4_ablation.pdf — Ablation curves
5. fig5_chain_length_dist.pdf — Task chain length distribution per split
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Color palette
COLORS = {
    "react": "#1f77b4",
    "native_fc": "#ff7f0e",
    "reflexion": "#2ca02c",
    "plan_execute": "#d62728",
    "chain_aware": "#9467bd",
    "deepseek_react": "#8c564b",
    "deepseek_fc": "#e377c2",
}


def load_all_summaries(results_dir: Path) -> dict[str, dict[str, dict]]:
    """Load all agent summary files."""
    summaries = {}
    for f in sorted(results_dir.glob("*_summary.json")):
        agent = f.stem.replace("_summary", "")
        summaries[agent] = json.loads(f.read_text(encoding="utf-8"))
    return summaries


def fig1_cgg_bar(summaries: dict, output_dir: Path) -> None:
    """Bar chart: CGG across agents × 3 test splits. Includes template + DeepSeek agents."""
    agents = ["react", "native_fc", "reflexion", "plan_execute", "chain_aware",
              "deepseek_react", "deepseek_fc"]
    splits = ["test_systematicity", "test_productivity", "test_substitutability"]
    split_labels = ["Systematicity", "Productivity", "Substitutability"]

    x = np.arange(len(splits))
    n_agents = len(agents)
    width = min(0.13, 0.95 / n_agents)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    for i, agent in enumerate(agents):
        if agent not in summaries or "val" not in summaries[agent]:
            continue
        val_tsr = summaries[agent]["val"]["tsr"]
        cggs = []
        for split in splits:
            if split in summaries[agent]:
                cgg = val_tsr - summaries[agent][split]["tsr"]
            else:
                cgg = 0
            cggs.append(cgg)
        offset = (i - (n_agents - 1) / 2) * width
        ax.bar(x + offset, cggs, width, label=agent, color=COLORS.get(agent, "gray"))

    ax.set_xlabel("Test Split", fontsize=12)
    ax.set_ylabel("Compositional Generalization Gap (TSR drop)", fontsize=12)
    ax.set_title("Compositional Generalization Gap Across Agents", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(split_labels)
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(output_dir / "fig1_cgg_bar.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "fig1_cgg_bar.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ fig1_cgg_bar saved")


def fig2_metrics_heatmap(summaries: dict, output_dir: Path) -> None:
    """Heatmap of metrics: agents × (split, metric)."""
    agents = list(summaries.keys())
    splits = ["val", "test_systematicity", "test_productivity", "test_substitutability"]
    metrics = ["tsr", "coc", "aba"]

    matrix = np.zeros((len(agents), len(splits) * len(metrics)))
    for i, agent in enumerate(agents):
        for j, split in enumerate(splits):
            for k, metric in enumerate(metrics):
                col = j * len(metrics) + k
                if split in summaries[agent]:
                    matrix[i, col] = summaries[agent][split].get(metric, 0)

    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(splits) * len(metrics)))
    ax.set_xticklabels(
        [f"{s.replace('test_', '').replace('val', 'i.i.d.')[:4]}\n{m.upper()}" for s in splits for m in metrics]
    )
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels(agents)
    ax.set_title("Per-Agent Per-Split Metric Heatmap")
    plt.colorbar(im, ax=ax)

    # Annotate values
    for i in range(len(agents)):
        for j in range(len(splits) * len(metrics)):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=7)

    fig.tight_layout()
    fig.savefig(output_dir / "fig2_metrics_heatmap.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "fig2_metrics_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ fig2_metrics_heatmap saved")


def fig3_error_breakdown(results_dir: Path, figures_dir: Path) -> None:
    """Stacked bar of error types per split (using NativeFC)."""
    error_file = results_dir / "error_analysis.json"
    if not error_file.exists():
        return
    data = json.loads(error_file.read_text(encoding="utf-8"))
    native_fc = data.get("native_fc", {}).get("rates", {})
    if not native_fc:
        return

    splits = ["val", "test_systematicity", "test_productivity", "test_substitutability"]
    error_types = ["missing_tool", "wrong_tool", "wrong_order", "bad_argument", "none"]

    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(splits))
    color_map = {
        "missing_tool": "#e41a1c",
        "wrong_tool": "#377eb8",
        "wrong_order": "#4daf4a",
        "bad_argument": "#984ea3",
        "none": "#999999",
    }

    for et in error_types:
        values = []
        for split in splits:
            v = native_fc.get(split, {}).get(et, 0)
            values.append(v)
        ax.bar(splits, values, bottom=bottom, label=et, color=color_map[et])
        bottom += np.array(values)

    ax.set_ylabel("Fraction of Tasks")
    ax.set_title("Error Type Breakdown (NativeFC Agent, 30-tool benchmark)")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 1.05)
    plt.xticks(rotation=15)

    fig.tight_layout()
    fig.savefig(figures_dir / "fig3_error_breakdown.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(figures_dir / "fig3_error_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ fig3_error_breakdown saved")


def fig4_ablation(results_dir: Path, figures_dir: Path) -> None:
    """Ablation: n_synthetic_chains vs Productivity TSR."""
    abl_file = results_dir / "ablation_n_synthetic.json"
    if not abl_file.exists():
        return
    data = json.loads(abl_file.read_text(encoding="utf-8"))

    x = [d["n_synthetic"] for d in data]
    y = [d["tsr_productivity"] for d in data]
    coc = [d["coc_productivity"] for d in data]

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.plot(x, y, "o-", color="#9467bd", label="Productivity TSR", linewidth=2, markersize=8)
    ax1.plot(x, coc, "s--", color="#ff7f0e", label="Productivity COC", linewidth=2, markersize=8)
    ax1.set_xlabel("Number of Synthetic Chains (n_synthetic)")
    ax1.set_ylabel("Score")
    ax1.set_title("Ablation: Effect of Synthetic Chain Augmentation (30-tool)")
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax1.set_ylim(0, 0.5)

    fig.tight_layout()
    fig.savefig(figures_dir / "fig4_ablation.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(figures_dir / "fig4_ablation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ fig4_ablation saved")


def fig5_chain_length_dist(data_dir: Path, output_dir: Path) -> None:
    """Distribution of chain lengths per split."""
    splits = ["train", "val", "test_systematicity", "test_productivity", "test_substitutability"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for split in splits:
        f = data_dir / f"{split}.jsonl"
        if not f.exists():
            continue
        lengths = []
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            lengths.append(len(d["expected_chain"]))
        ax.hist(lengths, bins=range(1, 8), alpha=0.5, label=split)

    ax.set_xlabel("Tool Chain Length")
    ax.set_ylabel("Number of Tasks")
    ax.set_title("Chain Length Distribution per Split")
    ax.legend()
    ax.set_xticks(range(1, 7))

    fig.tight_layout()
    fig.savefig(output_dir / "fig5_chain_length_dist.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "fig5_chain_length_dist.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ fig5_chain_length_dist saved")


def main() -> None:
    results_dir = Path(__file__).parent.parent / "results"
    data_dir = Path(__file__).parent.parent / "data" / "generated"
    figures_dir = Path(__file__).parent.parent / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    summaries = load_all_summaries(results_dir)

    print(f"Found {len(summaries)} agent summaries")
    print("Generating figures...")
    fig1_cgg_bar(summaries, figures_dir)
    fig2_metrics_heatmap(summaries, figures_dir)
    fig3_error_breakdown(results_dir, figures_dir)
    fig4_ablation(results_dir, figures_dir)
    fig5_chain_length_dist(data_dir, figures_dir)
    print(f"\n✓ All figures saved to {figures_dir}")


if __name__ == "__main__":
    main()
