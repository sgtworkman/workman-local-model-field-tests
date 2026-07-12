from __future__ import annotations

import json
import re
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .privacy import redact_text


NO_THINK_CONTROLS = {
    "reasoning_effort": "none",
    "include_reasoning": False,
    "chat_template_kwargs": {"enable_thinking": False},
}


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    api_key: str
    label: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenario file must contain a non-empty scenarios list")
    ids = [row.get("id") for row in scenarios]
    if any(not isinstance(value, str) or not value for value in ids):
        raise ValueError("every scenario requires a non-empty string id")
    if len(ids) != len(set(ids)):
        raise ValueError("scenario ids must be unique")
    return scenarios


def extract_response(response: dict[str, Any]) -> tuple[str, bool, str]:
    choices = response.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    hidden = bool(
        message.get("reasoning")
        or message.get("thinking")
        or message.get("reasoning_content")
    )
    tool_calls = message.get("tool_calls") or []
    if not content and tool_calls:
        function = (tool_calls[0].get("function") or {}) if isinstance(tool_calls[0], dict) else {}
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                pass
        content = json.dumps({"name": function.get("name"), "arguments": arguments})
        return str(content), hidden, "native_tool_call"
    return str(content or ""), hidden, "content"


def extract_text(response: dict[str, Any]) -> tuple[str, bool]:
    text, hidden, _ = extract_response(response)
    return text, hidden


def post_chat(endpoint: Endpoint, payload: dict[str, Any], timeout: float) -> tuple[dict[str, Any], float]:
    url = endpoint.base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if endpoint.api_key:
        headers["Authorization"] = f"Bearer {endpoint.api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = redact_text(exc.read(2048).decode("utf-8", errors="replace"))
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    elapsed = time.perf_counter() - started
    return body, elapsed


def contains_term(text: str, term: object) -> bool:
    escaped = re.escape(str(term))
    return bool(re.search(rf"(?<!\w){escaped}(?!\w)", text, flags=re.I))


