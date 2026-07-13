from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .sanitize import scan


REQUIRED = {
    "schema_version",
    "runner_commit",
    "scenario_sha256",
    "model",
    "serving_artifact",
    "model_revision",
    "runtime",
    "runtime_version",
    "hardware",
    "hardware_memory_gb",
    "os",
    "quantization",
    "context_limit",
    "sampling",
    "concurrency",
    "no_think_controls",
    "scenario_count",
    "repeats",
    "created_utc",
    "summary",
    "rows",
    "comparability_class",
}


def validate_result(data: dict[str, Any], scenario_path: Path | None = None, verify_commit: bool = False) -> list[str]:
    issues: list[str] = []
    missing = sorted(REQUIRED - set(data))
    issues.extend(f"missing:{key}" for key in missing)
    if data.get("schema_version") != "workman-field-tests.v2":
        issues.append("schema_version_must_be_v2")
    if data.get("comparability_class") != "quality/public-battery":
        issues.append("unsupported_comparability_class")
    if not re.fullmatch(r"[0-9a-f]{40}", str(data.get("runner_commit", ""))):
        issues.append("invalid_runner_commit")
    if not re.fullmatch(r"[0-9a-f]{64}", str(data.get("scenario_sha256", ""))):
        issues.append("invalid_scenario_sha256")
    if scenario_path and scenario_path.is_file():
        expected = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
        if data.get("scenario_sha256") != expected:
            issues.append("scenario_sha256_mismatch")
    if verify_commit and re.fullmatch(r"[0-9a-f]{40}", str(data.get("runner_commit", ""))):
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{data['runner_commit']}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            issues.append("runner_commit_not_in_history")
    summary = data.get("summary") or {}
    if not isinstance(summary, dict) or not {"passed", "total", "pass_rate", "latency_sample_n"}.issubset(summary):
        issues.append("invalid_summary")
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        issues.append("rows_required")
    else:
        identities: list[tuple[Any, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(f"invalid_row:{index}")
                continue
            identity = (row.get("scenario_id"), row.get("repeat"))
            if not isinstance(identity[0], str) or not identity[0] or not isinstance(identity[1], int):
                issues.append(f"invalid_row_identity:{index}")
            identities.append(identity)
        if len(identities) != len(set(identities)):
            issues.append("duplicate_scenario_repeat")

        scenario_count = data.get("scenario_count")
        repeats = data.get("repeats")
        if isinstance(scenario_count, int) and isinstance(repeats, int):
            if len(rows) != scenario_count * repeats:
                issues.append("row_count_mismatch")

        passed = sum(1 for row in rows if isinstance(row, dict) and row.get("passed") is True)
        if isinstance(summary, dict):
            if summary.get("total") != len(rows):
                issues.append("summary_total_mismatch")
            if summary.get("passed") != passed:
                issues.append("summary_passed_mismatch")
            expected_rate = passed / len(rows) if rows else 0.0
            try:
                actual_rate = float(summary.get("pass_rate"))
            except (TypeError, ValueError):
                actual_rate = -1.0
            if abs(actual_rate - expected_rate) > 0.000001:
                issues.append("summary_pass_rate_mismatch")
    if data.get("hardware_memory_gb") is not None and not isinstance(data.get("hardware_memory_gb"), (int, float)):
        issues.append("invalid_hardware_memory_gb")
    if data.get("context_limit") is not None and not isinstance(data.get("context_limit"), int):
        issues.append("invalid_context_limit")
    issues.extend(f"privacy:{finding}" for finding in scan(data))
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a v2 public-battery result for admission.")
    parser.add_argument("result", type=Path)
    parser.add_argument("--scenarios", type=Path, default=Path("scenarios/public-22-check.json"))
    parser.add_argument("--verify-commit", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    issues = validate_result(data, args.scenarios, verify_commit=args.verify_commit)
    print(json.dumps({"status": "PASS" if not issues else "FAIL", "issues": issues}, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
