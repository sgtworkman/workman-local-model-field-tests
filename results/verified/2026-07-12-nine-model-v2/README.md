# Nine-model local inference comparison — 2026-07-12

This pack contains a complete quality and streaming-load comparison of nine local serving artifacts across a 96 GB Apple Silicon Mac Studio and a 128 GB NVIDIA DGX Spark.

Mac and DGX throughput values are **not cross-hardware rankings**. Models are ranked within each host. Quality used the same `workman-field-tests.v2` scenario set, scenario hash, sampling controls, and two-repeat battery.

## Quality

| Host | Serving artifact | Quality | Request errors | Reasoning leaks |
|---|---|---:|---:|---:|
| Mac Studio | Qwen3.6 35B-A3B Q4_K_M | 22/22 | 0 | 0 |
| Mac Studio | Ornith 1.0 9B Q4_K_M | 22/22 | 0 | 0 |
| Mac Studio | Qwen3-Coder-Next Q4_K_M | 22/22 | 0 | 0 |
| Mac Studio | Gemma 4 12B Q4_K_M | 22/22 | 0 | 0 |
| Mac Studio | Qwen3.6 27B Q4_K_M | 22/22 | 0 | 0 |
| Mac Studio | Ornith 1.0 35B Q4_K_M | 18/22 | 0 | 0 |
| DGX Spark | Qwen3.6 35B-A3B NVFP4-Fast | 22/22 | 0 | 0 |
| DGX Spark | Qwen3.6 35B-A3B NVFP4 | 22/22 | 0 | 0 |
| DGX Spark | Qwen3.6 27B NVFP4 | 22/22 | 0 | 0 |

Ornith 35B's four misses were strict output-contract failures: fenced tool JSON and `Verdict: Reject` instead of beginning literally with `Reject`. The substantive content was safe, but it did not satisfy the requested machine contract.

## Mac Studio streaming results

One model was resident at a time. Each level used one 256-token request per worker against the OpenAI-compatible streaming endpoint.

| Model | C1 tok/s | C2 tok/s | C4 tok/s | C1 TTFT p50 | C4 success |
|---|---:|---:|---:|---:|---:|
| Ornith 35B | 81.38 | 85.15 | 85.13 | 0.15s | 100% |
| Qwen3.6 35B-A3B | 76.99 | 80.07 | 79.52 | 0.15s | 100% |
| Ornith 9B | 74.76 | 76.81 | 77.61 | 0.16s | 100% |
| Qwen3-Coder-Next | 58.31 | 60.26 | 60.26 | 0.19s | 100% |
| Gemma 4 12B | 53.72 | 54.63 | 54.52 | 0.20s | 100% |
| Qwen3.6 27B | 27.16 | 27.87 | 27.68 | 0.35s | 100% |

Quality-first general-purpose selection: **Qwen3.6 35B-A3B**. Worker/reference selection: **Ornith 9B**.

## DGX Spark streaming results

| Model | C1 tok/s | C2 tok/s | C8 tok/s | C24 tok/s | C24 success |
|---|---:|---:|---:|---:|---:|
| Qwen3.6 35B-A3B NVFP4-Fast | 58.31 | 72.86 | 71.91 | 55.62 | 100% |
| Qwen3.6 35B-A3B NVFP4 | 44.66 | 66.17 | 65.28 | 50.83 | 100% |
| Qwen3.6 27B NVFP4 | 16.73 | 18.52 | 18.16 | 18.42 | 75% |

**NVFP4-Fast won every measured DGX concurrency level.** The useful operating range in this configuration is C1–C8. At C24, median TTFT exceeded 56 seconds for both 35B variants, so C24 should be treated as saturation evidence rather than an interactive recommendation.

## Metric definitions

- Quality request throughput is completion tokens divided by complete request wall time. It is not decode-only throughput.
- Streaming aggregate throughput is successful completion tokens divided by load-level wall time.
- TTFT is measured from request dispatch to the first visible content event.
- Host, runtime, quantization, context limit, model revision, scenario hash, sampling controls, raw rows, and failure classes are included in the JSON artifacts.

## Reproduce

See the repository root README and `docs/METHODOLOGY.md`. The quality files are in [`quality/`](quality/) and streaming files are in [`streaming/`](streaming/).

