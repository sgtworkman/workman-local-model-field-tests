#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
SKIP = {
    SELF,
    ROOT / "src" / "workman_field_tests" / "sanitize.py",
}
PATTERNS = {
    "credential": re.compile(r"(?:hf|gho|github_pat|sk)-[A-Za-z0-9_-]{12,}"),
    "personal_path": re.compile(r"/Users/[^/\s]+/"),
    "tailscale_or_local_hostname": re.compile(r"(?:tailscale|[A-Za-z0-9_-]+\.local\b)", re.I),
    "cgnat_or_private_100_address": re.compile(r"\b100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])(?:\.[0-9]{1,3}){2}\b"),
}


def tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
        return [ROOT / line for line in output.splitlines() if line]
    except subprocess.CalledProcessError:
        return [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if path in SKIP or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}:{name}")
    if findings:
        print("PUBLIC_REPO_AUDIT FAIL")
        print("\n".join(findings))
        return 1
    print("PUBLIC_REPO_AUDIT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
