# TASK-SIM-002 — Deterministic Smoke Runtime

> Lane: Simulation  
> Type: Minimal Executable Simulation Proof  
> Status: BLOCKED until TASK-SIM-001 consumer eligibility is satisfied  
> Governing ADR: `docs/architecture/adr/ADR-Simulation-Lane-v1.md`  
> Governing Mapping: `context/simulation_task_mapping_v1.md`  
> Predecessor: `TASK-SIM-001`  
> Downstream Consumer: `TASK-SIM-GATE`  
> Physical Authorization: NONE

---

# 1. Purpose

Implement the smallest bounded deterministic executable path necessary to prove that the accepted Simulation Contract Profile can execute without physical hardware.

This task exists to create concrete executable smoke evidence **before** `TASK-SIM-GATE`.

It is not a full simulator implementation.

---

# 2. Core State Model

The following states are distinct:

```text
Implementation completion
≠
Task-specific decision
≠
Independent acceptance
≠
Downstream authorization
```

This task may complete with either:

```text
SIM_SMOKE_READY
```

or:

```text
SIM_SMOKE_BLOCKED
```

An independently accepted `SIM_SMOKE_BLOCKED` means the blocked result is trustworthy.

It does **not** authorize `TASK-SIM-GATE` to produce SIM_GO.

---

# 3. Mandatory Predecessor Rule

`TASK-SIM-002` may start only when `TASK-SIM-001` satisfies **both**:

```text
1. independent acceptance = ACCEPT
2. task-specific decision = SIM_CONTRACT_PROFILE_READY
```

The following states prohibit implementation:

```text
SIM-001 acceptance missing
SIM-001 acceptance pending
SIM-001 acceptance rejected
SIM-001 decision missing
SIM-001 decision ambiguous
SIM-001 decision = SIM_CONTRACT_PROFILE_BLOCKED
SIM-001 evidence hash mismatch
SIM-001 profile hash mismatch
SIM-001 acceptance binding mismatch
SIM-001 reviewed commit missing
SIM-001 source binding mismatch
```

In any of these states:

```text
TASK-SIM-002 must not start.
```

This is a preflight contract failure, not a condition this task may repair.

---

# 4. Required Context

`TASK-SIM-002` shall use exactly the following authoritative sources:

```text
docs/architecture/adr/ADR-Simulation-Lane-v1.md
context/simulation_task_mapping_v1.md
docs/architecture/system_architecture_v1.md
docs/contracts/contract_plan.md
results/phase0/P0-004R_vla_readiness.json

docs/simulation/simulation_contract_profile_v1.md
results/simulation/SIM-001_contract_profile.json
results/reviews/SIM-001_acceptance.json
```

The accepted SIM-001 profile is the authoritative implementation envelope for SIM-002.

Additional files may be inspected only as supporting implementation context and shall not override the Required Context.

SIM-002 shall not expand, reinterpret, or repair the accepted SIM-001 profile merely to make the smoke runtime executable.

---

# 5. Preflight — SIM-001 Consumer Eligibility

Before modifying implementation files, verify:

```text
SIM-001 acceptance artifact exists
review_decision = ACCEPT
task_specific_decision = SIM_CONTRACT_PROFILE_READY

acceptance evidence SHA
=
canonical SIM-001 evidence SHA

acceptance profile SHA
=
canonical contract-profile SHA

reviewed Git commit exists

current source bindings
=
accepted source bindings
```

If any check fails:

```text
TASK-SIM-002 is NOT authorized to start.
```

Do not create partial implementation artifacts.

---

# 6. Goal

Demonstrate:

```text
accepted simulation contract profile
        ↓
bounded deterministic fixture/runtime
        ↓
known input
        ↓
known success/failure/timeout behavior
        ↓
machine-readable evidence
```

without:

- physical robot access;
- physical camera access;
- physical motion;
- training;
- Dataset V1;
- Week-task implementation.

---

# 7. Implementation Boundary

The smoke runtime shall sit behind the existing boundaries identified by accepted SIM-001, such as:

```text
Navigation Skill
VLA Skill
Verification
```

and/or the existing deterministic mission executor boundary.

It shall not create:

```text
Mission → ManipulatorPort
Mission → NavigationPort
Mission → ObservationPort
```

or any other new public actuator-facing contract.

---

# 8. Required Smoke Scenarios

