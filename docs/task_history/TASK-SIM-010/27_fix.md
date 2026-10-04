# Fix — TASK-SIM-010

- Result: COMPLETE
- Based on Review: `26_review.md`
- Source candidate: `8b4395f10a7235b018181d37e5b4a781222feafb`
- Canonical Evidence: NOT GENERATED
- Orchestrator: NOT USED
- Next: `RUN_MANUAL_S10_G0_THROUGH_G5`

## Trigger

This bounded Fix remediated the independent rereview findings:

- `SIM010-G8R-001`
- `SIM010-G8R-002`

## Authorized Boundary

Only the authorized resolver and test correction was committed in the Fix
candidate. The runner was not changed (`runner changed: NO`). No TASK
specification, canonical Evidence, accepted predecessor artifact, simulator,
physics implementation, or orchestrator source was modified.

## TDD

Negative tests were added before the implementation correction and the RED
phase was verified. Eight nested/provenance mutations failed before the
implementation: reconciliation completion, logical side-effect count,
missing reconciliation semantics, retry/reconciliation mismatch, lifecycle,
required state invariant, missing required provenance, and wrong/arbitrary
provenance claims. Additional NOT_APPLICABLE mutations covered missing and
wrong timing source, invalid justification/source pairing, and contradictory
execution-state applicability.

After implementation, the focused suite completed with **65 passed**.

## Finding Results

### SIM010-G8R-001

Status: FIXED

Historical-oracle versus Q01-observation comparison is now fail-closed for
the required nested semantics and exact provenance. Validation includes retry
semantics, reconciliation semantics and completion state, lifecycle semantics,
required state invariants, logical side-effect/idempotency invariants, and
exact required provenance. Missing, extra, contradictory, or semantically
wrong nested fields and provenance claims fail closed.

### SIM010-G8R-002

Status: FIXED

NOT_APPLICABLE observations now require the complete accepted
applicability/source contract, including the exact
`timing.simulation_time_source`. Missing or wrong sources, invalid
justification/source pairings, and contradictory simulator/physics execution
state claims fail closed; no source is synthesized.

## Regression Protection

The accepted fixture classification remains:

- 53 total
- 21 `HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING`
- 32 `EXPLICITLY_QUALIFIED_BY_Q01`
- 0 `STILL_BLOCKING`

The exact eleven operation subjects remain unchanged. Historical and Q01
authority namespaces remain separate. Deterministic replay remains
historical-only. No blanket Q01 override was reintroduced.

## Immutable Candidate

Previous rejected candidate:

`2179d965b64abac79c068a94363b9a67e9f4739b`

New Fix candidate:

`8b4395f10a7235b018181d37e5b4a781222feafb`

The new candidate must be fully re-gated from S10-G0. No previous G6/G7
Evidence is transferable to this candidate.

## Protected Boundary

- TASK specification: unchanged
- Q01 and predecessor accepted artifacts: unchanged
- Canonical Evidence: not generated
- Orchestrator: not used

## Required Verification

The next required sequence is:

S10-G0, S10-G1, S10-G2, S10-G3, S10-G4, S10-G5.

Only after all PASS may S10-G6, S10-G7, and a fresh independent S10-G8
review proceed.

## Next Action

`RUN_MANUAL_S10_G0_THROUGH_G5`
