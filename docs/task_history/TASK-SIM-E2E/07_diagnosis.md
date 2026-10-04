# Diagnosis — TASK-SIM-E2E

- Status: RESOLVED
- Trigger: Re-review finding `SIM-E2E-REREV-001` showed a sparse SIM-009 Evidence fixture can still produce `SIM_E2E_QUALIFIED`.
- Triggering status: Canonical scenario IDs plus `pass=true`, cleanup flags, and `mission_success_committed=false` qualify even when outcome/recovery semantics are absent.
- Finding IDs: `SIM-E2E-REREV-001`

## Trigger

The task-owned verifier does not reconstruct mandatory SIM-009 failure/recovery meaning from the accepted Evidence schema.

## Root Cause

`scripts/verify_simulation_e2e_qualification.py::_scenario_set` checks only unique required scenario IDs and `pass=true`. `PREDICATES["required_navigation_system_failures"]` and `PREDICATES["required_failure_cases"]` use that helper without checking canonical `layer`, `outcome_kind`, `expected_decision`, observed `decision`, or scenario-specific result/reconciliation/mission semantics. The separate safety checks require only cleanup flags and, for L2 rows in the synthetic fixture, `mission.mission_success_committed=false`.

The qualifying test fixture in `tests/test_simulation_e2e_qualification.py::_fixture` encodes the same reduced model, so focused tests validate the permissive implementation rather than the accepted SIM-009 schema. An isolated reproduction that removed every SIM-009 semantic field except IDs, `pass`, cleanup/budget flags, and the mission-success boolean returned `SIM_E2E_QUALIFIED`; all four SIM-009-owned matrix predicates returned `PASS`.

## Requirement / Contract

`tasks/TASK-SIM-E2E.md` R3, R8, R9, and R13 and Sections 4.1 and 9 require predicate-specific reconstruction from underlying accepted Evidence and fail-closed behavior for incomplete scenario coverage. `tasks/TASK-SIM-009.md` R1–R10 and its Evidence contract require each scenario's expected outcome, actual result/recovery decision, retry/reconciliation/idempotency/HITL facts where applicable, and bounded cleanup.

## Authoritative Source

- `tasks/TASK-SIM-E2E.md`
- `docs/task_history/TASK-SIM-E2E/06_review.md`
- `tasks/TASK-SIM-009.md`
- `results/reviews/SIM-009_acceptance.json`
- SIM-010's accepted-source binding for SIM-009 in `results/simulation/SIM-010_observability_regression.json`
- Bound accepted Evidence `results/simulation/SIM-009_failure_recovery.json`
- `scripts/verify_simulation_e2e_qualification.py`
- `tests/test_simulation_e2e_qualification.py`

## Fault Domain

Target verifier and task-owned focused tests.

## Resolution

Replace the generic SIM-009 ID/`pass` proof with an explicit task-local scenario contract keyed by all 16 required IDs. For every required row, validate the accepted canonical fields and fixed semantic expectation: `layer`, `outcome_kind`, `expected_decision`, observed `decision`, `pass=true`, `within_budget=true`, and `cleanup_complete=true`. The ID-specific contract must require the canonical decisions (`FAIL_CLOSED`, `RETRY`, `RECONCILE`, `RECOVERY`, or `HITL`) rather than accepting self-consistent arbitrary expected/observed values.

Also validate the corresponding observed payload: failure/error identity for fail-closed cases; timeout plus retry authorization, reconciled status, identity/idempotency, and single side effect for the retry case; reconciliation evidence for unknown/timeout cases; and exact L2 verification verdict plus mission state/transition/outcome with `mission_success_committed=false` for mismatch, stale, and uncertain cases. Keep bounded cleanup/process proof mandatory for every scenario. Both `required_navigation_system_failures` and `required_failure_cases` must consume this semantic validation; no predicate may pass from scenario presence or `pass=true` alone.

Replace the synthetic positive SIM-009 fixture with canonical-shaped semantics and add adversarial cases that independently remove or contradict outcome kind, expected/observed decision, result/error identity, retry/reconciliation/idempotency facts, L2 mission transition, and cleanup/budget fields. Each case must rebind only its isolated fixture hashes and return `SIM_E2E_NOT_QUALIFIED`.

## Authorized Correction Boundary

- `scripts/verify_simulation_e2e_qualification.py`: `_scenario_set`, SIM-009 predicate reconstruction, and task-local semantic helper/constants only.
- `tests/test_simulation_e2e_qualification.py`: canonical-shaped SIM-009 fixture and focused sparse/contradictory semantic cases.
- `results/simulation/SIM-E2E_qualification.json` and `docs/simulation/simulation_e2e_qualification_v1.md`: regenerate only to match the corrected verifier.

## Modification Scope

The correction is limited to the four TASK Section 7.4 allowlisted files above.

## Protected Boundary

Do not modify SIM-003 through SIM-010 implementation, acceptance artifacts, underlying Evidence, the SIM-010 source index, shared runtime/contracts/backends, `tasks/TASK-SIM-E2E.md`, `tasks/TASK-SIM-009.md`, or Git history. Do not invent new recovery policy or turn the canonical `SIM_E2E_NOT_QUALIFIED` result into remediation.

## Required Verification

1. Run `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_e2e_qualification.py`.
2. Re-run the sparse-semantics reproducer and each field-level adversarial fixture; all must return `SIM_E2E_NOT_QUALIFIED` with exit code `0` where the evaluation completes.
3. Verify a fully canonical-shaped isolated fixture still returns `SIM_E2E_QUALIFIED`.
4. Run the canonical CLI and confirm exactly one stdout decision line, exit code `0`, and report/Evidence agreement.
5. Confirm predecessor acceptance/Evidence hashes are unchanged, then run `git diff --check` and verify the changed-file set remains within Section 7.4.

## Assumptions Forbidden

- Do not treat scenario ID, `pass=true`, or cleanup flags as recovery-semantic proof.
- Do not accept `expected_decision == decision` without checking the fixed ID-specific canonical decision.
- Do not infer retry, reconciliation, idempotency, HITL, or mission transition from top-level READY/PASS fields.
- Do not weaken all SIM-009 cases to one uniform schema; validate the scenario-specific canonical payload.
- Do not modify or rebind accepted predecessor Evidence to make the gate qualify.

## Next Action

FIX_RESOLVED_DIAGNOSIS

Final diagnosis status: RESOLVED
