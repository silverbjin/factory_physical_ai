# TASK-SIM-Q01 — Additive Simulation Provenance Qualification

## 1. Objective

Produce new, additive, immutable Simulation qualification Evidence for the
provenance facts that accepted predecessor Evidence does not contain and that
TASK-SIM-010 requires to evaluate observability regression.  A qualification
record proves a newly executed or newly measured qualification subject bound
to an immutable predecessor state; it never claims to be the historical
predecessor run.

The task-specific result is exactly one of:

```text
SIM_PROVENANCE_QUALIFICATION_READY
SIM_PROVENANCE_QUALIFICATION_BLOCKED
```

## 2. Lifecycle role and preconditions

This is a predecessor-qualification task for the frozen TASK-SIM-010 handoff
at commit `ff48f751489800132099b7c3e8ac2ad7435c9b73`.  It is not a repair of
SIM-004 through SIM-009 and does not reopen their Acceptance records.

Before any qualification collector runs, it MUST resolve and verify every
following immutable predecessor binding from Git objects, not from a current
working-tree copy.

| Task | Acceptance path | Accepted commit | Evidence path | Evidence SHA256 |
|---|---|---|---|---|
| TASK-SIM-004 | `results/reviews/SIM-004_acceptance.json` | `b7e8266abd17f48c18cca94d9433db50fd55464d` | `results/simulation/SIM-004_navigation_backend.json` | `b4c0ce91dde6c2f92c57ea6a227149362279993dee0dec4fd1ab12877e73f1d9` |
| TASK-SIM-005 | `results/reviews/SIM-005_acceptance.json` | `542514a4d10bc03087834e8a5f672d53afe6aa21` | `results/simulation/SIM-005_mujoco_vla_backend.json` | `f4d41fdb1f13978e1b1e5c91b95e31b38a69825a0d432a8284ff7731a3beb84f` |
| TASK-SIM-007 | `results/reviews/SIM-007_acceptance.json` | `228eb7745aa05c230e1b272184601b5afd53853b` | `results/simulation/SIM-007_mission_integration.json` | `7247f8db76c874e533f615f1c8c3f32febb7a7e2377790ff05e3e93320531711` |
| TASK-SIM-008 | `results/reviews/SIM-008_acceptance.json` | `ea91e0c16412e20c8cae66355a1a39129919dd42` | `results/simulation/SIM-008_normal_system_e2e.json` | `ebf0ef0a27114e3c04fa6bec05aa3eef792fdfc282d2be009640bac7ecc26290` |
| TASK-SIM-009 | `results/reviews/SIM-009_acceptance.json` | `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be` | `results/simulation/SIM-009_failure_recovery.json` | `91d10e5bb4fb7ca1b62c325885bec276c6ef6231c6baa0424f3213702be3216e` |

The current SIM-010 Evidence is authoritative only for identifying these
gaps.  It is not a source of predecessor provenance.

## 3. Authoritative sources

### 3.1 Required

- `docs/contracts/simulation_execution_contract_v1.md`
  - Preserves operation, identity, reconciliation, Verification, and
    non-success semantics.
- The predecessor Acceptance, accepted commits, and Evidence blobs in Section
  2.
  - Bind the exact qualified subject.
- `tasks/TASK-SIM-010.md`,
  `docs/task_history/TASK-SIM-010/11_diagnosis.md`, and
  `results/simulation/SIM-010_observability_regression.json`.
  - Bound the downstream gaps and the SIM-010 consumption need.

### 3.2 Conditional

- Predecessor task specifications at their accepted commits.
  - Read for a qualification scenario's frozen semantics or asset authority.
- The Simulation contract schema.
  - Read for structural validation failures.

## 4. Scope

This task MUST produce qualification subjects only for the following genuine
gaps.

1. SIM-004: structured, measured per-scenario `simulation_time` for the
   accepted success, blocked, and timeout/reconciliation cases.
2. SIM-005: new MuJoCo runs with run-created correlation identity, including
   `trace_id`, and exact MuJoCo configuration provenance.
3. SIM-007: profile-local source/configuration qualification for aggregate
   profile records, without converting them into operation messages.
4. SIM-008: distinct bridge-configuration and launch/run-configuration
   authorities for a new normal-system qualification.
5. SIM-009: run-local configuration, world/model, and structured simulation
   time for applicable Gazebo and MuJoCo failure/recovery scenarios.

### Non-goals

This task MUST NOT:

- modify predecessor Acceptance, canonical Evidence, or accepted commits;
- attach a newly created identity, hash, or time to a historical run;
- infer time from log prose, wall time, or timestamps;
- use a current file as a replacement for an accepted historical asset;
- join subjects by backend name, position, recency, or an arbitrary matching
  action identifier;
- change accepted failure, recovery, reconciliation, or Verification
  semantics;
- create physical, production-performance, training, or hardware claims.

## 5. Qualification subject identity

Every `qualification_subject` MUST include one complete
`predecessor_binding`:

```text
predecessor_task_id
predecessor_acceptance_path
predecessor_accepted_commit
predecessor_evidence_path
predecessor_evidence_sha256
```

