# 2026-07-13 operator role rankings

This packet publishes sanitized aggregate evidence from the Workman role harness. It does not publish private operational prompts, internal network addresses, filesystem paths, credentials, or raw model output.

## Controlled semantic rankings

Ranks are lane-specific. A rank in one role does not transfer to another role.

| Lane | Rank | Model | Semantic pass | Trials | Status |
|---|---:|---|---:|---:|---|
| Blog Factory | 1 | Ornith 35B | 100.0% | 72 | active control |
| Blog Factory | 2 | Qwen3.6 35B-A3B | 100.0% | 72 | retired, rollback only |
| Blog Factory | 3 | Qwen3.6 35B NVFP4-Fast | 100.0% | 72 | report only |
| Code Repair | 1 | Qwen3-Coder-Next | 100.0% | 72 | active control |
| Code Repair | 2 | Qwen3-Coder 30B | 100.0% | 72 | rollback control |
| Code Repair | 3 | Qwen3.6 35B NVFP4-Fast | 100.0% | 72 | report only |
| Code Repair | 4 | Qwen3.6 35B-A3B | 100.0% | 72 | report only |
| Code Repair | 5 | Ministral 14B | 77.8% | 72 | needs hardening |
| Code Repair | 6 | Nemotron 30B | 56.9% | 72 | needs hardening |
| Loop Forge | 1 | Qwen3.6 35B-A3B | 100.0% | 64 | active control |
| Loop Forge | 2 | Qwen3.6 35B NVFP4-Fast | 100.0% | 64 | report only |
| Loop Forge | 3 | Ministral 14B | 87.5% | 64 | needs hardening |
| Loop Forge | 4 | Nemotron 30B | 57.8% | 64 | needs hardening |
| Workman Worker | 1 | Ornith 9B | 100.0% | 40 | active control |

Frontier controls scored 100% in Code Repair and Loop Forge but are reference ceilings, not local ranks.

## Qwen Fast confirmation

- Full role confirmation: 208/208.
- First passive watchdog: 208/208.
- Fresh champion confirmation: Ornith Blog Factory 72/72; Qwen3-Coder-Next Code Repair 72/72; Qwen3.6 35B-A3B Loop Forge 64/64.
- Decision: quality ceiling tie across all three large-model roles; no automatic production promotion.

## Evidence boundaries

- Semantic role scores do not mix with the public 22-check quality battery.
- Mac Studio and DGX throughput remain host-specific.
- Latency is configuration evidence, not a universal model score.
- Smoke checks remain visible but never become role ranks.
- Any missing or hash-mismatched receipt falls back to unranked.

Machine-readable aggregates are in [`role-rankings.json`](role-rankings.json).
