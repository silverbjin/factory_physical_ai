# Gate Validation — TASK-SIM-010

## Result

- Result: PASS — S10-G0 through S10-G5
- Event type: Review-style manual gate validation; this is not S10-G8 Acceptance.

## Immutable Candidate

`2179d965b64abac79c068a94363b9a67e9f4739b` is the immutable source candidate
validated by these gates. A later documentation-only history change is not a
replacement source candidate.

## Qualified Environment

- Python: `/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python`
- MuJoCo: `3.13.0`

## Focused Validation

Focused validation reference: `51 passed`.

## Requirement-Scoped Classification

- Classification total: `53`
- `HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING`: `21`
- `EXPLICITLY_QUALIFIED_BY_Q01`: `32`
- `STILL_BLOCKING`: `0`

Historical diagnostics remain preserved and visible. They were not deleted,
rewritten, or globally cleared by Q01 validity.

## Gate Results

- S10-G0: PASS
- S10-G1: PASS
- S10-G2: PASS
- S10-G3: PASS
- S10-G4: PASS
- S10-G5: PASS

## Full Repository Regression

- Candidate: `2179d965b64abac79c068a94363b9a67e9f4739b`
- Baseline: `6909c6cceb727598570f6e170ae8d1d293418c9a`
- Candidate raw result: `FAIL` — `4 failed, 392 passed` (exit code `1`)
- Baseline raw result: `FAIL` — `4 failed, 392 passed` (exit code `1`)
- Complete failed-node sets: MATCH
- Stable non-empty failure signatures: MATCH
- Raw execution result: `FAIL`
- S10-G5 classification: `PASS_PROVEN_PREEXISTING`

Raw pytest `FAIL` and the authorized S10-G5 `PASS_PROVEN_PREEXISTING`
classification are separate concepts under the TASK-SIM-010 contract. The
classification was accepted only after valid detached executions, complete
failed-node-set equality, and exact non-empty stable-signature equality.

## Source Isolation

Candidate detached source: PASS.

Baseline detached source: PASS.

Both executions used the qualified interpreter and shared environment without
project-source leakage; each imported project code from its own detached source.

## Protected Boundary

No unauthorized protected artifact changed. Canonical Evidence was not
generated, and no orchestrator was used.

## Next Action

`RUN_MANUAL_S10_G6_AND_G7`
