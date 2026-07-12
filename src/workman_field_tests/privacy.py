from __future__ import annotations

import ipaddress
import re


SENSITIVE_KEY_NAMES = {
    "apikey",
    "authorization",
    "baseurl",
    "endpointurl",
    "host",
    "hostname",
    "ip",
    "password",
    "secret",
    "token",
    "user",
    "username",
    "workingdirectory",
}

TOKEN_PATTERN = re.compile(
    r"(?:hf_|ghp_|gho_|github_pat_|glpat-|xox[baprs]-|sk[-_]|AKIA)"
    r"[A-Za-z0-9_\-]{8,}"
)
PERSONAL_PATH_PATTERN = re.compile(r"/(?:Users|home)/[^/\s]+/")
PRIVATE_HOST_PATTERN = re.compile(r"(?:[A-Za-z0-9_-]+\.local\b|[A-Za-z0-9_.-]+\.ts\.net\b|tailscale)", re.I)
IPV4_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
BRACKETED_IPV6_PATTERN = re.compile(r"\[([0-9A-Fa-f:]+)\]")
CGNAT = ipaddress.ip_network("100.64.0.0/10")


def normalize_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def is_sensitive_key(key: object) -> bool:
    return normalize_key(key) in SENSITIVE_KEY_NAMES


def is_sensitive_address(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if parsed.is_loopback:
        return False
    return bool(parsed.is_private or parsed.is_link_local or parsed.is_reserved or parsed in CGNAT)


def private_address_matches(text: str) -> list[str]:
    matches: list[str] = []
    for match in IPV4_PATTERN.finditer(text):
        candidate = match.group(0)
        if is_sensitive_address(candidate):
            matches.append(candidate)
    for match in BRACKETED_IPV6_PATTERN.finditer(text):
        candidate = match.group(1)
        if is_sensitive_address(candidate):
            matches.append(candidate)
    return sorted(set(matches))


def scan_text(text: str) -> list[str]:
    findings: list[str] = []
    if TOKEN_PATTERN.search(text):
        findings.append("credential_pattern")
    if PERSONAL_PATH_PATTERN.search(text):
        findings.append("personal_path")
    if PRIVATE_HOST_PATTERN.search(text):
        findings.append("private_hostname")
    if private_address_matches(text):
        findings.append("private_address")
    return findings


def redact_text(text: str) -> str:
    clean = TOKEN_PATTERN.sub("[REDACTED_CREDENTIAL]", text)
    clean = PERSONAL_PATH_PATTERN.sub("/[REDACTED_HOME]/", clean)
    clean = PRIVATE_HOST_PATTERN.sub("[REDACTED_HOST]", clean)
    for address in private_address_matches(clean):
        clean = clean.replace(address, "[REDACTED_PRIVATE_ADDRESS]")
    return clean
