# Methodology

## What this measures

The public battery checks eleven behaviors. Repeats at temperature zero are timing samples, not independent quality checks:

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
- Use one temperature-zero pass for quality. Additional temperature-zero repeats measure timing jitter only.
- Warm the model before timing.
- Keep single-session and aggregate-concurrency throughput separate.
- Do not compare DGX and Apple Silicon speed as if the hardware and runtime were interchangeable.
- Preserve failed outputs. Do not silently rescore them.
- If a known-capable model returns zero or empty output, inspect the adapter before calling it a model-quality failure.

## Qwen no-think controls

For Qwen thinking-family models behind a compatible OpenAI-style vLLM endpoint, pass `--no-think` to send:

```json
{
  "reasoning_effort": "none",
  "include_reasoning": false,
  "chat_template_kwargs": {"enable_thinking": false}
}
```

No-think controls are opt-in because strict non-Qwen servers may reject unknown fields.

## Throughput

The non-streaming runner reports request-level output-token throughput when the server returns `usage.completion_tokens`. It divides completion tokens by full request wall time, including connection, queueing, prefill, decode, and response read. It is not decode speed. Streaming TTFT, inter-token latency, and decode-rate measurement are planned for v2.

For dedicated throughput work, publish the load generator, fixed input/output lengths, concurrency, request count, warmup, scheduler, KV-cache, speculative-decoding, batching, and percentile sample sizes alongside any number.

## Streaming metric definitions

- TTFT = first non-empty content event minus actual request send.
- TPOT = last-content time minus first-content time, divided by `max(completion_tokens - 1, 1)`.
- End-to-end latency = stream completion minus actual request send.
- Request throughput = completed requests divided by load-window wall time.
- Aggregate output-token throughput = successful completion tokens divided by load-window wall time.
- Concurrency efficiency = aggregate output-token throughput at concurrency C divided by `C ×` median concurrency-1 decode rate.

Token-derived streaming metrics require `usage.completion_tokens`. Missing usage is a failure, not an invitation to count SSE chunks as tokens. Open-loop runs report client dispatch delay so load-generator backlog is visible.

## Limits

This is a field test. It is not MMLU, HumanEval, or a universal intelligence score. The battery is intentionally small enough to inspect every failure.

Community results must use the v2 provenance schema and pass comparability and privacy validation. Cross-model quality comparisons may include only the same public-battery comparability class. Cross-hardware speed ranking is not supported.
