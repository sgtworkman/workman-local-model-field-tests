from __future__ import annotations

import concurrent.futures
import json
import socket
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .core import Endpoint, NO_THINK_CONTROLS, percentile, utc_now
from .privacy import redact_text


@dataclass(frozen=True)
class StreamMeasurement:
    request_id: int
    success: bool
    intended_send_offset_seconds: float
    dispatch_delay_seconds: float
    ttft_seconds: float | None
    e2e_seconds: float | None
    tpot_seconds: float | None
    decode_tokens_per_second: float | None
    completion_tokens: int | None
    streamed_content_event_count: int
    reasoning_leak: bool
    failure: str | None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _delta_text(delta: dict[str, Any]) -> str:
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return ""


def stream_chat(
    *,
    endpoint: Endpoint,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
    no_think: bool,
    request_id: int,
    intended_send: float,
    run_started: float,
) -> StreamMeasurement:
    now = time.perf_counter()
    if intended_send > now:
        time.sleep(intended_send - now)
    actual_send = time.perf_counter()
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if no_think:
        payload.update(NO_THINK_CONTROLS)
    headers = {"Content-Type": "application/json"}
    if endpoint.api_key:
        headers["Authorization"] = f"Bearer {endpoint.api_key}"
    request = urllib.request.Request(
        endpoint.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    first_content: float | None = None
    last_content: float | None = None
    usage_tokens: int | None = None
    content_events = 0
    reasoning_leak = False
    saw_done = False
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    saw_done = True
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    return _failed_measurement(request_id, intended_send, actual_send, run_started, "malformed_sse")
                usage = event.get("usage") or {}
                if isinstance(usage.get("completion_tokens"), int):
                    usage_tokens = usage["completion_tokens"]
                for choice in event.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("reasoning") or delta.get("thinking") or delta.get("reasoning_content"):
                        reasoning_leak = True
                    if _delta_text(delta):
                        observed = time.perf_counter()
                        first_content = first_content or observed
                        last_content = observed
                        content_events += 1
    except urllib.error.HTTPError as exc:
        detail = redact_text(exc.read(1024).decode("utf-8", errors="replace"))
        return _failed_measurement(request_id, intended_send, actual_send, run_started, f"http_{exc.code}:{detail[:160]}")
    except Exception as exc:
        failure = "timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else f"{type(exc).__name__}:{redact_text(str(exc))[:160]}"
        return _failed_measurement(request_id, intended_send, actual_send, run_started, failure)

    finished = time.perf_counter()
    if reasoning_leak:
        return _failed_measurement(request_id, intended_send, actual_send, run_started, "reasoning_leak", reasoning_leak=True)
    if not saw_done:
        return _failed_measurement(request_id, intended_send, actual_send, run_started, "incomplete_stream")
    if first_content is None or last_content is None:
        return _failed_measurement(request_id, intended_send, actual_send, run_started, "empty_stream")
    failure = "missing_usage" if usage_tokens is None else None
    decode_seconds = max(last_content - first_content, 0)
    tpot = (
        decode_seconds / max(usage_tokens - 1, 1)
        if usage_tokens is not None
        else None
    )
    decode_rate = (
        usage_tokens / decode_seconds
        if usage_tokens is not None and decode_seconds > 0
        else None
    )
    return StreamMeasurement(
        request_id=request_id,
        success=failure is None,
        intended_send_offset_seconds=round(intended_send - run_started, 6),
        dispatch_delay_seconds=round(max(0, actual_send - intended_send), 6),
        ttft_seconds=round(first_content - actual_send, 6),
        e2e_seconds=round(finished - actual_send, 6),
        tpot_seconds=round(tpot, 8) if tpot is not None else None,
        decode_tokens_per_second=round(decode_rate, 3) if decode_rate is not None else None,
        completion_tokens=usage_tokens,
        streamed_content_event_count=content_events,
        reasoning_leak=reasoning_leak,
        failure=failure,
    )


def _failed_measurement(
    request_id: int,
    intended_send: float,
    actual_send: float,
    run_started: float,
    failure: str,
    reasoning_leak: bool = False,
) -> StreamMeasurement:
    return StreamMeasurement(
        request_id=request_id,
        success=False,
        intended_send_offset_seconds=round(intended_send - run_started, 6),
        dispatch_delay_seconds=round(max(0, actual_send - intended_send), 6),
        ttft_seconds=None,
        e2e_seconds=round(time.perf_counter() - actual_send, 6),
        tpot_seconds=None,
        decode_tokens_per_second=None,
        completion_tokens=None,
        streamed_content_event_count=0,
        reasoning_leak=reasoning_leak,
        failure=failure,
    )


def run_load_level(
    *,
    endpoint: Endpoint,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
    no_think: bool,
    concurrency: int,
    request_count: int,
    request_rate: float,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if concurrency < 1 or request_count < 1:
        raise ValueError("concurrency and request_count must be positive")
    if request_rate < 0:
        raise ValueError("request_rate must be >= 0")
    run_started = time.perf_counter()
    intended = [
        run_started if request_rate == 0 else run_started + index / request_rate
        for index in range(request_count)
    ]
    rows: list[StreamMeasurement] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                stream_chat,
                endpoint=endpoint,
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                timeout=timeout,
                no_think=no_think,
                request_id=index,
                intended_send=intended[index],
                run_started=run_started,
            )
            for index in range(request_count)
        ]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            if progress:
                progress(f"request={row.request_id} success={row.success} failure={row.failure or 'none'}")
    wall_seconds = time.perf_counter() - run_started
    rows.sort(key=lambda row: row.request_id)
    successful = [row for row in rows if row.success]
    completion_tokens = sum(row.completion_tokens or 0 for row in successful)
    ttfts = [row.ttft_seconds for row in successful if row.ttft_seconds is not None]
    tpots = [row.tpot_seconds for row in successful if row.tpot_seconds is not None]
    e2es = [row.e2e_seconds for row in successful if row.e2e_seconds is not None]
    dispatch = [row.dispatch_delay_seconds for row in rows]
    return {
        "concurrency": concurrency,
        "request_count": request_count,
        "request_rate": request_rate,
        "load_mode": "burst" if request_rate == 0 else "open_loop",
        "wall_seconds": round(wall_seconds, 6),
        "success_count": len(successful),
        "success_rate": round(len(successful) / len(rows), 6),
        "request_throughput_per_second": round(len(rows) / wall_seconds, 3),
        "aggregate_output_tokens_per_second": round(completion_tokens / wall_seconds, 3),
        "ttft_p50_seconds": _rounded_percentile(ttfts, 0.50),
        "ttft_p95_seconds": _rounded_percentile(ttfts, 0.95, 20),
        "tpot_p50_seconds": _rounded_percentile(tpots, 0.50),
        "e2e_p50_seconds": _rounded_percentile(e2es, 0.50),
        "dispatch_delay_p95_seconds": _rounded_percentile(dispatch, 0.95, 20),
        "sample_n": len(rows),
        "rows": [row.as_dict() for row in rows],
    }


