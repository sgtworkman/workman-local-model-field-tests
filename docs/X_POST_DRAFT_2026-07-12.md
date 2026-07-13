# X post draft — nine-model local inference comparison

Attach: [`docs/assets/local-model-field-test-ranking-2026-07-12.png`](assets/local-model-field-test-ranking-2026-07-12.png)

Fast numbers are easy to post. Comparable numbers take discipline.

We reran 9 local model artifacts with exact revisions, raw outputs, TTFT, streaming throughput, concurrency sweeps, privacy admission, and strict quality checks.

Mac Studio 96 GB:

- Qwen3.6 35B-A3B: 22/22, ~77 tok/s single, ~80 tok/s at C2
- Ornith 9B: 22/22, ~75 tok/s single, ~78 tok/s at C4
- Qwen3-Coder-Next: 22/22, ~58–60 tok/s
- Ornith 35B: fastest at ~81–85 tok/s, but 18/22 on strict output contracts

DGX Spark 128 GB:

- Qwen3.6 35B NVFP4-Fast: 22/22, ~58 tok/s single, ~73 tok/s at C2, ~72 tok/s at C8
- Standard NVFP4: 22/22, slower at every tested concurrency
- 27B NVFP4: 22/22 quality, but only 75% success at C24

Mac and DGX speeds are ranked separately. Aggregate streaming throughput is successful output tokens divided by the full load window. It is not decode-only speed.

Quality first. Speed second. Hardware disclosed.

Reproducible artifacts and methodology: https://github.com/sgtworkman/workman-local-model-field-tests/tree/main/results/verified/2026-07-12-nine-model-v2
