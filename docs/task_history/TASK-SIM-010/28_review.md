# Gate Validation — TASK-SIM-010

## Result

PASS — S10-G0 through S10-G5

## Immutable Candidate

The reviewed source candidate is:

`8b4395f10a7235b018181d37e5b4a781222feafb`

The current later HEAD is documentation-only and does not replace this
immutable source candidate.

## Validation Scope

S10-G0 through S10-G3 were impact-based invariant and binding revalidations.
S10-G4 and S10-G5 were freshly validated against the new Fix candidate.

## Gate Results

- S10-G0: PASS
- S10-G1: PASS
- S10-G2: PASS
- S10-G3: PASS
- S10-G4: PASS
- S10-G5: PASS

## G4 Remediation Verification

Twenty-two adversarial tests passed, and valid accepted fixtures passed.
Coverage verified nested retry, reconciliation and lifecycle semantics,
required invariants, exact provenance, and NOT_APPLICABLE source validation,
including `timing.simulation_time_source`. This validates the remediation of
`SIM010-G8R-001` and `SIM010-G8R-002`; it does not claim S10-G8 PASS.

## Requirement-Scoped Classification

The accepted classification remains `53 / 21 / 32 / 0`:

- 53 total
- 21 `HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING`
- 32 `EXPLICITLY_QUALIFIED_BY_Q01`
- 0 `STILL_BLOCKING`

Historical deficiencies remain visible and were not globally cleared or
rewritten.

## Full Repository Regression

Candidate: `410 collected / 4 failed / 406 passed`
Baseline: `341 collected / 4 failed / 337 passed`

The raw pytest result was FAIL on both executions. Complete failed-node sets
were EQUAL, and corresponding stable signatures were NON-EMPTY / EQUAL.
Therefore the S10-G5 gate decision is `PASS_PROVEN_PREEXISTING`.

The 69-test collection difference is verified as ordinary test-suite
evolution: 65 candidate-only SIM-010 observability test nodes and 4
candidate-only orchestrator test nodes (`EXPECTED_TEST_SUITE_EVOLUTION`).
The candidate/baseline executions used their own clean detached source and
test trees, the qualified interpreter, and the identical declared command.

## Protected Boundary

- Canonical Evidence: NOT GENERATED
- Orchestrator: NOT USED
- Worktree after validation: CLEAN

## Next Action

`RUN_MANUAL_S10_G6_AND_G7`
