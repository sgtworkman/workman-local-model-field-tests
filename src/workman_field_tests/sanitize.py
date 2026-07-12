from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .privacy import is_sensitive_key, redact_text, scan_text


def sanitize(value: Any, path: str = "$") -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, child in value.items():
            if is_sensitive_key(key):
                continue
            clean[key] = sanitize(child, f"{path}.{key}")
        return clean
    if isinstance(value, list):
        return [sanitize(child, f"{path}[]") for child in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def scan(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if is_sensitive_key(key):
                findings.append(f"{path}.{key}:sensitive_key")
            findings.extend(scan(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        findings.extend(f"{path}:{finding}" for finding in scan_text(value))
    return sorted(set(findings))


def main() -> int:
    p = argparse.ArgumentParser(description="Remove endpoint and credential-adjacent data from a result JSON file.")
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    clean = sanitize(data)
    remaining = scan(clean)
    if remaining:
        raise SystemExit("sanitized result still contains sensitive patterns: " + ", ".join(remaining))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(clean, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
