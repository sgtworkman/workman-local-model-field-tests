from __future__ import annotations

import argparse
import json
import os
import platform
import hashlib
import subprocess
import sys
from pathlib import Path

from .core import Endpoint, load_scenarios, run_battery
from .io import atomic_write_json


def exit_code_for_summary(summary: dict, min_pass_rate: float) -> int:
    if summary.get("request_error_count"):
        return 2
    if float(summary.get("pass_rate", 0)) < min_pass_rate:
        return 3
    return 0


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
    p.add_argument("--no-think", action="store_true", help="Send Qwen/vLLM no-think controls. Off by default for compatibility.")
    p.add_argument("--min-pass-rate", type=float, default=1.0, help="Exit 3 when quality pass rate is below this threshold.")
    p.add_argument("--admission-ready", action="store_true", help="Emit v2 provenance fields; requires the metadata flags below.")
    p.add_argument("--model-revision")
    p.add_argument("--runtime-version")
    p.add_argument("--hardware-memory-gb", type=float)
    p.add_argument("--os", dest="os_name")
    p.add_argument("--context-limit", type=int)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--resume", action="store_true", help="Resume completed scenario/repeat rows from the output checkpoint.")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")
    if not 0 <= args.min_pass_rate <= 1:
        raise SystemExit("--min-pass-rate must be between 0 and 1")
    provenance = None
    if args.admission_ready:
        required = {
            "model_revision": args.model_revision,
            "runtime_version": args.runtime_version,
            "hardware_memory_gb": args.hardware_memory_gb,
            "context_limit": args.context_limit,
        }
        missing = [key for key, value in required.items() if value in {None, ""}]
        if missing:
            raise SystemExit("--admission-ready requires: " + ", ".join(missing))
        try:
            runner_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            raise SystemExit("--admission-ready requires a git checkout with a resolvable HEAD")
        provenance = {
            "runner_commit": runner_commit,
            "scenario_sha256": hashlib.sha256(args.scenarios.read_bytes()).hexdigest(),
            "model_revision": args.model_revision,
            "runtime_version": args.runtime_version,
            "hardware_memory_gb": args.hardware_memory_gb,
            "os": args.os_name or platform.platform(),
            "context_limit": args.context_limit,
            "seed": args.seed,
        }
    initial_rows = []
    if args.resume and args.output.is_file():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("model") != args.model:
            raise SystemExit("resume checkpoint model does not match --model")
        initial_rows = existing.get("rows") or []

    def checkpoint(rows: list[dict]) -> None:
        atomic_write_json(
            args.output,
            {
                "schema_version": "workman-field-tests.checkpoint.v1",
                "status": "IN_PROGRESS",
                "model": args.model,
                "endpoint_label": args.endpoint_label,
                "rows": rows,
            },
        )

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
        no_think=args.no_think,
        provenance=provenance,
        initial_rows=initial_rows,
        checkpoint=checkpoint,
        progress=lambda message: print(message, file=sys.stderr, flush=True),
    )
    atomic_write_json(args.output, result)
    print(json.dumps(result["summary"], sort_keys=True))
    return exit_code_for_summary(result["summary"], args.min_pass_rate)


if __name__ == "__main__":
    raise SystemExit(main())
