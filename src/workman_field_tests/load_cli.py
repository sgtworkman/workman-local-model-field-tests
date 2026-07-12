from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .core import Endpoint
from .io import atomic_write_json
from .performance import run_concurrency_sweep


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded streaming concurrency sweep.")
    parser.add_argument("--base-url", default=os.getenv("LOCAL_MODEL_BASE_URL", "http://127.0.0.1:8080/v1"))
    parser.add_argument("--api-key", default=os.getenv("LOCAL_MODEL_API_KEY", ""))
    parser.add_argument("--endpoint-label", default="local")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="Write a concise technical explanation of reliable local-model benchmarking.")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--levels", default="1,2,4")
    parser.add_argument("--requests-per-worker", type=int, default=2)
    parser.add_argument("--request-rate", type=float, default=0, help="Requests/second; 0 means a bounded burst.")
    parser.add_argument("--no-think", action="store_true")
    parser.add_argument("--acknowledge-high-load", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    levels = sorted(set(int(value) for value in args.levels.split(",") if value.strip()))
    if not levels or min(levels) < 1:
        raise SystemExit("--levels requires positive comma-separated integers")
    if max(levels) > 8 and not args.acknowledge_high_load:
        raise SystemExit("Concurrency above 8 requires --acknowledge-high-load")
    if args.requests_per_worker < 1:
        raise SystemExit("--requests-per-worker must be positive")
    result = run_concurrency_sweep(
        endpoint=Endpoint(args.base_url, args.api_key, args.endpoint_label),
        model=args.model,
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
        no_think=args.no_think,
        levels=levels,
        requests_per_worker=args.requests_per_worker,
        request_rate=args.request_rate,
        progress=lambda message: print(message, file=sys.stderr, flush=True),
    )
    atomic_write_json(args.output, result)
    summary = [
        {
            "concurrency": run["concurrency"],
            "success_rate": run["success_rate"],
            "aggregate_output_tokens_per_second": run["aggregate_output_tokens_per_second"],
            "ttft_p50_seconds": run["ttft_p50_seconds"],
        }
        for run in result["levels"]
    ]
    print(json.dumps(summary, sort_keys=True))
    return 0 if all(run["success_rate"] == 1.0 for run in result["levels"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
