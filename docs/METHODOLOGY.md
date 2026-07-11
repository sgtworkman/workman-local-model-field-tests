# Methodology

## What this measures

The public battery checks eleven behaviors twice:

1. Exact instruction following
2. Structured status output
3. Tool-call shape
4. Basic code repair
5. Basic command-injection awareness
6. Unsafe absolute-claim rejection
7. Approval-gate discipline
8. Absolute-claim cleanup
9. Escalation judgment
10. Context-marker retention
11. Benchmark-method completeness

Quality comes first. Speed breaks ties. A fast model that ignores a gate does not outrank a slower model that completes the work safely.

## Reproduction rules

- Record the exact serving artifact, quantization, runtime, runtime version, hardware, context limit, concurrency and sampling configuration.
- Use temperature zero for the quality battery.
- Run at least two repeats.
- Warm the model before timing.
- Keep single-session and aggregate-concurrency throughput separate.
- Do not compare DGX and Apple Silicon speed as if the hardware and runtime were interchangeable.
- Preserve failed outputs. Do not silently rescore them.
- If a known-capable model returns zero or empty output, inspect the adapter before calling it a model-quality failure.

## Qwen no-think controls

For Qwen thinking-family models behind an OpenAI-compatible vLLM endpoint, the runner sends:

```json
{
  "reasoning_effort": "none",
  "include_reasoning": false,
  "chat_template_kwargs": {"enable_thinking": false}
}
```

Use `--allow-thinking` only when reasoning output is part of the test.

## Throughput

The runner reports request-level generation tokens per second when the server returns `usage.completion_tokens`. For dedicated throughput work, publish the load generator, input/output lengths, concurrency, request count, warmup, and percentile latency alongside the headline number.

## Limits

This is a field test. It is not MMLU, HumanEval, or a universal intelligence score. The battery is intentionally small enough to inspect every failure.
