# Gate Validation — TASK-SIM-010

## Result

PASS — corrected S10-G0 through S10-G5 validation

## Source Candidate

`2179d965b64abac79c068a94363b9a67e9f4739b`

This remains the immutable source candidate. A documentation-only commit
created by this session must not replace it.

## Corrected Full Regression Provenance

Candidate:

- Commit / test tree: `2179d965b64abac79c068a94363b9a67e9f4739b`
- Collected: `396`
- Summary: `4 failed, 392 passed`
- Exit code: `1`

Baseline:

- Commit / test tree: `6909c6cceb727598570f6e170ae8d1d293418c9a`
- Collected: `341`
- Summary: `4 failed, 337 passed`
- Exit code: `1`

Qualified interpreter:

`/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python`

MuJoCo: `3.13.0`

## Test-Suite Evolution

Candidate-only collection contains `55` additional tests: `51` from
`tests/test_simulation_observability_regression.py` and `4` from
`scripts/codex/test_run_task_orchestrator.py`. This is
`EXPECTED_TEST_SUITE_EVOLUTION`; total and pass count equality are not G5
requirements.

## Corrected G5 Contract

- Total test count equality: NOT REQUIRED
- Pass count equality: NOT REQUIRED
- Complete failed-node set equality: REQUIRED / PASS
- Corresponding non-empty stable signature equality: REQUIRED / PASS

## Corrected G5 Decision

- Raw candidate: FAIL — `4 failed, 392 passed`
- Raw baseline: FAIL — `4 failed, 337 passed`
- Gate classification: `PASS_PROVEN_PREEXISTING`
- S10-G5: PASS

## History Correction

The previous baseline `4 failed, 392 passed` assertion in `22_review.md` is
`SUPERSEDED_BY_CORRECTIVE_DIAGNOSIS` only for the incorrect baseline
summary/test-tree provenance. The old record remains preserved as append-only
audit history.

Unrelated prior G0-G4 results and the requirement-scoped classification remain
valid.

## Requirement-Scoped Classification

- `53` total
- `21` `HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING`
- `32` `EXPLICITLY_QUALIFIED_BY_Q01`
- `0` `STILL_BLOCKING`

## Gate State

- S10-G0: PASS
- S10-G1: PASS
- S10-G2: PASS
- S10-G3: PASS
- S10-G4: PASS
- S10-G5: PASS

## Next Action

`RUN_MANUAL_S10_G6_AND_G7`