def _rounded_percentile(values: list[float], fraction: float, min_samples: int = 1) -> float | None:
    value = percentile(values, fraction, min_samples=min_samples)
    return round(value, 6) if value is not None else None


def run_concurrency_sweep(
    *,
    endpoint: Endpoint,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
    no_think: bool,
    levels: list[int],
    requests_per_worker: int,
    request_rate: float,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    runs = []
    for level in levels:
        if progress:
            progress(f"START concurrency={level}")
        runs.append(
            run_load_level(
                endpoint=endpoint,
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                timeout=timeout,
                no_think=no_think,
                concurrency=level,
                request_count=level * requests_per_worker,
                request_rate=request_rate,
                progress=progress,
            )
        )
    baseline_rates = [
        row["decode_tokens_per_second"]
        for row in runs[0]["rows"]
        if row.get("decode_tokens_per_second") is not None
    ] if runs and runs[0]["concurrency"] == 1 else []
    baseline = statistics.median(baseline_rates) if baseline_rates else None
    for run in runs:
        run["concurrency_efficiency"] = (
            round(run["aggregate_output_tokens_per_second"] / (run["concurrency"] * baseline), 6)
            if baseline and run["concurrency"]
            else None
        )
    return {
        "schema_version": "workman-performance.v0.1",
        "created_utc": utc_now(),
        "endpoint_label": endpoint.label,
        "model": model,
        "adapter": "openai-compatible-streaming-chat-completions",
        "no_think_controls": no_think,
        "max_tokens": max_tokens,
        "requests_per_worker": requests_per_worker,
        "levels": runs,
    }
