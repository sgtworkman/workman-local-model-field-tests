#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "results/verified/2026-07-12-nine-model-v2"
OUTPUT = ROOT / "docs/assets/local-model-field-test-ranking-2026-07-12.svg"

LABELS = {
    "ornith35-streaming.json": "Ornith 35B",
    "qwen36-35b-a3b-streaming.json": "Qwen3.6 35B-A3B",
    "ornith9-streaming.json": "Ornith 9B",
    "qwen3-coder-next-streaming.json": "Qwen3-Coder-Next",
    "gemma4-12b-streaming.json": "Gemma 4 12B",
    "qwen36-27b-streaming.json": "Qwen3.6 27B",
    "dgx-fast-streaming.json": "35B NVFP4-Fast",
    "dgx-35b-streaming.json": "35B NVFP4",
    "dgx-27b-streaming.json": "27B NVFP4",
}

QUALITY = {
    "Ornith 35B": "18/22",
    "Qwen3.6 35B-A3B": "22/22",
    "Ornith 9B": "22/22",
    "Qwen3-Coder-Next": "22/22",
    "Gemma 4 12B": "22/22",
    "Qwen3.6 27B": "22/22",
    "35B NVFP4-Fast": "22/22",
    "35B NVFP4": "22/22",
    "27B NVFP4": "22/22",
}


def rows(prefix: str) -> list[tuple[str, float, str]]:
    output = []
    for path in sorted((PACK / "streaming").glob(prefix + "*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        c1 = next(level for level in data["levels"] if level["concurrency"] == 1)
        label = LABELS[path.name]
        output.append((label, float(c1["aggregate_output_tokens_per_second"]), QUALITY[label]))
    return sorted(output, key=lambda row: row[1], reverse=True)


def panel(parts: list[str], title: str, subtitle: str, data: list[tuple[str, float, str]], x: int, y: int, width: int, color: str) -> None:
    parts.append(f'<text x="{x}" y="{y}" class="panel">{html.escape(title)}</text>')
    parts.append(f'<text x="{x}" y="{y + 30}" class="sub">{html.escape(subtitle)}</text>')
    max_value = max(value for _, value, _ in data)
    label_width = 230
    bar_width = width - label_width - 110
    for index, (label, value, quality) in enumerate(data):
        row_y = y + 80 + index * 66
        fill = "#C97A2B" if quality != "22/22" else color
        rendered = bar_width * value / max_value
        parts.append(f'<text x="{x}" y="{row_y + 20}" class="label">{html.escape(label)}</text>')
        parts.append(f'<rect x="{x + label_width}" y="{row_y}" width="{rendered:.1f}" height="30" rx="5" fill="{fill}"/>')
        parts.append(f'<text x="{x + label_width + rendered + 12:.1f}" y="{row_y + 21}" class="value">{value:.1f}</text>')
        parts.append(f'<text x="{x + label_width}" y="{row_y + 50}" class="quality">quality {quality}</text>')


def main() -> int:
    mac = rows("")
    mac = [row for row in mac if not row[0].endswith("NVFP4") and "NVFP4" not in row[0]]
    dgx = [
        (LABELS[path.name], float(next(level for level in json.loads(path.read_text())["levels"] if level["concurrency"] == 1)["aggregate_output_tokens_per_second"]), QUALITY[LABELS[path.name]])
        for path in sorted((PACK / "streaming").glob("dgx-*.json"))
    ]
    dgx.sort(key=lambda row: row[1], reverse=True)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">',
        '<rect width="1600" height="1000" fill="#F7F8FA"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#172033}.title{font-size:48px;font-weight:750}.deck{font-size:22px;fill:#566174}.panel{font-size:29px;font-weight:700}.sub{font-size:17px;fill:#687386}.label{font-size:19px;font-weight:600}.value{font-size:20px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:700}.quality{font-size:15px;fill:#687386}.foot{font-size:16px;fill:#687386}</style>',
        '<text x="70" y="82" class="title">Local model field-test results</text>',
        '<text x="70" y="122" class="deck">Single-session aggregate output throughput. Quality uses the same 22-check public battery.</text>',
        '<line x1="800" y1="180" x2="800" y2="820" stroke="#D8DDE6" stroke-width="2"/>',
    ]
    panel(parts, "Mac Studio", "96 GB unified memory · GGUF Q4_K_M · llama.cpp", mac, 70, 200, 670, "#2166C1")
    panel(parts, "DGX Spark", "128 GB unified memory · NVFP4 · vLLM", dgx, 860, 200, 670, "#9C7A18")
    parts.extend([
        '<line x1="70" y1="860" x2="1530" y2="860" stroke="#D8DDE6" stroke-width="2"/>',
        '<text x="70" y="902" class="foot">Metric: successful completion tokens ÷ full load-window wall time at concurrency 1. Not decode-only speed.</text>',
        '<text x="70" y="934" class="foot">Host rankings are separate. Orange marks a strict quality-contract miss. Source: workman-field-tests.v2 · 2026-07-12.</text>',
        '<text x="70" y="966" class="foot">github.com/sgtworkman/workman-local-model-field-tests</text>',
        '</svg>',
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
