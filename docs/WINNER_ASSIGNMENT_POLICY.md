# Winner assignment policy

A leaderboard result is evidence. It is not a route change.

Use four separate states:

1. **Tested** — the model produced complete evidence.
2. **Qualified** — it won an exact, comparable role and hardware pool.
3. **Assigned** — a versioned role registry points to its exact artifact and serving profile.
4. **Live** — the production route passed an exact task completion, watchdog, and rollback check.

Never collapse these states into one badge.

## Selection order

Rank inside one exact comparison class:

1. Quality score.
2. Pass^N reliability.
3. Critical failures.
4. Median end-to-end task time for exact quality ties.
5. Tokens per second as supporting capacity evidence.

The fastest model loses when its output is worse.

## Assignment record

Each role assignment should bind:

- public role ID;
- exact model or artifact revision;
- quantization and serving runtime;
- hardware class;
- battery, scorer, scenario-set, and prompt-profile identities;
- winning evidence hash;
- qualification timestamp and expiration;
- rollback assignment;
- assignment state and live-proof receipt.

Unknown or changed identities fail closed. A new model revision, quantization, runtime profile, scorer, prompt profile, or scenario set requires requalification.

## Controlled cutover

1. Freeze the qualified winner and rollback identities.
2. Confirm the full comparable candidate pool completed.
3. Update the assignment registry transactionally.
4. Run one exact task through the intended production route.
5. Run the role watchdog and zero-tolerance checks.
6. Mark the assignment live only after every check passes.
7. Restore the rollback assignment immediately on failure.

## Drift control

Run a winner-assignment audit on every configuration change and on a schedule. The audit compares the qualified-winner registry with the assigned registry and current live route.

Report these conditions separately:

- `WINNER_ASSIGNED_LIVE`
- `WINNER_QUALIFIED_NOT_ASSIGNED`
- `ASSIGNMENT_STALE_OR_EXPIRED`
- `LIVE_ROUTE_IDENTITY_DRIFT`
- `ROLLBACK_NOT_PROVEN`

No automatic promotion should occur from a benchmark alone. Automatic maintenance is safe only after the assignment contract, exact route proof, watchdog, expiration, and rollback mechanisms are all enforced.
