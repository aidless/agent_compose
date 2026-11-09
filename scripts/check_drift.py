"""Offline drift check. No API key and no network.

Usage:
    python scripts/check_drift.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_drift import (
    test_ci_workflow_does_not_call_live_models,
    test_dataset_fingerprint_matches_manifest,
    test_deepseek_summary_files_stay_partial,
    test_live_aggregate_matches_pin,
    test_missing_split_is_not_a_zero_gap,
    test_package_version_is_alpha,
    test_readme_has_no_static_count_badges,
    test_readme_status_and_observed_block,
    test_statistical_tests_file_is_not_strict_json,
    test_template_recompute_matches_pin,
    test_test_function_count_matches_manifest,
    test_tool_inventory_matches_manifest,
)


def main() -> None:
    checks = [
        test_tool_inventory_matches_manifest,
        test_dataset_fingerprint_matches_manifest,
        test_readme_has_no_static_count_badges,
        test_readme_status_and_observed_block,
        test_template_recompute_matches_pin,
        test_live_aggregate_matches_pin,
        test_deepseek_summary_files_stay_partial,
        test_test_function_count_matches_manifest,
        test_package_version_is_alpha,
        test_statistical_tests_file_is_not_strict_json,
        test_missing_split_is_not_a_zero_gap,
        test_ci_workflow_does_not_call_live_models,
    ]
    for check in checks:
        check()
        print(f"ok {check.__name__}")
    print("offline drift checks passed")


if __name__ == "__main__":
    main()
