# 2026-07-19 large local-model role rankings

Fastest does not automatically win.

This release publishes sanitized aggregate results for four generic roles across two hardware classes. It includes the new Bonsai 27B Binary and Ternary GGUF tests plus a current Qwen3.6 27B NVFP4 comparison.

![Large local-model role rankings](../../../docs/assets/local-model-category-rankings-2026-07-19.svg)

## What the chart means

- Quality score is the first ordering rule.
- Pass^N and critical failures come next.
- Median task time breaks only exact quality ties inside one host and comparison class.
- Tokens per second and task time come from the same accepted receipts as the quality result.
- Hardware classes are shown separately. Speed is never ranked across hosts.

The Code and Debugging result is the clearest example. Qwen3.6 27B NVFP4 scored 100.0 with zero critical failures. The 35B NVFP4 Fast model was much faster, but scored 98.6 with one critical failure. The 27B model ranks first.

## Publication boundary

This packet contains aggregate metrics, trial counts, public model and hardware labels, and evidence hashes. It does not contain private prompts, raw model output, internal routing state, network details, filesystem paths, credentials, or proprietary task names.

These results do not declare a universal model winner. They rank exact artifacts within one role, hardware class, battery, and serving profile.

Machine-readable aggregates are in [`category-rankings.json`](category-rankings.json).
