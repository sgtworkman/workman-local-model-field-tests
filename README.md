# Workman Local Model Field Tests

Fast is easy to post. Reliable is harder.

This repository tests both.

Run the same public battery against local models on DGX Spark, Apple Silicon, or any OpenAI-compatible endpoint. Measure instruction following, structured output, tool shape, code repair, safety gates, context retention, latency, and generation speed.

Publish the conditions. Keep the failures. Let other operators reproduce the result.

## Current field-test leaders

| Rank | Model | Hardware | Quality | Generation speed | Decision |
|---:|---|---|---:|---:|---|
| 1 | Ornith 1.0 35B Q4_K_M | Mac Studio / llama.cpp | 22/22 | 86.67 tok/s | Mac Studio aggregator winner |
| 2 | Ornith 1.0 9B Q4_K_M | Mac Studio / llama.cpp | 22/22 | 61.45 tok/s | Worker/reference winner |
| 3 | Unsloth Qwen3.6 35B-A3B Q4_K_M | Mac Studio / llama.cpp | 22/22 | 53.54 tok/s | Clean challenger |
| 4 | Unsloth Qwen3.6 35B-A3B NVFP4-Fast | DGX Spark / vLLM | 20/22 | 67.87 tok/s normalized; 80.13 dedicated | DGX winner |
| 5 | Unsloth Gemma 4 12B Q4_K_M | Mac Studio / llama.cpp | 20/22 | 53.09 tok/s | Small-model contender |
| 6 | Unsloth Qwen3-Coder-Next Q4_K_M | Mac Studio / llama.cpp | 18/22 | 54.98 tok/s | Held |
| 7 | Unsloth Qwen3.6 27B Q4_K_M | Mac Studio / llama.cpp | 18/22 | 26.57 tok/s | Held |

DGX and Mac speeds are not directly comparable. Hardware, runtime, quantization, context, and scheduling differ. These are workload-specific field tests, not universal model rankings.

The DGX Fast result landed at 80.13 tok/s in our dedicated single-session run. MiaAI Lab independently reported roughly 81 tok/s on DGX Spark. Reproduction matters.

The included public battery was also rerun end to end against Ornith 9B: **22/22**, zero empty outputs, zero reasoning leaks, zero request errors, and **53.39 tok/s median generation across the mixed workload**. Inspect the [sanitized raw result](results/verified/2026-07-11-ornith-9b-mac-studio.json).

## Run it

Python 3.10 or newer. No runtime dependencies.

```bash
git clone https://github.com/sgtworkman/workman-local-model-field-tests.git
cd workman-local-model-field-tests
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run the 22-check battery against llama.cpp:

```bash
workman-field-test \
  --base-url http://127.0.0.1:8080/v1 \
  --model ornith \
  --hardware "Mac Studio" \
  --runtime "llama.cpp b9821" \
  --quantization Q4_K_M \
  --output raw-results/ornith-35b.json
```

Run it against vLLM on DGX Spark:

```bash
workman-field-test \
  --base-url http://127.0.0.1:8888/v1 \
  --model unsloth/Qwen3.6-35B-A3B-NVFP4 \
  --hardware "NVIDIA DGX Spark 128GB" \
  --runtime "vLLM" \
  --quantization NVFP4 \
  --output raw-results/qwen36-dgx.json
```

The runner does not write the endpoint URL or API key into the result.

## Sanitize before publishing

```bash
workman-field-sanitize raw-results/qwen36-dgx.json \
  --output results/community/your-name/qwen36-dgx.json
```

The sanitizer removes credential-adjacent fields, private addresses, internal hostnames, usernames, and personal paths. Review the output yourself. You own the release.

## Build a leaderboard

```bash
workman-field-compare results/community/your-name/*.json \
  --output LEADERBOARD.md
```

The comparison is quality-first. Speed breaks ties.

## What is public

- Generic prompts
- Runner and sanitizer
- Runtime metadata
- Sanitized raw outputs
- Pass/fail results
- Latency and throughput
- Reproduction instructions

## What stays private

- Credentials
- Private network details
- Customer or business data
- Proprietary prompts
- Internal routing policy
- Operational hostnames and filesystem paths

Read [the methodology](docs/METHODOLOGY.md). Submit your result through [the contribution guide](CONTRIBUTING.md).

Speed gets attention. Reproducibility earns trust.
