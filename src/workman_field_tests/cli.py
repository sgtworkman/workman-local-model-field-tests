from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .core import Endpoint, load_scenarios, run_battery


def parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description="Run reproducible field tests against an OpenAI-compatible local model.")
    p.add_argument("--base-url", default=os.getenv("LOCAL_MODEL_BASE_URL", "http://127.0.0.1:8080/v1"))
    p.add_argument("--api-key", default=os.getenv("LOCAL_MODEL_API_KEY", ""))
    p.add_argument("--endpoint-label", default="local")
    p.add_argument("--model", required=True)
    p.add_argument("--hardware", required=True)
    p.add_argument("--runtime", required=True)
    p.add_argument("--quantization", default="unspecified")
    p.add_argument("--scenarios", type=Path, default=root / "scenarios" / "public-22-check.json")
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--max-tokens", type=int, default=700)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-thinking", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")
    result = run_battery(
        endpoint=Endpoint(args.base_url, args.api_key, args.endpoint_label),
        model=args.model,
        scenarios=load_scenarios(args.scenarios),
        repeats=args.repeats,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
        hardware=args.hardware,
        runtime=args.runtime,
        quantization=args.quantization,
        no_think=not args.allow_thinking,
        progress=lambda message: print(message, file=sys.stderr, flush=True),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0 if result["summary"]["request_error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
