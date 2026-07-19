#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/verified/2026-07-19-category-rankings/category-rankings.json"
OUTPUT = ROOT / "docs/assets/local-model-category-rankings-2026-07-19.svg"

CATEGORIES = (
    "General Instruction Following",
    "Code and Debugging",
    "Reasoning and Planning",
    "Batch Processing",
)
HOSTS = ("Apple Silicon 96 GB", "NVIDIA DGX Spark 128 GB")


def load_groups() -> dict[tuple[str, str], list[dict[str, object]]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in payload["rows"]:
        groups[(str(row["category"]), str(row["host"]))].append(row)
    for rows in groups.values():
        rows.sort(key=lambda row: int(row["rank"]))
    return groups


def panel(
    parts: list[str],
    title: str,
    rows: list[dict[str, object]],
    x: int,
    y: int,
    width: int,
) -> None:
    parts.append(f'<text x="{x}" y="{y}" class="panel">{html.escape(title)}</text>')
    parts.append(
        f'<text x="{x + width}" y="{y}" text-anchor="end" class="columns">'
        "Score · P^N · Crit · tok/s · sec</text>"
    )
    label_width = 295
    bar_width = width - label_width - 240
    for index, row in enumerate(rows):
        row_y = y + 38 + index * 47
        score = float(row["quality_score"])
        fill = "#24A85A" if int(row["rank"]) == 1 else "#D9DDE2"
        text_fill = "#FFFFFF" if int(row["rank"]) == 1 else "#28313D"
        rendered = max(3.0, bar_width * score / 100.0)
        label = html.escape(str(row["model"]))
        metrics = (
            f'{score:.1f} · {float(row["pass_power_n"]):.1f} · '
            f'{int(row["critical_failures"])} · {float(row["tokens_per_second"]):.1f} · '
            f'{float(row["median_task_seconds"]):.2f}'
        )
        parts.append(f'<text x="{x}" y="{row_y + 19}" class="rank">{int(row["rank"])}.</text>')
        parts.append(f'<text x="{x + 28}" y="{row_y + 19}" class="model">{label}</text>')
        parts.append(
            f'<rect x="{x + label_width}" y="{row_y}" width="{bar_width}" height="27" '
            'rx="4" fill="#EEF0F3"/>'
        )
        parts.append(
            f'<rect x="{x + label_width}" y="{row_y}" width="{rendered:.1f}" height="27" '
            f'rx="4" fill="{fill}"/>'
        )
        if int(row["rank"]) == 1:
            parts.append(
                f'<text x="{x + label_width + 10}" y="{row_y + 19}" class="winner" '
                f'fill="{text_fill}">WINNER</text>'
            )
        parts.append(
            f'<text x="{x + label_width + bar_width + 15}" y="{row_y + 19}" class="metrics">'
            f'{html.escape(metrics)}</text>'
        )


def render_svg(groups: dict[tuple[str, str], list[dict[str, object]]]) -> str:
    width = 1900
    height = 1320
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#161A20}.title{font-size:47px;font-weight:760}.deck{font-size:20px;fill:#4E5662}.category{font-size:31px;font-weight:740}.panel{font-size:20px;font-weight:720}.columns{font-size:13px;fill:#737B86}.rank{font-size:15px;fill:#8B929C}.model{font-size:16px;font-weight:560}.winner{font-size:11px;font-weight:780;letter-spacing:.5px}.metrics{font-size:14px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;fill:#313945}.legend{font-size:15px;fill:#555E6A}.foot{font-size:14px;fill:#68717D}</style>',
        '<text x="54" y="68" class="title">Large Local Model Role Benchmarks</text>',
        '<text x="54" y="105" class="deck">Quality first · reliability next · median task time breaks exact quality ties · hardware ranked separately</text>',
        '<rect x="1430" y="54" width="22" height="14" rx="3" fill="#24A85A"/>',
        '<text x="1460" y="67" class="legend">qualified winner</text>',
        '<rect x="1620" y="54" width="22" height="14" rx="3" fill="#D9DDE2"/>',
        '<text x="1650" y="67" class="legend">tested candidate</text>',
        '<line x1="54" y1="132" x2="1846" y2="132" stroke="#C9CED5" stroke-width="1"/>',
    ]
    section_y = 180
    section_height = 273
    for category in CATEGORIES:
        parts.append(f'<text x="54" y="{section_y}" class="category">{html.escape(category)}</text>')
        parts.append(
            f'<text x="1846" y="{section_y}" text-anchor="end" class="columns">'
            "Aggregate role battery · sanitized evidence</text>"
        )
        parts.append(
            f'<line x1="54" y1="{section_y + 17}" x2="1846" y2="{section_y + 17}" '
            'stroke="#D7DBE0" stroke-width="1"/>'
        )
        panel(parts, HOSTS[0], groups[(category, HOSTS[0])], 54, section_y + 56, 840)
        panel(parts, HOSTS[1], groups[(category, HOSTS[1])], 1005, section_y + 56, 840)
        parts.append(
            f'<line x1="950" y1="{section_y + 45}" x2="950" y2="{section_y + 222}" '
            'stroke="#E1E4E8" stroke-width="1"/>'
        )
        section_y += section_height
    parts.extend(
        [
            '<line x1="54" y1="1260" x2="1846" y2="1260" stroke="#C9CED5" stroke-width="1"/>',
            '<text x="54" y="1290" class="foot">Score and P^N are percentages. Crit = critical failures. tok/s = measured output throughput. sec = median full-task completion time.</text>',
            '<text x="1846" y="1290" text-anchor="end" class="foot">20 candidates · 4 task categories · evidence frozen 2026-07-19</text>',
            '</svg>',
        ]
    )
    return "\n".join(parts) + "\n"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(load_groups()), encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
