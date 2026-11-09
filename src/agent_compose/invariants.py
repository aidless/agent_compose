"""Offline invariants for AgentCompose.

These checks pin the tool library and the seed-42 task generator. They do not
call a model API and they do not treat committed score files as a leaderboard.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from agent_compose.agents.chain_aware import ChainAwareAgent
from agent_compose.agents.native_fc import NativeFCAgent
from agent_compose.agents.plan_execute import PlanExecuteAgent
from agent_compose.agents.react import ReActAgent
from agent_compose.agents.reflexion import ReflexionAgent
from agent_compose.env.simulator import ToolSimulator
from agent_compose.eval.metrics import Evaluator
from agent_compose.eval.runner import evaluate_split
from agent_compose.generator.tasks import TaskGenerator
from agent_compose.tools import ToolLibrary

SPLIT_ORDER = (
    "train",
    "val",
    "test_systematicity",
    "test_productivity",
    "test_substitutability",
)
EVAL_SPLITS = (
    "val",
    "test_systematicity",
    "test_productivity",
    "test_substitutability",
)
TEMPLATE_AGENTS = ("react", "native_fc", "reflexion", "plan_execute", "chain_aware")
LIVE_AGENTS = ("deepseek_react", "deepseek_fc")

# Recompute stamp. The date is the day this pin was produced in this workspace.
# It is not a claim about when the historical summary files were written.
RECOMPUTE_DATE = "2026-11-09"
RECOMPUTE_SEED = 42
RECOMPUTE_FAILURE_RATE = 0.0


def repo_root() -> Path:
    """Return the repository root (parent of ``src``)."""
    return Path(__file__).resolve().parents[2]


def display_path(path: Path, root: Path | None = None) -> str:
    """Render ``path`` relative to the repo when possible.

    Host-specific absolute paths are not useful in logs that get copied around.
    Paths outside the repo fall back to the file name.
    """
    path = Path(path)
    root = repo_root() if root is None else Path(root)
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    """Load ``benchmark_manifest.json``."""
    root = repo_root() if root is None else Path(root)
    return json.loads((root / "benchmark_manifest.json").read_text(encoding="utf-8"))


def tool_inventory(root: Path | None = None) -> dict[str, Any]:
    """Count on-disk tool schemas. Files starting with ``_`` are metadata."""
    root = repo_root() if root is None else Path(root)
    library = ToolLibrary(root / "tools")
    names = sorted(tool.name for tool in library.all_tools)
    domains = sorted({tool.domain for tool in library.all_tools})
    meta_path = root / "tools" / "_equivalence.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    listed = [name for group in meta["tools_by_domain"].values() for name in group]
    return {
        "n_tools": len(names),
        "names": names,
        "n_domains": len(domains),
        "domains": domains,
        "n_equivalence_groups": len(library.equivalence_groups),
        "meta_total_tools": meta["_meta"]["total_tools"],
        "listed_names": listed,
    }


def dataset_fingerprint(root: Path | None = None, seed: int = RECOMPUTE_SEED) -> dict[str, Any]:
    """Regenerate the seed-42 dataset and hash a canonical record per task.

    The JSONL files are gitignored. This hash is the committed stand-in.
    """
    root = repo_root() if root is None else Path(root)
    generator = TaskGenerator(root / "templates" / "task_templates.yaml", seed=seed)
    splits = generator.generate_all()
    sizes = {name: len(splits[name]) for name in SPLIT_ORDER}
    digest = hashlib.sha256()
    for split_name in SPLIT_ORDER:
        for task in splits[split_name]:
            record = {
                "expected_chain": task.expected_chain,
                "metadata": task.metadata,
                "natural_language": task.natural_language,
                "parameters": task.parameters,
                "split": split_name,
                "task_id": task.task_id,
                "template_id": task.template_id,
            }
            digest.update(json.dumps(record, ensure_ascii=False, sort_keys=True).encode())
            digest.update(b"\n")
    return {
        "seed": seed,
        "n_templates": len(generator._templates),
        "sizes": sizes,
        "n_tasks": sum(sizes.values()),
        "sha256": digest.hexdigest(),
        "splits": splits,
    }


def count_test_functions(root: Path | None = None) -> int:
    """Count top-level ``test_*`` functions under ``tests/``.

    The suite does not use ``pytest.mark.parametrize``, so this matches
    pytest's collected count.
    """
    root = repo_root() if root is None else Path(root)
    total = 0
    for path in sorted((root / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                total += 1
    return total


def _agent_factory(name: str, library: ToolLibrary) -> Any:
    classes = {
        "react": ReActAgent,
        "native_fc": NativeFCAgent,
        "reflexion": ReflexionAgent,
        "plan_execute": PlanExecuteAgent,
        "chain_aware": ChainAwareAgent,
    }
    return classes[name](library, max_steps=10, use_oracle=False)


def recompute_template_agents(root: Path | None = None) -> dict[str, Any]:
    """Re-evaluate the five heuristic agents on a fresh seed-42 dataset.

    This is a simulator run. It is not a live model evaluation.
    """
    root = repo_root() if root is None else Path(root)
    generated = dataset_fingerprint(root, seed=RECOMPUTE_SEED)
    splits = generated["splits"]
    library = ToolLibrary(root / "tools")
    evaluator = Evaluator()
    agents: dict[str, Any] = {}
    mismatches: list[dict[str, Any]] = []
    for name in TEMPLATE_AGENTS:
        agent = _agent_factory(name, library)
        simulator = ToolSimulator(library, failure_rate=RECOMPUTE_FAILURE_RATE, seed=RECOMPUTE_SEED)
        if name == "chain_aware":
            agent.train_on(splits["train"])
        fresh: dict[str, Any] = {}
        for split_name in EVAL_SPLITS:
            metrics, _traces = evaluate_split(
                agent,
                simulator,
                splits[split_name],
                split_name,
                library=library,
            )
            aggregate = evaluator.aggregate(metrics)
            fresh[split_name] = {
                "aba": aggregate.aba,
                "coc": aggregate.coc,
                "n": aggregate.n_tasks,
                "tca": aggregate.tca,
                "tsr": aggregate.tsr,
            }
        committed_path = root / "results" / f"{name}_summary.json"
        committed = json.loads(committed_path.read_text(encoding="utf-8"))
        for split_name in EVAL_SPLITS:
            for metric in ("tsr", "tca", "coc", "aba", "n"):
                old = committed[split_name][metric]
                new = fresh[split_name][metric]
                if abs(float(old) - float(new)) > 1e-12:
                    mismatches.append(
                        {
                            "agent": name,
                            "committed": old,
                            "metric": metric,
                            "recompute": new,
                            "split": split_name,
                        }
                    )
        agents[name] = fresh
    mismatches.sort(key=lambda row: (row["agent"], row["split"], row["metric"]))
    return {
        "agents": agents,
        "mismatches_vs_committed_summaries": mismatches,
        "provenance": {
            "chain_aware_equiv_detector": True,
            "chain_aware_trained_on": "train split from TaskGenerator seed 42",
            "date": RECOMPUTE_DATE,
            "equiv_scoring": True,
            "failure_rate": RECOMPUTE_FAILURE_RATE,
            "kind": "simulator-heuristic-recompute",
            "model": "none",
            "note": (
                "OBSERVED recompute of the heuristic agents against the current "
                "generator and scorer. Historical results/*_summary.json files do "
                "not record a date or a seed. Where the two disagree, neither "
                "number is a live model score."
            ),
            "seed": RECOMPUTE_SEED,
            "status": "OBSERVED",
        },
    }


def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
    return sum(float(row[key]) for row in rows) / len(rows)


def aggregate_committed_live(root: Path | None = None) -> dict[str, Any]:
    """Mean the task metrics stored in the committed DeepSeek per-split files.

    The files do not record model id, date, seed, temperature, or prompt hash.
    Those fields stay UNKNOWN. This function does not call an API.
    """
    root = repo_root() if root is None else Path(root)
    agents: dict[str, Any] = {}
    for agent in LIVE_AGENTS:
        splits: dict[str, Any] = {}
        for split_name in EVAL_SPLITS:
            path = root / "results" / f"{agent}_{split_name}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            rows = data["task_metrics"]
            splits[split_name] = {
                "aba": _mean_metric(rows, "aba"),
                "agent_field": data.get("agent"),
                "coc": _mean_metric(rows, "coc"),
                "n": len(rows),
                "tca": _mean_metric(rows, "tca"),
                "tsr": _mean_metric(rows, "tsr"),
            }
        agents[agent] = splits
    return {
        "agents": agents,
        "provenance": {
            "date": "UNKNOWN",
            "kind": "committed-task-metrics-mean",
            "model": "UNKNOWN",
            "note": (
                "OBSERVED means of task_metrics in the committed per-split JSON. "
                "Those files do not record model, date, seed, temperature, or "
                "prompt hash. llm_react.py names deepseek-v4-flash as a client "
                "default; that string is not evidence about these files. "
                "The matching *_summary.json files are partial and are not this table."
            ),
            "seed": "UNKNOWN",
            "status": "OBSERVED",
        },
    }


def _fmt(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return format(float(value), ".12g")


def render_observed_section(root: Path | None = None) -> str:
    """Markdown block the README must contain verbatim."""
    root = repo_root() if root is None else Path(root)
    manifest = load_manifest(root)
    sizes = manifest["splits"]
    inventory = tool_inventory(root)
    lines = [
        "Pinned by `benchmark_manifest.json` and `tests/test_drift.py`:",
        (
            f"{inventory['n_tools']} JSON tool schemas, "
            f"{manifest['n_templates']} templates, "
            f"{inventory['n_domains']} domains, "
            f"{inventory['n_equivalence_groups']} author-declared equivalence groups, "
            f"seed {manifest['seed']}."
        ),
        (
            "Split sizes: "
            + ", ".join(f"{name} {sizes[name]}" for name in SPLIT_ORDER)
            + f" ({manifest['n_tasks']} tasks)."
        ),
        f"Dataset SHA-256: `{manifest['dataset_sha256']}`.",
        "The JSONL is gitignored. A fresh clone regenerates it; it is not a committed artifact.",
        "",
        "### Simulator snapshots",
        "",
        (
            "Committed `results/{agent}_summary.json` files do not store a model, date, or seed. "
            "Provenance of those files: **UNKNOWN**. They are historical snapshots."
        ),
        (
            f"`results/recompute_seed42.json` is an OBSERVED recompute dated {RECOMPUTE_DATE} "
            "with seed 42, failure_rate 0, equivalence-tolerant scoring on, and ChainAware's "
            "equivalence detector on. Model: none (heuristic agents in the JSON simulator)."
        ),
        "",
        "| Agent | Split | Committed TSR | Recompute TSR | N |",
        "|---|---|---:|---:|---:|",
    ]
    recompute = json.loads((root / "results" / "recompute_seed42.json").read_text(encoding="utf-8"))
    for agent in TEMPLATE_AGENTS:
        committed = json.loads(
            (root / "results" / f"{agent}_summary.json").read_text(encoding="utf-8")
        )
        for split_name in EVAL_SPLITS:
            old = committed[split_name]["tsr"]
            new = recompute["agents"][agent][split_name]["tsr"]
            n = committed[split_name]["n"]
            lines.append(f"| {agent} | {split_name} | {_fmt(old)} | {_fmt(new)} | {n} |")
    n_mismatch = len(recompute["mismatches_vs_committed_summaries"])
    lines.extend(
        [
            "",
            (
                f"The recompute differs from the committed summaries in {n_mismatch} "
                "metric cells (TSR, TCA, COC, ABA, or N). The full list is "
                "`mismatches_vs_committed_summaries` in `results/recompute_seed42.json`. "
                "Do not collapse the two columns into one leaderboard."
            ),
            "",
            "### Live LLM fragments",
            "",
            (
                "OBSERVED means of `task_metrics` in the committed per-split files. "
                "**model: UNKNOWN. date: UNKNOWN. seed: UNKNOWN.**"
            ),
            (
                "`deepseek_react_summary.json` contains only `val`. "
                "`deepseek_fc_summary.json` contains only `test_substitutability`. "
                "Those summary files are not a four-split result."
            ),
            "",
            "| File agent field | Split | N | TSR | TCA | COC | ABA |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    live = json.loads((root / "results" / "live_llm_observed.json").read_text(encoding="utf-8"))
    for agent in LIVE_AGENTS:
        for split_name in EVAL_SPLITS:
            row = live["agents"][agent][split_name]
            lines.append(
                "| {agent_field} | {split} | {n} | {tsr} | {tca} | {coc} | {aba} |".format(
                    agent_field=row["agent_field"],
                    split=split_name,
                    n=row["n"],
                    tsr=_fmt(row["tsr"]),
                    tca=_fmt(row["tca"]),
                    coc=_fmt(row["coc"]),
                    aba=_fmt(row["aba"]),
                )
            )
    lines.extend(
        [
            "",
            (
                "Each live split above has N=200 stored traces, not the full generated "
                "split (val 400, systematicity 600, productivity 600, substitutability 200). "
                "Substitutability is the only live split that covers its full generated size, "
                "and only by coincidence of that size being 200."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def cgg_or_none(summary: dict[str, Any], split_name: str) -> float | None:
    """Return val TSR minus ``split_name`` TSR, or None if either side is absent.

    Missing splits are not zeros. Plotting them as zero reports a gap that was
    not measured.
    """
    val = summary.get("val")
    held = summary.get(split_name)
    if not isinstance(val, dict) or not isinstance(held, dict):
        return None
    if "tsr" not in val or "tsr" not in held:
        return None
    return float(val["tsr"]) - float(held["tsr"])
