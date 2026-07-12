#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workman_field_tests.admission import validate_result


def main() -> int:
    scenario = ROOT / "scenarios" / "public-22-check.json"
    failures: dict[str, list[str]] = {}
    for path in sorted((ROOT / "results" / "community").glob("**/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures[str(path.relative_to(ROOT))] = [f"invalid_json:{type(exc).__name__}"]
            continue
        issues = validate_result(data, scenario, verify_commit=True)
        if issues:
            failures[str(path.relative_to(ROOT))] = issues
    print(json.dumps({"status": "PASS" if not failures else "FAIL", "failures": failures}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
