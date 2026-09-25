# TASK-SIM-Q01 — Simulation Provenance Qualification Proposal

```yaml
STATUS: PROMOTED TO FORMAL SPECIFICATION
IMPLEMENTATION AUTHORIZED: NO
```

This proposal is preserved as the approval provenance for the formal task
specification at `tasks/TASK-SIM-Q01.md` and implementation plan at
`docs/plans/TASK-SIM-Q01_implementation_plan.md`.  Promotion does not
authorize implementation, qualification runs, Evidence generation, or
downstream TASK-SIM-010 consumption.

## Objective

Produce new additive, immutable qualification Evidence for the provenance facts that the fresh TASK-SIM-010 regression still proves absent from accepted predecessor state. The qualification records new runs or profile qualifications; it does not retroactively enrich historical runs.

## Authoritative trigger

- Diagnosis: `docs/task_history/TASK-SIM-010/11_diagnosis.md`
- Fresh Evidence: `results/simulation/SIM-010_observability_regression.json` generated at `2026-09-25T12:55:28Z`
- TASK-SIM-010 result: `SIM_OBSERVABILITY_REGRESSION_BLOCKED`
- Deterministic replay: `PASS`
- Normal/failure coverage: `PASS` (`SIM-008` 1/1, `SIM-009` 16/16)
- Full regression: `PROVEN_PREEXISTING`; current and baseline have the same four nodes and matching non-empty stable signatures.

## Non-goals

- No modification of SIM-003..SIM-009 Acceptance or canonical Evidence.
- No modification of accepted predecessor commits.
- No invented historical identity, source hash, simulator time, or provenance.
- No newly generated `trace_id` attached to an old SIM-005 run.
- No conversion of SIM-007 aggregate profile records into operation messages.
- No change to accepted outcomes, including accepted SIM-007 failure outcomes.
- No unrelated runtime behavior change and no physical or production performance claim.

## Frozen dependencies

| Predecessor | Accepted commit | Canonical Evidence | Evidence SHA256 |
|---|---|---|---|
| SIM-004 | `b7e8266abd17f48c18cca94d9433db50fd55464d` | `results/simulation/SIM-004_navigation_backend.json` | `b4c0ce91dde6c2f92c57ea6a227149362279993dee0dec4fd1ab12877e73f1d9` |
| SIM-005 | `542514a4d10bc03087834e8a5f672d53afe6aa21` | `results/simulation/SIM-005_mujoco_vla_backend.json` | `f4d41fdb1f13978e1b1e5c91b95e31b38a69825a0d432a8284ff7731a3beb84f` |
| SIM-007 | `228eb7745aa05c230e1b272184601b5afd53853b` | `results/simulation/SIM-007_mission_integration.json` | `7247f8db76c874e533f615f1c8c3f32febb7a7e2377790ff05e3e93320531711` |
| SIM-008 | `ea91e0c16412e20c8cae66355a1a39129919dd42` | `results/simulation/SIM-008_normal_system_e2e.json` | `ebf0ef0a27114e3c04fa6bec05aa3eef792fdfc282d2be009640bac7ecc26290` |
| SIM-009 | `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be` | `results/simulation/SIM-009_failure_recovery.json` | `91d10e5bb4fb7ca1b62c325885bec276c6ef6231c6baa0424f3213702be3216e` |

## Required new measurements

Only these fresh Evidence gaps are in scope.

### SIM-004 qualification

Run new Gazebo/Nav2 qualification scenarios corresponding to the accepted executed cases (`success`, `blocked`, and `timeout_reconciliation`) and record structured per-scenario simulation time. Preserve the already resolved action-keyed wall time and bounded lifecycle linkage, exact world identity, and the accepted bridge/runner asset authorities. Do not infer simulator time from wall time or timestamps.

### SIM-005 qualification

Create new MuJoCo qualification runs whose correlation identity is created with the run: `mission_id`, `request_id`, action-bound `action_id`, and `trace_id`. Record exact MuJoCo version, model/config/source hashes, seed, timestep/step settings, and initial-state identity. The new trace identities qualify the new runs only.

### SIM-007 qualification

For each accepted profile aggregate (`deterministic`, `navigation_physics`, `manipulation_physics`, and `system`), record explicit profile-local configuration and source identities/hashes without adding singular request/action fields. Preserve `mission_result`, `failure_code`, `action_ids[]`, and accepted failure semantics.

