"""Generate Critical Difference (CD) diagram from statistical_tests.json.

Standard CD diagram (Demsar 2006 style):
- Each agent placed on a horizontal number line by rank
- Agents not significantly different are connected by a horizontal bar

Usage:
    python scripts/make_cd_diagram.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def compute_cd_threshold(n_agents: int, n_datasets: int, alpha: float = 0.05) -> float:
    """Critical Difference threshold from Demsar 2006 Table 5.

    q_alpha values for Nemenyi test (two-tailed).
    """
    # q_alpha for k agents, alpha=0.05, from Demsar 2006
    q_table = {
        2: 1.960,
        3: 2.343,
        4: 2.569,
        5: 2.728,
        6: 2.850,
        7: 2.949,
        8: 3.031,
        9: 3.102,
        10: 3.164,
    }
    q_alpha = q_table.get(n_agents, 3.164)
    return q_alpha * np.sqrt(n_agents * (n_agents + 1) / (6 * n_datasets))


def find_cliques(ranks: list[int], cd: float) -> list[list[int]]:
    """Find groups of agents (by rank) that are within CD threshold (cliques).

    Returns list of lists of indices into `ranks`.
    """
    n = len(ranks)
    adj = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if abs(ranks[i] - ranks[j]) <= cd:
                adj[i].append(j)
                adj[j].append(i)
    # Find maximal cliques (simple greedy: groups of consecutive ranks within CD)
    cliques = []
    used = set()
    for i in range(n):
        if i in used:
            continue
        clique = [i]
        for j in range(i + 1, n):
            if j in used:
                continue
            if all(abs(ranks[k] - ranks[j]) <= cd for k in clique):
                clique.append(j)
        if len(clique) > 1:
            cliques.append(clique)
            used.update(clique)
    return cliques


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir", type=Path, default=Path(__file__).parent.parent / "results"
    )
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent.parent / "figures")
    parser.add_argument("--split", default="test_productivity")
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()

    stats_path = args.results_dir / "statistical_tests.json"
    data = json.loads(stats_path.read_text(encoding="utf-8"))
    cd_data = data.get("cd_data", {}).get(args.split, {})
    if not cd_data:
        print(f"No CD data for split {args.split}")
        return

    agents = cd_data["sorted_agents"]
    ranks = [cd_data["ranks"][a] for a in agents]
    means = [cd_data["means"][a] for a in agents]
    n_agents = len(agents)
    n_datasets = 600  # test_productivity size
    cd = compute_cd_threshold(n_agents, n_datasets, alpha=args.alpha)

    # Draw diagram
    fig, ax = plt.subplots(figsize=(10, 4.5))
    # Bottom: rank line
    ax.hlines(0, 0.5, n_agents + 0.5, color="black", linewidth=1)
    for i in range(1, n_agents + 1):
        ax.vlines(i, -0.05, 0.05, color="black", linewidth=0.8)

    # Agent labels (above)
    label_y = 0.4
    for i, (a, r, m) in enumerate(zip(agents, ranks, means)):
        ax.plot([r, r], [0.05, label_y - 0.15], color="gray", linewidth=0.5)
        ax.text(r, label_y, f"{a}\n({m:.3f})", ha="center", va="bottom", fontsize=9)

    # Cliques (horizontal bars)
    cliques = find_cliques(ranks, cd)
    bar_y = 1.2
    for k, clique in enumerate(cliques):
        r_min = min(ranks[i] for i in clique)
        r_max = max(ranks[i] for i in clique)
        ax.hlines(bar_y + k * 0.2, r_min, r_max, color="#9467bd", linewidth=4)

    # CD annotation
    ax.text(n_agents + 0.6, 0, f"CD={cd:.2f}", fontsize=10, va="center")
    ax.set_xlim(0.3, n_agents + 1.5)
    ax.set_ylim(-0.3, bar_y + len(cliques) * 0.2 + 0.3)
    ax.set_xlabel("Mean Rank (lower = better)")
    ax.set_title(f"Critical Difference Diagram — {args.split} (Nemenyi α={args.alpha})")
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    fig.tight_layout()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_dir / "fig6_cd_diagram.pdf", dpi=300, bbox_inches="tight")
    fig.savefig(args.output_dir / "fig6_cd_diagram.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✓ fig6_cd_diagram saved (CD={cd:.2f}, cliques={len(cliques)})")


if __name__ == "__main__":
    main()
