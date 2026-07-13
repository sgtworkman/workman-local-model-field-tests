# Public benchmark data-quality report — 2026-07-12

## Dataset and grain

The verified pack contains nine v2 quality artifacts at one row per model, scenario, and repeat, plus nine streaming artifacts at one row per request and concurrency level. Quality comparisons share one public scenario hash and comparability class. Speed comparisons are valid only within the same host/runtime family.

## Checks performed

- Provenance and scenario-hash admission for all nine quality artifacts.
- Required-field, privacy, private-network, credential, and personal-path scanning.
- Unique `(scenario_id, repeat)` identities and expected row counts.
- Raw-row reconciliation to summary pass count, total, and pass rate.
- Request-error, empty-output, and hidden-reasoning checks.
- Streaming request accounting at concurrency 2, 8, and 24.
- TTFT, TPOT, decode-rate, aggregate-throughput, and success-rate definition review.

## Findings

1. **PASS — quality artifacts are admissible.** All nine current v2 files pass provenance, privacy, unique-grain, and summary reconciliation.
2. **FIXED — duplicate repeat inflation was not previously blocked.** Admission now rejects duplicate scenario/repeat identities and inconsistent summaries. Severity: high. Confidence: high.
3. **FIXED — row-level streaming decode numerator was inconsistent with TPOT.** Harness v0.2.1 excludes the first token from both formulas. Severity: medium because published ranking tables use aggregate load-window throughput, which was unaffected. Confidence: high.
4. **PASS — public boundary audit.** RFC1918, CGNAT, private IPv6, private hostnames, common credential formats, camelCase sensitive keys, and macOS/Linux home paths are covered by regression tests.
5. **HELD — universal or cross-hardware ranking.** Hardware and runtime differences make a combined speed leaderboard analytically unsafe.

## Impacted use cases

The hardened artifacts are safe for same-battery quality comparisons and host-specific streaming comparisons. They are not evidence for universal intelligence, cross-hardware efficiency, or production Code Repair promotion.

## Automated regression proof

`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` passes 33 tests. All nine v2 artifacts pass admission with commit verification. The public repository audit passes.

## Remaining gates

- Qwen3-Coder-Next still requires its isolated Code Repair semantic comparison before routing promotion.
- Historical row-level `decode_tokens_per_second` values from before v0.2.1 should not be used for precise decode comparisons.
- Publication remains approval-gated.