### SIM-008 qualification

Run a new normal system qualification that independently binds the bridge configuration asset and launch/run asset. Do not reuse the scenario `config_sha256` under both semantic names. Preserve normal-run correlation, world/config, timing, and outcome semantics.

### SIM-009 qualification

Run or explicitly re-qualify the applicable Gazebo and MuJoCo scenarios with run-local configuration hash, world/model identity, and structured simulation time. Preserve each scenario's accepted failure, recovery, reconciliation, and Verification semantics. Version-wide SIM-004/SIM-005 backend qualification may be retained only through accepted binding plus exact `component_version`; it cannot replace these run-local facts.

## Additive immutable Evidence model

Proposed artifact classes, subject to approval:

- Evidence: `results/simulation/SIM-Q01_provenance_qualification.json`
- Human-readable report: `docs/simulation/SIM-Q01_provenance_qualification.md`
- Post-review Acceptance: `results/reviews/SIM-Q01_acceptance.json`

The Evidence must distinguish operation runs, profile aggregates, and scenario qualification records. Every value must carry an explicit JSON source path or immutable asset authority. Original predecessor rows remain historical and unmodified.

## Binding contract

TASK-SIM-010 may consume the future artifact only through:

```text
Qualification Acceptance
  -> accepted_commit
  -> results/simulation/SIM-Q01_provenance_qualification.json at that commit
  -> recomputed Evidence SHA256
  -> qualified predecessor task + frozen predecessor commit/Evidence hash
  -> exact profile/scenario/run identity and qualification-record kind
  -> normalized TASK-SIM-010 provenance
```

For operation runs, binding requires the new run's complete correlation identity. For profile aggregates, binding requires exact profile identity and explicitly declared aggregate semantics. For SIM-009 backend facts, `accepted_bindings/SIM-004` or `accepted_bindings/SIM-005` plus exact `component_version` may bind version-wide facts only. Name-only, backend-name-only, positional, newest-file, and cross-scenario joins are forbidden.

Approval must define additive qualification semantics: a valid new qualification record satisfies the applicable TASK-SIM-010 gate while the historical predecessor row remains immutable and visibly gap-labeled; it must never be presented as if missing historical fields had existed.

## Failure behavior

Missing Acceptance, invalid commit, missing Git blob, hash mismatch, predecessor-state mismatch, duplicate/ambiguous identity, wrong profile/scenario, absent required measurement, or unsupported supersession/qualification relation must fail closed. Current-working-tree data and SIM-010-generated claims are not provenance substitutes.

## Validation

- Focused tests for exact accepted-commit/blob/hash resolution.
- Positive and negative identity-binding tests for operation, profile aggregate, and scenario qualification records.
- Tests that reject cross-scenario, positional, backend-name-only, and wrong-component bindings.
- Fresh Gazebo/Nav2 and MuJoCo qualification execution with structured time/config/world/correlation fields.
- Profile-local SIM-007 authority validation without synthetic operation IDs.
- Fresh TASK-SIM-010 focused validation and Evidence regeneration after independent review and Acceptance of the qualification artifact.
- Full regression comparison under the existing evidence-first baseline policy.

## Acceptance criteria

The qualification task succeeds only when independently reviewed, immutable accepted Evidence supplies every genuine gap required by TASK-SIM-010, all bindings are unique and deterministic, predecessor artifacts remain byte-for-byte unmodified, and TASK-SIM-010 can recompute every consumed hash from accepted Git state.

## MANUAL APPROVAL REQUIRED

Authorize all of the following as one architecture decision:

1. Use the identifier `TASK-SIM-Q01` and the name “Simulation Provenance Qualification”.
2. Perform new qualification runs instead of rewriting historical SIM-003..SIM-009 runs.
3. Measure exactly the gaps listed above: SIM-004 structured simulation time; SIM-005 new run-created trace correlation; SIM-007 profile-local config/source authority; SIM-008 separate bridge and launch/run authority; and SIM-009 run-local config, world/model, and simulation time.
4. Use the additive immutable Evidence/report/Acceptance model and proposed artifact paths.
5. Permit TASK-SIM-010 to consume the future accepted qualification artifact as an additional authoritative source under the deterministic binding contract above.
6. Permit qualification task specification and implementation work to begin only after this approval.
