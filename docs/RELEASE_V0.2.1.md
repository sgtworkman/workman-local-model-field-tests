# v0.2.1 — admission and streaming-metric integrity

This release hardens the evidence boundary. It does not change the committed model outputs or host-specific aggregate-throughput rankings.

## Changes

- Reject duplicate `(scenario_id, repeat)` rows during v2 admission.
- Reconcile summary totals, pass counts, and pass rates to raw rows.
- Require scenario and repeat counts in admitted v2 artifacts.
- Align streaming decode rate with TPOT by excluding the TTFT-owned first token from both formulas.
- Add a one-command release verifier covering tests, privacy audit, commit provenance, and all nine verified quality artifacts.
- Correct the root README to point at the complete nine-model evidence pack.
- Add a reproducible, host-separated benchmark chart for GitHub and social sharing.

## Compatibility note

Historical pre-v0.2.1 streaming artifacts used total completion tokens in the row-level decode-rate numerator. Their aggregate output-token throughput, TTFT, TPOT, end-to-end latency, success rate, and published host rankings are unchanged. Do not use the old row-level decode field for precise comparisons.

## Verification

```bash
python -m pip install -e .
python scripts/verify_release.py
```

Expected result: 33 tests pass, the public boundary audit passes, all nine verified v2 quality artifacts pass admission, and the command ends with `RELEASE_VERIFICATION PASS`.

Regenerate the SVG chart with `python scripts/build_public_chart.py`. On macOS, generate the PNG social asset with:

```bash
sips -s format png docs/assets/local-model-field-test-ranking-2026-07-12.svg \
  --out docs/assets/local-model-field-test-ranking-2026-07-12.png
```