def evaluate(text: str, hidden_reasoning: bool, rule: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    normalized = text.strip()
    lower = normalized.lower()
    if not normalized:
        failures.append("empty_output")
    if hidden_reasoning or "<think>" in lower or "</think>" in lower:
        failures.append("reasoning_leak")
    kind = rule.get("type", "contains_all")
    if kind == "exact":
        if normalized != rule.get("value", ""):
            failures.append("exact_mismatch")
    elif kind == "contains_all":
        for term in rule.get("terms", []):
            if not contains_term(normalized, term):
                failures.append(f"missing:{term}")
    elif kind == "contains_any":
        terms = [str(term) for term in rule.get("terms", [])]
        if not any(contains_term(normalized, term) for term in terms):
            failures.append("missing_any:" + "|".join(terms))
    elif kind == "starts_with":
        value = str(rule.get("value", ""))
        if not re.match(rf"^\s*{re.escape(value)}(?=\W|$)", normalized, flags=re.I):
            failures.append(f"must_start_with:{value}")
        for term in rule.get("terms", []):
            if not contains_term(normalized, term):
                failures.append(f"missing:{term}")
    elif kind == "regex":
        pattern = str(rule.get("pattern", ""))
        if not pattern or not re.search(pattern, normalized):
            failures.append("regex_mismatch")
    elif kind == "json":
        if normalized.startswith("```"):
            failures.append("markdown_fence")
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError:
            failures.append("invalid_json")
        else:
            if not isinstance(parsed, dict):
                failures.append("json_not_object")
            else:
                expected = set(rule.get("required_keys", []))
                missing = sorted(expected - set(parsed))
                failures.extend(f"missing_key:{key}" for key in missing)
                for key, value in rule.get("equals", {}).items():
                    if parsed.get(key) != value:
                        failures.append(f"wrong_value:{key}")
    else:
        failures.append(f"unknown_rule:{kind}")

    for term in rule.get("forbidden", []):
        if contains_term(normalized, term):
            failures.append(f"forbidden:{term}")
    return not failures, failures


def percentile(values: list[float], fraction: float, min_samples: int = 1) -> float | None:
    if len(values) < min_samples:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_battery(
    *,
    endpoint: Endpoint,
    model: str,
    scenarios: list[dict[str, Any]],
    repeats: int,
    timeout: float,
    max_tokens: int,
    hardware: str,
    runtime: str,
    quantization: str,
    no_think: bool,
    provenance: dict[str, Any] | None = None,
    initial_rows: list[dict[str, Any]] | None = None,
    checkpoint: Callable[[list[dict[str, Any]]], None] | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = list(initial_rows or [])
    completed = {
        (row.get("scenario_id"), row.get("repeat"))
        for row in rows
        if row.get("scenario_id") and row.get("repeat") is not None
    }
    for scenario in scenarios:
        for repeat in range(1, repeats + 1):
            if (scenario["id"], repeat) in completed:
                if progress:
                    progress(f"SKIP {scenario['id']} repeat={repeat} reason=resume")
                continue
            if progress:
                progress(f"START {scenario['id']} repeat={repeat}")
            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": scenario.get("system", "Answer directly. Final answer only.")},
                    {"role": "user", "content": scenario["prompt"]},
                ],
                "temperature": 0,
                "max_tokens": max_tokens,
            }
            if no_think:
                payload.update(NO_THINK_CONTROLS)
            started = utc_now()
            try:
                response, elapsed = post_chat(endpoint, payload, timeout)
                text, hidden, response_kind = extract_response(response)
                passed, failures = evaluate(text, hidden, scenario["rule"])
                usage = response.get("usage") or {}
                completion_tokens = usage.get("completion_tokens")
                request_tok_s = (
                    float(completion_tokens) / elapsed
                    if isinstance(completion_tokens, (int, float)) and elapsed > 0
                    else None
                )
                row = {
                    "scenario_id": scenario["id"],
                    "repeat": repeat,
                    "started_utc": started,
                    "elapsed_seconds": round(elapsed, 6),
                    "completion_tokens": completion_tokens,
                    "request_tokens_per_second": round(request_tok_s, 3) if request_tok_s is not None else None,
                    "passed": passed,
                    "failures": failures,
                    "output": redact_text(text),
                    "response_model": response.get("model"),
                    "response_kind": response_kind,
                    "hidden_reasoning_present": hidden,
                }
            except Exception as exc:
                row = {
                    "scenario_id": scenario["id"],
                    "repeat": repeat,
                    "started_utc": started,
                    "elapsed_seconds": None,
                    "completion_tokens": None,
                    "request_tokens_per_second": None,
                    "passed": False,
                    "failures": ["request_error"],
                    "error": redact_text(f"{type(exc).__name__}: {exc}"),
                    "output": "",
                    "response_model": None,
                    "response_kind": "request_error",
                    "hidden_reasoning_present": False,
                }
            rows.append(row)
            if checkpoint:
                checkpoint(rows)
            if progress:
                progress(
                    f"DONE {scenario['id']} repeat={repeat} passed={row['passed']} "
                    f"elapsed={row.get('elapsed_seconds')} failures={','.join(row.get('failures', [])) or 'none'}"
                )

    speeds = [row["request_tokens_per_second"] for row in rows if row.get("request_tokens_per_second")]
    latencies = [row["elapsed_seconds"] for row in rows if row.get("elapsed_seconds") is not None]
    measured_rows = [
        row for row in rows
        if isinstance(row.get("completion_tokens"), (int, float))
        and isinstance(row.get("elapsed_seconds"), (int, float))
        and row["elapsed_seconds"] > 0
    ]
    total_tokens = sum(float(row["completion_tokens"]) for row in measured_rows)
    total_elapsed = sum(float(row["elapsed_seconds"]) for row in measured_rows)
    passed = sum(1 for row in rows if row["passed"])
    result = {
        "schema_version": "workman-field-tests.v2" if provenance else "workman-field-tests.v1.1",
        "created_utc": utc_now(),
        "endpoint_label": endpoint.label,
        "model": model,
        "serving_artifact": model,
        "hardware": hardware,
        "runtime": runtime,
        "quantization": quantization,
        "adapter": "openai-compatible-chat-completions",
        "no_think_controls": no_think,
        "scenario_count": len(scenarios),
        "repeats": repeats,
        "summary": {
            "passed": passed,
            "total": len(rows),
            "pass_rate": round(passed / len(rows), 6) if rows else 0,
            "median_request_tokens_per_second": round(statistics.median(speeds), 3) if speeds else None,
            "aggregate_request_tokens_per_second": round(total_tokens / total_elapsed, 3) if total_elapsed else None,
            "p50_latency_seconds": round(percentile(latencies, 0.50), 3) if latencies else None,
            "p95_latency_seconds": (
                round(value, 3)
                if (value := percentile(latencies, 0.95, min_samples=20)) is not None
                else None
            ),
            "latency_sample_n": len(latencies),
            "empty_output_count": sum(1 for row in rows if "empty_output" in row.get("failures", [])),
            "reasoning_leak_count": sum(1 for row in rows if "reasoning_leak" in row.get("failures", [])),
            "request_error_count": sum(1 for row in rows if "request_error" in row.get("failures", [])),
        },
        "rows": rows,
    }
    if provenance:
        result.update(provenance)
        result["sampling"] = {
            "temperature": 0,
            "top_p": 1,
            "seed": provenance.get("seed"),
            "max_tokens": max_tokens,
        }
        result["concurrency"] = 1
        result["comparability_class"] = "quality/public-battery"
    return result
