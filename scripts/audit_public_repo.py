#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
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

BINARY_SUFFIXES = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".webp",
}


def tracked_files() -> list[Path]:
    try:
        # Include untracked, non-ignored release candidates. Auditing only the
        # index can miss a leak in a new file immediately before commit.
        output = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
        )
        return [ROOT / line for line in output.splitlines() if line]
    except subprocess.CalledProcessError:
        return [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]


@lru_cache(maxsize=1)
def changed_worktree_paths() -> set[str]:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all", "-z"],
            cwd=ROOT,
        )
    except subprocess.CalledProcessError:
        return set()
    changed: set[str] = set()
    for raw_entry in output.split(b"\0"):
        if len(raw_entry) < 4:
            continue
        path = raw_entry[3:].decode("utf-8", errors="surrogateescape")
        if path:
            changed.add(path)
    return changed


def read_audit_text(path: Path) -> str:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.read_text(encoding="utf-8")
    if relative not in changed_worktree_paths():
        completed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return completed.stdout
    return path.read_text(encoding="utf-8")


def audit_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if path in SKIP or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = read_audit_text(path)
        except (FileNotFoundError, UnicodeDecodeError):
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