It MUST also declare its `record_kind` as exactly `operation_run`,
`profile_aggregate`, or `version_qualification`; its subject-specific
`qualification_run_id` where a run exists; and explicit `claim_scope`.

An operation subject additionally binds exact `scenario_id`, `backend_id`,
`component_version`, and each applicable configuration/world/model identity.
An aggregate subject binds exact `profile_id` and preserves aggregate
semantics.  A version qualification binds exact component version and asset
identity, and MAY satisfy only version-wide fields explicitly labelled as
such; it MUST NOT satisfy a run-local field.

Q01 collectors MUST obtain predecessor assets either directly from the bound
Git blob or from a temporary execution materialization whose content hash is
verified equal to that blob before use.  A Q01 source revision alone is not
such authority.

## 6. Requirements

### Q1 — Immutable predecessor resolution

The implementation MUST resolve each Section 2 acceptance/commit/Evidence
tuple deterministically, recompute the Evidence SHA256 from the Git blob, and
fail before a collector or aggregator uses a subject when any tuple differs.

### Q2 — Additive-record honesty

Every qualifying record MUST state that it is a new qualification and identify
the frozen predecessor subject it qualifies.  It MUST NOT represent new
correlation IDs, time, or asset facts as fields that existed in historical
Evidence.

### Q3 — SIM-004 Gazebo/Nav2 time qualification

Q01 MUST execute one bounded, distinct operation qualification for each of
`success`, `blocked`, and `timeout_reconciliation`.  Each record MUST contain
structured simulator time captured by the simulator API/structured runtime
measurement, wall time, bounded execution/cleanup, exact world identity,
component version, and separately authoritative bridge and launch/run asset
identities.  Wall time, command text, or logs cannot substitute for simulator
time.

### Q4 — SIM-005 MuJoCo correlation qualification

For every qualified MuJoCo operation scenario, Q01 MUST create `mission_id`,
`request_id`, and `trace_id` at run creation; it MUST create `action_id` only
when the operation is action-bound.  It MUST record exact MuJoCo version,
model, scene, configuration, source hashes, seed, timestep, step settings,
and initial-state identity.  A new trace qualifies only its own Q01 run.

### Q5 — SIM-007 profile-aggregate qualification

Q01 MUST qualify each required profile using `profile_aggregate` records with
exact `profile_id`, profile-local source/configuration identities, and the
accepted aggregate outcome semantics.  Such a record MUST NOT require or
invent singular request/action IDs.  An accepted `mission_result = failure`
is an expected outcome when that is the frozen profile result, not an
assertion failure.

### Q6 — SIM-008 semantic configuration separation

Q01 MUST bind the bridge configuration and launch/run configuration as two
separate, semantically identified authorities.  A single generic configuration
hash cannot satisfy both roles unless the source explicitly identifies the
same immutable asset as both roles, which Q01 MUST record and validate.

### Q7 — SIM-009 run-local failure/recovery qualification

Q01 MUST execute a separate operation qualification for every SIM-009
Gazebo/MuJoCo scenario for which SIM-010 requires run-local configuration,
world/model, or simulator-time facts.  Each subject MUST preserve the exact
accepted scenario identifier and expected failure/recovery/reconciliation or
Verification semantic outcome.  A version-wide qualification may support
only a version-wide backend field and cannot replace a required run-local
world, model, configuration, timing, or correlation fact.

### Q8 — Applicability and semantic validation

The validator MUST use a declared applicability model.  It MUST require
recovery only for a scenario whose frozen semantics require recovery, and a
Verification verdict only for a successful Verification invocation.  An
operational Verification failure requires its structured error and MUST NOT
be forced to carry a verdict.

### Q9 — Evidence integrity and claim scope

The Evidence described in Section 8 MUST validate every subject, preserve
JSON source/asset authority paths, and set the task-specific result READY
only when all required qualification subjects pass.  Missing, duplicate, or
ambiguous subject identity is BLOCKED.

### Q10 — Fail-closed negative behavior

Q01 MUST reject wrong accepted commit, missing Git blob, Evidence hash
mismatch, predecessor-binding mismatch, wrong component/profile/scenario,
cross-scenario association, backend-name-only association, stale/tampered
Evidence, and configuration/world/model mismatch.

### Q11 — Downstream consumption contract

Q01 MUST publish no implicit inheritance.  Future SIM-010 resolution may
consume a Q01 subject only through the exact chain in Section 9 and only for
the explicitly declared `claim_scope` and applicable subject kind.

### Q12 — Independent workflow

Q01 MUST follow Implementation → Evidence → independent Review → Acceptance.
No Q01 READY output, downstream consumption, or re-review shortcut is valid
before independent Acceptance.

## 7. Minimum qualification-run design

The following run IDs are design identifiers.  They are not created by this
specification and they do not denote historical runs.

