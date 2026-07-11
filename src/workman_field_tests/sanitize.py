from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {
    "api_key", "authorization", "base_url", "endpoint_url", "host", "hostname",
    "ip", "password", "secret", "token", "user", "username", "working_directory",
}
SENSITIVE_PATTERNS = [
    re.compile(r"(?:hf|gho|github_pat|sk)-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"(?:tailscale|\.local\b)", re.I),
]


def looks_private_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_private
    except ValueError:
        return False


def sanitize(value: Any, path: str = "$") -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, child in value.items():
            if key.lower() in SENSITIVE_KEYS:
                continue
            clean[key] = sanitize(child, f"{path}.{key}")
        return clean
    if isinstance(value, list):
        return [sanitize(child, f"{path}[]") for child in value]
    if isinstance(value, str):
        if looks_private_ip(value.strip()):
            return "[REDACTED_PRIVATE_ADDRESS]"
        cleaned = value
        for pattern in SENSITIVE_PATTERNS:
            cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned
    return value


def scan(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SENSITIVE_KEYS:
                findings.append(f"{path}.{key}:sensitive_key")
            findings.extend(scan(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        if looks_private_ip(value.strip()):
            findings.append(f"{path}:private_address")
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path}:sensitive_pattern")
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
