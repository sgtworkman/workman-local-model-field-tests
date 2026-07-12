#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
sys.path.insert(0, str(ROOT / "src"))

from workman_field_tests.privacy import scan_text

SKIP = {
    SELF,
    ROOT / "src" / "workman_field_tests" / "sanitize.py",
    ROOT / "src" / "workman_field_tests" / "privacy.py",
}


def tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
        return [ROOT / line for line in output.splitlines() if line]
    except subprocess.CalledProcessError:
        return [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]


def audit_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if path in SKIP or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            display = str(path.relative_to(ROOT))
        except ValueError:
            display = path.name
        for line_number, line in enumerate(text.splitlines(), 1):
            for finding in scan_text(line):
                findings.append(f"{display}:{line_number}:{finding}")
    return findings


def main() -> int:
    findings = audit_files(tracked_files())
    if findings:
        print("PUBLIC_REPO_AUDIT FAIL")
        print("\n".join(findings))
        return 1
    print("PUBLIC_REPO_AUDIT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