| Qualification subject(s) | Purpose and required scope |
|---|---|
| `q01-sim004-success-time`, `q01-sim004-blocked-time`, `q01-sim004-timeout-reconciliation-time` | Gazebo/Nav2 operation runs; each captures structured simulator time and exact world/bridge/launch authority for its corresponding accepted semantic class. |
| `q01-sim005-<accepted-scenario-id>` | One new MuJoCo operation run for each SIM-005 scenario that SIM-010 consumes.  This is the minimum safe scope because trace/correlation and run-local physics provenance cannot be shared by position or backend name. |
| `q01-sim007-<profile-id>` | Four profile-aggregate records: `deterministic`, `navigation_physics`, `manipulation_physics`, and `system`.  These may be collected by one bounded profile-qualification session but remain four distinct subjects. |
| `q01-sim008-normal-system-authority` | One new normal system run that binds distinct bridge and launch/run authorities with normal scenario identity and structured timing. |
| `q01-sim009-<accepted-scenario-id>` | One new operation qualification for every applicable Gazebo/MuJoCo SIM-009 scenario.  Separate runs are required because the missing facts are run-local and no existing contract authorizes sharing them across scenario identities. |

All runs MUST have explicit startup, execution, timeout, and cleanup bounds.
Each declared expected semantic outcome is compared with the frozen accepted
scenario outcome; non-success outcomes are valid when they are the expected
semantic result.

## 8. Evidence design

The canonical Q01 Evidence path is:

```text
results/simulation/SIM-Q01_provenance_qualification.json
```

The implementation MUST emit a versioned JSON object with at least:

```text
schema_version
task_id = TASK-SIM-Q01
task_specific_result
source_git_sha
simulation_only = true
qualification_subjects[]
validation
```

Each subject has:

```text
subject_id
record_kind
claim_scope
predecessor_binding
qualification_run_id                 # required for operation_run
profile_id / scenario_id as applicable
backend_id
component_version
correlation_identity                 # fields only when applicable
configuration_provenance
world_model_provenance               # when applicable
timing { simulation_time, wall_time, bounded_execution }
semantic_outcome
authority_paths
validation
```

`configuration_provenance` names each semantic asset role independently;
hashes cannot be copied into a different role. `authority_paths` identify the
Q01 Evidence location or immutable Git asset path supplying each claimed
field. The schema distinguishes absent/not-applicable from a fabricated
placeholder; absent required fields fail validation.

The human-readable companion is
`docs/simulation/SIM-Q01_provenance_qualification.md`.  The post-review
Acceptance is `results/reviews/SIM-Q01_acceptance.json` and follows the
repository's canonical deterministic Acceptance model.

## 9. Downstream TASK-SIM-010 binding contract

After Q01 is independently accepted, SIM-010 may consume a qualification
subject only by:

```text
Q01 Acceptance
  -> accepted_commit
  -> exact Q01 Evidence blob at accepted_commit
  -> recomputed Q01 Evidence SHA256
  -> predecessor_binding matched to frozen predecessor commit + Evidence SHA256
  -> unique subject_id, record_kind, profile/scenario/run identity, claim_scope
  -> applicable normalized SIM-010 provenance
```

The future resolver MUST reject an absent/wrong Q01 commit or blob, a hash
mismatch, an unaccepted predecessor revision, component/profile/scenario
mismatch, a duplicate subject, or a claim beyond the subject scope.  A Q01
operation row is an additional current qualification row; it does not mutate
or conceal a historical predecessor gap.  SIM-010 may use it only where its
future resolver explicitly recognizes Q01 additive-qualification semantics.

## 10. Validation

### Focused

The implementation MUST add focused tests for:

- accepted commit/blob/SHA resolution and all mismatch cases;
- run-created trace identity and action-bound applicability;
- aggregate profile rows without fabricated singular operation IDs;
- structured simulation-time capture, rejecting log text as a substitute;
- distinct semantic bridge and launch/run asset roles;
- exact component/profile/scenario binding and rejection of cross-scenario or
  backend-name-only joins;
- version-wide versus run-local claim-scope enforcement;
- tampered/stale Evidence and wrong predecessor binding;
- expected non-success, recovery, reconciliation, and Verification outcomes.

### Qualification execution

Run all declared bounded qualification subjects, generate fresh Evidence, run
the task-owned aggregator, run `git diff --check`, and run the repository
regression command required by the implemented task contract.  Existing
SIM-010 regression evidence is not Q01 verification.

## 11. Exit criteria

- EC1: Every Section 2 predecessor tuple resolves from immutable Git state.
- EC2: Every required Q01 subject is unique, deterministic, and explicitly
  scoped.
- EC3: Required structured time, correlation, configuration, and world/model
  provenance are recorded from new qualification measurements.
- EC4: Expected predecessor semantics are preserved, including accepted
  non-success outcomes.
- EC5: All negative/tamper checks fail closed.
- EC6: Evidence is fresh, complete, Simulation-only, and reports exactly the
  declared task-specific result.
- EC7: Independent Review and Acceptance have occurred before any downstream
  use.

## 12. Workflow handoff

Implementation uses the repository's normal task workflow.  Completion of
implementation does not authorize consumption by TASK-SIM-010; only a later
independent Review and Acceptance of Q01 can establish the acceptance root
described in Section 9.
