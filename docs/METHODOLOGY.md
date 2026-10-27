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

The non-streaming runner reports request-level output-token throughput when the server returns `usage.completion_tokens`. It divides completion tokens by full request wall time, including connection, queueing, prefill, decode, and response read. It is not decode speed.

For dedicated throughput work, publish the load generator, fixed input/output lengths, concurrency, request count, warmup, scheduler, KV-cache, speculative-decoding, batching, and percentile sample sizes alongside any number.

## Streaming metric definitions

- TTFT = first non-empty content event minus actual request send.
- TPOT = last-content time minus first-content time, divided by `max(completion_tokens - 1, 1)`.
- Decode rate = `completion_tokens - 1` divided by last-content time minus first-content time. The first token belongs to TTFT and is not counted again as a decode token.
- End-to-end latency = stream completion minus actual request send.
- Request throughput = completed requests divided by load-window wall time.
- Aggregate output-token throughput = successful completion tokens divided by load-window wall time.
- Concurrency efficiency = aggregate output-token throughput at concurrency C divided by `C ×` median concurrency-1 decode rate.

Token-derived streaming metrics require `usage.completion_tokens`. Missing usage is a failure, not an invitation to count SSE chunks as tokens. Open-loop runs report client dispatch delay so load-generator backlog is visible.

Streaming artifacts created before harness v0.2.1 used total completion tokens in the row-level `decode_tokens_per_second` numerator while TPOT excluded the first token. Their aggregate output-token throughput, TTFT, TPOT, end-to-end latency, success rate, and published host-ranking tables are unaffected. Do not use those historical row-level decode fields for precise comparisons.

## Admission integrity

Every v2 quality artifact must contain exactly one row per `(scenario_id, repeat)` identity. Admission rejects duplicate identities, missing rows, and summary totals, pass counts, or pass rates that do not reconcile to raw rows. Temperature-zero repeats are timing samples and never multiply the number of independent quality checks.

## Runtime safety preflight

Unified-memory systems must preserve both accelerator-free and host-available memory margins before a temporary runtime starts. Checking only the accelerator reservation can admit a launch that later stalls the API process under host-memory pressure. `workman_field_tests.runtime_safety.evaluate_memory_reservation` implements the public fail-closed calculation.

Explicitly forced inference backends require a verified activation/backend pairing. Prefer runtime backend selection (`auto`) when the pairing is not proven. Unknown forced backends fail closed.

For thinking models, the uncontrolled OpenAI-compatible adapter is diagnostic: it establishes route identity but may expose reasoning or consume its small output budget before visible content. Admission requires both the no-think and strict JSON-schema controlled profiles to return non-empty, route-correct output without reasoning leakage.

File-backed scorer modules should be loaded with their source directory temporarily available for sibling imports. Missing sources or module specifications are hard failures, not zero-quality model results.

## Limits

This is a field test. It is not MMLU, HumanEval, or a universal intelligence score. The battery is intentionally small enough to inspect every failure.

Community results must use the v2 provenance schema and pass comparability and privacy validation. Cross-model quality comparisons may include only the same public-battery comparability class. Cross-hardware speed ranking is not supported.
