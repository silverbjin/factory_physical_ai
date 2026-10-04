# Diagnosis — TASK-SIM-E2E

- Status: RESOLVED
- Result: RESOLVED
- Trigger: `initial_red_classification`; the focused test path and task-owned verifier are absent.
- Triggering status: pytest exit `4`; verifier invocation exit `2`.

## Trigger

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_e2e_qualification.py` reports that the test file is not found, and `python3 scripts/verify_simulation_e2e_qualification.py` reports that the verifier is not found.

## Root Cause

TASK-SIM-E2E has not been implemented. All four deliverables in the task-owned allowlist are absent; the current branch contains the TASK specification but no verifier, focused tests, qualification Evidence, or human-readable report.

## Requirement / Contract

`tasks/TASK-SIM-E2E.md` Sections 7–11 require a pure read-only evaluator and CLI, isolated fail-closed tests, `results/simulation/SIM-E2E_qualification.json`, and `docs/simulation/simulation_e2e_qualification_v1.md`. R15 and R16 require predecessor non-mutation and the exact stdout/exit-code contract.

## Authoritative Sources

- `tasks/TASK-SIM-E2E.md`
- `results/reviews/SIM-003_acceptance.json` through `results/reviews/SIM-010_acceptance.json`
- `results/simulation/SIM-010_observability_regression.json`

The required acceptance artifacts exist. SIM-010 contains one unique accepted-source entry for each of SIM-003 through SIM-009, and every indexed acceptance/Evidence hash matches the current file. SIM-010's own acceptance-to-Evidence hash also matches. These facts rule out missing or tampered required inputs as the cause of the initial red state.

## Fault Domain

Target implementation.

## Resolution

Implement the task from the existing contract. No architecture or contract decision is needed before implementation.

## Authorized Correction Boundary

Only these TASK-owned files may be added or modified:

- `scripts/verify_simulation_e2e_qualification.py`
- `tests/test_simulation_e2e_qualification.py`
- `results/simulation/SIM-E2E_qualification.json`
- `docs/simulation/simulation_e2e_qualification_v1.md`

## Modification Scope

Create the four allowlisted deliverables. The evaluator must resolve immutable acceptance/index bindings, reconstruct predicates from bound underlying Evidence, fail closed, preserve the fixed false authorization snapshot, and expose the exact CLI contract.

## Protected Boundary

Do not modify predecessor implementation, acceptance artifacts, underlying Evidence, SIM-010's source index, shared simulation/mission/runtime/contract/backend behavior, TASK specifications, or Git history. Tests must use isolated fixtures and must not mutate canonical inputs.

## Protected Scope

All repository paths outside the four-file TASK allowlist, except this mandated TASK-history record and index.

## Required Verification

1. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_e2e_qualification.py`.
2. Run the task-owned verifier against canonical repository inputs and verify exactly one decision line on stdout with exit `0` for a completed evaluation.
3. Verify fixture coverage for tamper, missing, BLOCKED/wrong READY, stale/contradictory bindings, conditional-source non-repair, top-level forgery, predecessor non-mutation, and CLI behavior.
4. Run `git diff --check` and confirm the changed implementation set stays within the task allowlist.

## Verification

The minimum focused verification is the TASK Section 10.1 pytest command, canonical CLI execution, `git diff --check`, and an explicit changed-file allowlist check. Regression is `NOT REQUIRED` unless out-of-scope shared behavior was changed, in which case the change must be removed.

## Assumptions Forbidden

- Do not interpret the current red state as a substantive `SIM_E2E_NOT_QUALIFIED` decision; no evaluator exists yet.
- Do not trust top-level READY/PASS/QUALIFIED fields or the SIM-010 normalized summary without reconstructing each predicate from bound underlying Evidence.
- Do not infer staleness from current `HEAD` alone.
- Do not invent a direct SIM-009 Evidence binding in its acceptance artifact; validate the unique SIM-010 accepted-source/index binding required by the TASK contract.
- Do not remediate or rebind predecessor Evidence.
- Do not elevate any physical, hardware, Dataset V1, SmolVLA, or Week-task authorization.

## Next Action

IMPLEMENTATION

Final diagnosis status: RESOLVED
