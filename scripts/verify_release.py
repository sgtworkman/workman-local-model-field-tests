#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SCENARIOS = ROOT / "scenarios" / "public-22-check.json"
QUALITY = ROOT / "results" / "verified" / "2026-07-12-nine-model-v2" / "quality"


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + existing if existing else "")
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def main() -> int:
    run([PYTHON, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([PYTHON, "scripts/audit_public_repo.py"])
    for artifact in sorted(QUALITY.glob("*.json")):
        run([
            PYTHON,
            "-m",
            "workman_field_tests.admission",
            str(artifact),
            "--scenarios",
            str(SCENARIOS),
            "--verify-commit",
        ])
    print("RELEASE_VERIFICATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