Implement only scenarios permitted by accepted SIM-001.

Recommended minimum:

## S01 — Deterministic Success

```text
known request
→ deterministic fixture
→ expected successful result
```

## S02 — Deterministic Failure

```text
known request
→ deterministic fixture
→ explicit failure result
```

## S03 — Bounded Timeout

```text
known request
→ controlled delay / no-result
→ bounded timeout
→ non-success
```

## S04 — Ambiguous / Unknown Outcome

Only where supported by the accepted authoritative contract:

```text
ambiguous outcome
→ reconciliation / blocked completion
```

The task shall never convert an ambiguous result directly into success if the accepted contract prohibits it.

---

# 9. Determinism Requirements

Avoid:

- uncontrolled randomness;
- external physical dependencies;
- uncontrolled network dependencies;
- wall-clock-dependent business decisions;
- unbounded retry loops;
- hidden mutable global state.

Given the same accepted profile, fixture, request, and initial state, smoke execution shall produce semantically equivalent results.

---

# 10. Boundedness

Every scenario must have an explicit execution bound.

The runtime must not:

- wait indefinitely;
- retry indefinitely;
- leave child processes running;
- leave simulator/helper processes running;
- leak queues;
- leak files;
- leave background workers alive.

Cleanup itself must also be bounded.

---

# 11. Physical Isolation

Static and runtime evidence must establish that the smoke path does not require:

```text
/dev/tty*
/dev/video*
real robot controller
real camera
real gripper
physical E-stop
physical teleoperation
```

Physical execution remains unauthorized.

---

# 12. Training Isolation

The smoke runtime shall not require:

- model fine-tuning;
- optimizer execution;
- training compute;
- remote GPU provisioning;
- Dataset V1.

VLA behavior may be represented only through deterministic fixtures allowed by accepted SIM-001.

---

# 13. Dataset Boundary

Simulation fixtures shall use simulation-specific naming such as:

```text
SIM_FIXTURE_SET_V1
```

Invariant:

```text
SIM_FIXTURE_SET_V1
!=
Dataset V1
```

The task shall not create, publish, or claim Dataset V1.

---

# 14. Required Artifacts

## 14.1 Executable Smoke Entry Point

Repository-consistent path, for example:

```text
scripts/run_simulation_smoke.py
```

## 14.2 Focused Tests

For example:

```text
tests/test_simulation_smoke.py
```

## 14.3 Machine-readable Evidence

Mandatory:

```text
results/simulation/SIM-002_smoke_runtime.json
```

## 14.4 Human-readable Report

Mandatory:

```text
docs/simulation/simulation_smoke_runtime_v1.md
```

## 14.5 Task History

According to repository convention.

Independent review history is recorded separately after the read-only review.

---

# 15. Mandatory SIM-002 Evidence Schema

The evidence shall contain at least:

```text
task_id
implementation_complete
decision
generation_timestamp
generation_git_head
worktree_state

sim_001_binding:
  evidence_path
  evidence_sha256
  profile_path
  profile_sha256
  acceptance_path
  acceptance_sha256
  reviewed_commit

smoke_entry_point
smoke_entry_point_sha256

scenario_results

boundedness
determinism

physical_dependency
physical_motion_executed
physical_camera_dependency
physical_teleop_dependency

training_dependency
dataset_v1_created
week_authorization_modified

process_cleanup

source_bindings

authorization_snapshot

payload_sha256
```

Allowed decision values exactly:

```text
SIM_SMOKE_READY
SIM_SMOKE_BLOCKED
```

`implementation_complete=true` shall never imply `SIM_SMOKE_READY`.

---

# 16. Required Checks

```text
C01 SIM-001 consumer eligibility PASS
C02 Smoke entry point exists
C03 Success scenario behaves according to profile
C04 Failure scenario behaves according to profile
C05 Timeout is bounded
C06 Unknown/reconcile behavior correct where applicable
C07 Determinism verified
C08 No physical robot dependency
C09 No physical camera dependency
C10 No physical motion
C11 No physical teleoperation dependency
C12 No training dependency
C13 No Dataset V1 produced
C14 No W-task authorization changed
C15 No incompatible public contract introduced
C16 Runtime/process cleanup PASS
C17 Focused tests PASS
C18 Relevant regression PASS
C19 Evidence/source bindings valid
C20 Final decision consistent with mandatory checks
```

