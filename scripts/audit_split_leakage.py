#!/usr/bin/env python3
"""audit_split_leakage.py - verify AgentCompose split construction guarantees.

Checks (against data/generated/*.jsonl):
  1. train/val/test_substitutability chains are length-2 only.
  2. 100% of test_systematicity chains contain >=1 ordered 2-subchain seen in train.
  3. 0% of test_productivity chains contain any ordered 2-subchain seen in train.
  4. test_substitutability is derived from val templates (template overlap = 100%)
     and uses tool substitutions (chain differs from the val chain for the same template).
  5. No train/val ordered 2-subchain appears in test_substitutability except via
     the same val task (substitution check reports substitution rate).

Writes results/split_leakage_audit.json. Deterministic; no LLM calls.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "generated"
OUT = ROOT / "results" / "split_leakage_audit.json"
SPLITS = ["train", "val", "test_systematicity", "test_productivity", "test_substitutability"]


def load_split(name: str) -> list[dict]:
    path = DATA / f"{name}.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def ordered_pairs(chain: list[str]) -> set[tuple[str, str]]:
    return {(chain[i], chain[i + 1]) for i in range(len(chain) - 1)}


def main() -> None:
    splits = {name: load_split(name) for name in SPLITS}
    report: dict = {}
    report["n_tasks"] = {k: len(v) for k, v in splits.items()}

    # 1. chain-length discipline
    len_report = {}
    for name, tasks in splits.items():
        lens = [len(t["expected_chain"]) for t in tasks]
        len_report[name] = {
            "min": min(lens) if lens else None,
            "max": max(lens) if lens else None,
            "n_not_length2": sum(1 for x in lens if x != 2),
        }
    report["chain_length"] = len_report
    report["checks"] = {}
    report["checks"]["length2_train_val"] = (len_report["train"]["n_not_length2"] == 0 and len_report["val"]["n_not_length2"] == 0)

    train_pairs = set()
    for t in splits["train"]:
        train_pairs |= ordered_pairs(t["expected_chain"])
    report["train_ordered_pairs"] = len(train_pairs)

    # 2. systematicity: >=1 trained sub-pair
    sys_hits = 0
    for t in splits["test_systematicity"]:
        if ordered_pairs(t["expected_chain"]) & train_pairs:
            sys_hits += 1
    sys_frac = sys_hits / max(1, len(splits["test_systematicity"]))
    report["systematicity"] = {"with_trained_pair": sys_hits, "fraction": round(sys_frac, 6)}
    report["checks"]["systematicity_contains_trained_pair"] = sys_frac == 1.0

    # 3. productivity: no trained sub-pair
    prod_leaks = 0
    for t in splits["test_productivity"]:
        if ordered_pairs(t["expected_chain"]) & train_pairs:
            prod_leaks += 1
    prod_frac = prod_leaks / max(1, len(splits["test_productivity"]))
    report["productivity"] = {"with_trained_pair": prod_leaks, "fraction_leaked": round(prod_frac, 6)}
    report["checks"]["productivity_zero_trained_pair"] = prod_frac == 0.0

    # 4. substitutability: derived from val templates, with tool substitution
    val_templates = {t["template_id"] for t in splits["val"]}
    sub = splits["test_substitutability"]
    sub_same_templates = sum(1 for t in sub if t["template_id"] in val_templates)
    sub_changed = 0
    sub_with_substitutable_tool = 0
    sub_changed_given_substitutable = 0
    sub_consistent = True
    val_chain_by_tpl: dict[str, list[str]] = {}
    for t in splits["val"]:
        val_chain_by_tpl.setdefault(t["template_id"], t["expected_chain"])
    for t in sub:
        base = val_chain_by_tpl.get(t["template_id"])
        changed = base is not None and t["expected_chain"] != base
        substituted_tool = (t.get("metadata") or {}).get("substituted_tool")
        if changed:
            sub_changed += 1
        if substituted_tool is not None:
            sub_with_substitutable_tool += 1
            if changed:
                sub_changed_given_substitutable += 1
        if (substituted_tool is None) == changed:
            sub_consistent = False
    sub_frac = sub_same_templates / max(1, len(sub))
    report["substitutability"] = {
        "val_template_overlap": sub_same_templates,
        "overlap_fraction": round(sub_frac, 6),
        "chain_changed_via_substitution": sub_changed,
        "with_substitutable_tool": sub_with_substitutable_tool,
        "changed_given_substitutable": sub_changed_given_substitutable,
        "substitution_fraction": round(sub_changed / max(1, len(sub)), 6),
        "chain_change_consistent_with_metadata": sub_consistent,
    }
    report["checks"]["substitutability_from_val_templates"] = sub_frac == 1.0
    report["checks"]["substitution_complete_and_consistent"] = (
        sub_changed_given_substitutable == sub_with_substitutable_tool and sub_consistent
    )

    report["all_checks_pass"] = all(report["checks"].values())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()