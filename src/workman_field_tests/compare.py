from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_result(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") not in {"workman-field-tests.v1", "workman-field-tests.v1.1", "workman-field-tests.v2"}:
        raise ValueError(f"{path}: unsupported schema_version")
    return data


def markdown_table(results: list[dict[str, Any]]) -> str:
    classes = {row.get("comparability_class", "legacy/unclassified") for row in results}
    if len(classes) != 1:
        raise ValueError(f"cannot rank mixed comparability classes: {sorted(classes)}")
    ranked = sorted(
        results,
        key=lambda row: (
            -(row.get("summary", {}).get("pass_rate") or 0),
            -(row.get("summary", {}).get("aggregate_request_tokens_per_second") or 0),
        ),
    )
    lines = [
        "| Rank | Model | Hardware | Runtime | Quality | Request tok/s |",
        "|---:|---|---|---|---:|---:|",
    ]
    for index, row in enumerate(ranked, 1):
        summary = row["summary"]
        speed = summary.get("aggregate_request_tokens_per_second")
        lines.append(
            f"| {index} | `{row['model']}` | {row['hardware']} | {row['runtime']} | "
            f"{summary['passed']}/{summary['total']} | {speed if speed is not None else 'n/a'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Build a quality-first Markdown leaderboard from field-test JSON files.")
    p.add_argument("results", nargs="+", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    table = markdown_table([load_result(path) for path in args.results])
    if args.output:
        args.output.write_text(table, encoding="utf-8")
    else:
        print(table, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