---

# 17. Decision Rules

Return:

```text
SIM_SMOKE_READY
```

only when:

- accepted SIM-001 is READY;
- required smoke scenarios execute within bounds;
- deterministic semantics match the accepted profile;
- no physical dependency exists;
- no Week authorization is changed;
- no new incompatible public contract is introduced;
- evidence integrity passes.

Return:

```text
SIM_SMOKE_BLOCKED
```

when any mandatory smoke requirement cannot be satisfied without violating the accepted SIM-001 profile or frozen architecture.

Do not modify SIM-001 semantics to obtain READY.

---

# 18. Independent Acceptance Artifact

Independent acceptance is separate from implementation evidence.

The authoritative post-review acceptance artifact shall be:

```text
results/reviews/SIM-002_acceptance.json
```

It shall be created only in a separate post-review recording step.

The READ-ONLY reviewer shall not create it.

Minimum fields:

```text
task_id: TASK-SIM-002

review_decision:
  ACCEPT
  or
  REJECT

task_specific_decision:
  SIM_SMOKE_READY
  or
  SIM_SMOKE_BLOCKED

reviewed_commit

evidence_path
evidence_sha256

smoke_report_path
smoke_report_sha256

review_record_path
review_record_sha256

sim_001_acceptance_sha256

recorded_at
recording_commit
```

Mandatory binding:

```text
acceptance.evidence_sha256
==
SHA256(results/simulation/SIM-002_smoke_runtime.json)

acceptance.smoke_report_sha256
==
SHA256(docs/simulation/simulation_smoke_runtime_v1.md)
```

Self-reported fields inside implementation evidence have no independent acceptance authority.

---

# 19. Consumer Eligibility for TASK-SIM-GATE

SIM-002 may be consumed as a READY predecessor only when:

```text
independent review decision = ACCEPT

AND

task-specific decision = SIM_SMOKE_READY

AND

acceptance evidence hash =
current canonical SIM-002 evidence hash

AND

acceptance report hash =
current canonical smoke report hash

AND

SIM-002 acceptance remains bound to the accepted SIM-001 revision
```

Invariant:

```text
ACCEPT + SIM_SMOKE_BLOCKED
=
trustworthy blocked result

ACCEPT + SIM_SMOKE_BLOCKED
!=
SIM_GO eligibility
```

---

# 20. Out of Scope

Do not:

- implement a full simulator;
- implement physical adapters;
- implement Week tasks;
- modify P0-004R authorization;
- access real hardware;
- train models;
- create Dataset V1;
- provision paid resources;
- freeze candidate hardware;
- create new public lower-level actuator ports.

---

# 21. Validation Requirements

At minimum:

1. verify SIM-001 consumer eligibility before implementation;
2. run focused smoke tests;
3. run success/failure/timeout scenarios;
4. verify determinism;
5. verify process cleanup;
6. verify physical independence;
7. verify no W authorization mutation;
8. verify no Dataset V1 artifact;
9. verify evidence schema and hashes;
10. run relevant repository regression/static checks;
11. run `git diff --check`.

---

# 22. Required Implementation Report

Return:

```markdown
# Implementation Result — TASK-SIM-002

## Predecessor Eligibility

## Files Changed

## Smoke Entry Point

## Scenarios

## Determinism / Boundedness

## Physical / Dataset / Training Isolation

## Tests

## Evidence

## Task-specific Decision

## Independent Acceptance

## Downstream Eligibility

## Repository Check

## Final Status
```

Required state separation:

```text
TASK-SIM-002 implementation:
complete | incomplete

Task-specific decision:
SIM_SMOKE_READY | SIM_SMOKE_BLOCKED

Independent acceptance:
pending

TASK-SIM-GATE readiness eligibility:
false
```

The gate eligibility remains false until separate independent acceptance and immutable bindings satisfy Section 19.

---

# 23. Final Completion Rule

Implementation is complete when:

- predecessor eligibility was valid before work started;
- required smoke artifacts exist;
- all mandatory checks are evaluated;
- boundedness and cleanup pass;
- evidence integrity passes;
- no downstream task was started.

Only:

```text
ACCEPT
+
SIM_SMOKE_READY
```

with valid bindings may be consumed by `TASK-SIM-GATE` as a READY predecessor.
