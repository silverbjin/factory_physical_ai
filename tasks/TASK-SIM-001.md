# TASK-SIM-001 — Simulation Contract Profile

> Lane: Simulation  
> Type: Contract Profile / Architecture Readiness Task  
> Status: READY_FOR_IMPLEMENTATION after frozen Simulation Lane architecture  
> Governing ADR: `docs/architecture/adr/ADR-Simulation-Lane-v1.md`  
> Governing Mapping: `context/simulation_task_mapping_v1.md`  
> Downstream Consumer: `TASK-SIM-002`  
> Physical Authorization: NONE

---

# 1. Purpose

Define the exact existing architecture and contract surface that the Simulation Lane is allowed to emulate.

This task answers:

> Which existing project-facing boundaries must a deterministic simulation fixture implement so that later simulation execution can validate software behavior without introducing new actuator ownership or silently redefining the frozen architecture?

This task shall profile existing boundaries and produce a trustworthy machine-readable contract-readiness result.

It shall **not** invent executable APIs merely because later simulation work needs them.

---

# 2. Core State Model

The following states are distinct and shall never be conflated:

```text
Implementation completion
≠
Task-specific decision
≠
Independent acceptance
≠
Downstream authorization
```

This task may therefore complete with either:

```text
SIM_CONTRACT_PROFILE_READY
```

or:

```text
SIM_CONTRACT_PROFILE_BLOCKED
```

An independently accepted `SIM_CONTRACT_PROFILE_BLOCKED` means only that the blocked result is trustworthy.

It does **not** authorize `TASK-SIM-002`.

---

# 3. Required Context

The implementation and review of `TASK-SIM-001` shall use exactly the following authoritative project sources:

```text
docs/architecture/adr/ADR-Simulation-Lane-v1.md
context/simulation_task_mapping_v1.md
docs/architecture/system_architecture_v1.md
docs/contracts/contract_plan.md
docs/contracts/simulation_execution_contract_v1.md
docs/contracts/schemas/simulation_execution_contract_v1.schema.json
results/reviews/SIM-C01_acceptance.json
docs/hardware/hardware_target_selection_status_v1.md
docs/architecture/adr/ADR-001-manipulator.md
docs/architecture/adr/ADR-002-amr.md
docs/architecture/adr/ADR-005-camera-observation.md
docs/architecture/adr/ADR-010-deployment-topology.md
results/phase0/P0-004R_vla_readiness.json
```

These files form the bounded authoritative context for this task. The delegated Simulation Lane contract and schema are authoritative only after `TASK-SIM-C01` has been independently accepted with valid immutable bindings.

Additional files may be inspected only as supporting implementation context and shall not override the Required Context.

The implementer shall not select additional documents as higher-authority sources merely because they make the task easier to complete.

If authoritative Required Context sources conflict and no repository-defined precedence rule resolves the conflict:

```text
TASK-SIM-001 decision =
SIM_CONTRACT_PROFILE_BLOCKED
```

The task shall not silently reconcile conflicting authoritative sources.

---

# 4. Preconditions

Before implementation:

1. `ADR-Simulation-Lane-v1.md` is `FROZEN`.
2. `simulation_task_mapping_v1.md` is `FROZEN`.
3. Existing P0 evidence remains unchanged.
4. Existing Week-task authorization remains governed by P0-004R.
5. No physical execution authorization is granted by this task.
6. No lower-level public port is assumed to exist unless already authoritative.
7. The project-wide contract plan remains planning-only; any accepted Simulation Lane executable-contract delegation must be evaluated only within its explicitly scoped authority.
8. A revised-contract re-evaluation requires a valid `SIM-C01_acceptance.json` with `review_decision = ACCEPT`, `task_specific_decision = SIM_CONTRACT_GAPS_RESOLVED`, and bindings to the current contract, schema, C01 evidence, reviewed commit, and frozen-authority checks. Missing or stale acceptance keeps this task blocked.

---

# 5. Scope

The task shall inspect and profile the applicable existing boundaries, including where authoritative:

```text
Deterministic Mission Executor
Navigation Skill boundary
VLA Skill boundary
Verification boundary
```

The task shall identify:

- ownership;
- request concept;
- result concept;
- failure semantics;
- timeout semantics;
- reconciliation relationship;
- authorization boundary;
- executable-contract status.

The task shall not implement simulator behavior.

---

# 6. Sources of Truth and Authority Rules

Authority order is:

```text
Frozen architecture / ADRs
→ frozen Simulation Lane mapping
→ authoritative contract plan
→ accepted Simulation Lane executable contract and schema, when validly delegated
→ accepted P0 authorization evidence
→ implementation conventions
```

Implementation code and future simulation needs are **not** sources of truth for contract semantics.

If an executable API is absent from the authoritative contract, do not infer one from desired implementation shape.

---

# 7. Required Boundary Classification

For each applicable boundary classify exactly one:

```text
EXECUTABLE_CONTRACT_AVAILABLE
PLANNING_CONTRACT_ONLY
PARTIALLY_DEFINED
NOT_DEFINED
```

At minimum classify:

## 7.1 Mission Executor Boundary

Record, where authoritative:

- invocation semantics;
- state preconditions;
- action lifecycle;
- completion representation;
- failure representation;
- reconciliation relationship.

## 7.2 Navigation Skill Boundary

Record:

- request concept;
- result concept;
- failure concept;
- timeout behavior;
- ownership;
- whether an executable contract exists.

## 7.3 VLA Skill Boundary

Record:

- request concept;
- skill/action result concept;
- prohibited direct actuator ownership;
- uncertainty/failure semantics;
- authorization boundary;
- whether an executable contract exists.

## 7.4 Verification Boundary

Record:

- observation/result verification;
- expected versus actual state;
- success/reconcile/escalate semantics;
- whether an executable contract exists.

---

# 8. Frozen Contract Boundary

The Simulation Lane shall preserve the existing conceptual topology:

```text
Deterministic Mission Executor
        │
        ├── Navigation Skill
        ├── VLA Skill
        └── Verification
```

Simulation fixtures shall sit behind those boundaries.

The task shall not introduce direct mission-layer actuator interfaces such as:

```text
ManipulatorPort
NavigationPort
ObservationPort
```

as frozen public architecture merely to simplify simulation.

If such a lower-level abstraction is genuinely required, this task must return:

```text
SIM_CONTRACT_PROFILE_BLOCKED
```

and report a contract-gap finding requiring a separate versioned contract/ADR task.

---

# 9. No Direct Actuator Ownership

The VLA boundary shall not be redefined into a direct:

```text
joint command
motor command
gripper command
trajectory command
```

contract.

Simulation may emulate:

- skill invocation;
- skill result;
- timeout;
- failure;
- unknown/ambiguous outcome;
- reconciliation;
- verification.

It may not silently redefine actuator ownership.

---

# 10. Deterministic Fixture Profile

For each boundary that is sufficiently defined, specify the minimum deterministic fixture semantics needed by `TASK-SIM-002`.

Recommended cases:

```text
known request
→ deterministic success

known request
→ deterministic failure

known request
→ deterministic timeout

ambiguous outcome
→ reconciliation / blocked completion
```

The fixture profile describes required behavior only.

It does not implement it.

---

# 11. Dataset Boundary

Simulation fixtures shall use simulation-specific naming.

Recommended identifier:

```text
SIM_FIXTURE_SET_V1
```

Invariant:

```text
SIM_FIXTURE_SET_V1
!=
Dataset V1
```

Simulation fixtures may represent:

- deterministic observations;
- fixed request/result pairs;
- deterministic failure scenarios;
- timeout scenarios.

They do not constitute the existing Dataset V1 deliverable.

---

# 12. Training Boundary

This task shall not require:

- SmolVLA fine-tuning;
- optimizer execution;
- training compute;
- remote GPU provisioning;
- Dataset V1.

A deterministic VLA fixture may be profiled only if consistent with the authoritative contract boundary.

---

# 13. Physical Exclusions

The profile must explicitly exclude:

- real robot device access;
- real camera access;
- physical motion;
- physical gripper commands;
- physical teleoperation;
- physical E-stop execution;
- vendor-specific hardware dependency.

Candidate hardware recorded in `hardware_target_selection_status_v1.md` is informational only and shall not be treated as frozen architecture.

---

# 14. Required Artifacts

## 14.1 Human-readable Contract Profile

Mandatory:

```text
docs/simulation/simulation_contract_profile_v1.md
```

## 14.2 Machine-readable Evidence

Mandatory:

```text
results/simulation/SIM-001_contract_profile.json
```

## 14.3 Task History

Create/update according to repository conventions, for example:

```text
docs/task_history/TASK-SIM-001/01_implementation.md
docs/task_history/TASK-SIM-001/README.md
docs/task_history/README.md
```

Independent review history is recorded separately after the read-only review.

---

# 15. Mandatory Machine-readable Evidence Schema

The machine-readable evidence shall contain at least:

```text
task_id
implementation_complete
decision
generation_timestamp
generation_git_head
worktree_state

governing_adr:
  path
  sha256

simulation_mapping:
  path
  sha256

system_architecture:
  path
  sha256

contract_plan:
  path
  sha256

simulation_execution_contract:
  path
  sha256

simulation_execution_schema:
  path
  sha256

sim_c01_acceptance:
  path
  sha256

p0_004r_authorization:
  path
  sha256

profile:
  path
  sha256

boundary_classification:
  mission_executor
  navigation_skill
  vla_skill
  verification

executable_contract_status

direct_actuator_contract_introduced

physical_dependency_required
training_required
dataset_v1_required
week_authorization_modified

unresolved_contract_gaps

source_bindings
final_authorization_snapshot

payload_sha256
```

Allowed `decision` values are exactly:

```text
SIM_CONTRACT_PROFILE_READY
SIM_CONTRACT_PROFILE_BLOCKED
```

`implementation_complete=true` shall never imply `SIM_CONTRACT_PROFILE_READY`.

---

# 16. Required Checks

The evidence shall explicitly evaluate:

```text
C01 Governing Simulation ADR frozen
C02 Simulation task mapping frozen
C03 Required Context resolved
C04 Existing architecture located
C05 Mission execution boundary identified
C06 Navigation Skill boundary classified
C07 VLA Skill boundary classified
C08 Verification boundary classified
C09 Executable/planning status truthful
C10 Direct actuator ownership absent
C11 Deterministic fixture semantics defined where supported
C12 Failure path defined where supported
C13 Timeout behavior defined where supported
C14 Reconciliation relationship defined where applicable
C15 Physical dependency absent
C16 Dataset V1 not aliased
C17 Training not required
C18 Week authorization unchanged
C19 No existing contract silently rewritten
C20 Evidence/profile/source bindings internally consistent
```

---

# 17. Decision Rules

Return:

```text
SIM_CONTRACT_PROFILE_READY
```

only when the authoritative sources provide sufficient semantics for `TASK-SIM-002` to implement the bounded deterministic smoke runtime without inventing a new incompatible public contract.

When a Simulation Lane executable-contract delegation exists, validate its semantic contract and structural schema directly. Do not infer executable readiness from implementation code, task completion, or self-reported acceptance. Missing, invalid, stale, or unaccepted contract/schema bindings require `SIM_CONTRACT_PROFILE_BLOCKED`.

Return:

```text
SIM_CONTRACT_PROFILE_BLOCKED
```

when any required simulation semantics remain too ambiguous or insufficiently authoritative.

Examples of valid blockers:

- VLA Skill exists conceptually but no sufficiently precise executable request/result semantics exist;
- timeout semantics are missing but required by the planned smoke path;
- reconciliation behavior is undefined;
- architecture sources conflict;
- simulation would require a new lower-level public interface.

Do not weaken the contract requirements to obtain READY.

---

# 18. Independent Acceptance Binding

Independent acceptance is separate from implementation evidence.

The authoritative post-review acceptance artifact shall be:

```text
results/reviews/SIM-001_acceptance.json
```

It shall be created only during the separate **post-review recording step**, after an independent READ-ONLY review.

The READ-ONLY reviewer itself shall not create this file.

Minimum fields:

```text
task_id: TASK-SIM-001

review_decision:
  ACCEPT
  or
  REJECT

task_specific_decision:
  SIM_CONTRACT_PROFILE_READY
  or
  SIM_CONTRACT_PROFILE_BLOCKED

reviewed_commit

evidence_path
evidence_sha256

profile_path
profile_sha256

review_record_path
review_record_sha256

recorded_at
recording_commit
```

Mandatory bindings:

```text
acceptance.evidence_sha256
==
SHA256(results/simulation/SIM-001_contract_profile.json)

acceptance.profile_sha256
==
SHA256(docs/simulation/simulation_contract_profile_v1.md)
```

A self-reported field such as:

```text
accepted: true
```

inside implementation-generated evidence has no independent acceptance authority.

---

# 19. Consumer Eligibility Rule

`TASK-SIM-001` is eligible for consumption by `TASK-SIM-002` only when all are true:

```text
implementation_complete = true

independent review decision = ACCEPT

task-specific decision =
SIM_CONTRACT_PROFILE_READY

acceptance evidence hash =
current canonical SIM-001 evidence hash

acceptance profile hash =
current canonical profile hash

reviewed commit exists in Git

no authoritative source binding mismatch exists
```

The following states explicitly prohibit `TASK-SIM-002`:

```text
acceptance missing
acceptance pending
acceptance rejected
decision missing
decision ambiguous
SIM_CONTRACT_PROFILE_BLOCKED
evidence hash mismatch
profile hash mismatch
acceptance binding mismatch
```

Invariant:

```text
ACCEPT + BLOCKED
=
trustworthy blocked result

ACCEPT + BLOCKED
!=
downstream authorization
```

---

# 20. Out of Scope

Do not:

- implement simulation fixtures;
- implement smoke runtime;
- implement full simulator behavior;
- run physical hardware;
- modify Week-task mapping;
- change P0-004R;
- freeze candidate hardware;
- train a model;
- collect Dataset V1;
- introduce new public lower-level ports.

---

# 21. Validation Requirements

At minimum:

1. validate all Required Context paths;
2. hash authoritative sources;
3. validate the delegated executable-contract schema and machine-readable evidence schema;
4. verify profile/evidence consistency;
5. verify no W-task authorization modification;
6. verify no physical authorization;
7. verify no Dataset V1 alias;
8. verify no direct actuator ownership;
9. run relevant repository regression/static checks;
10. run `git diff --check`.

---

# 22. Required Implementation Report

Return:

```markdown
# Implementation Result — TASK-SIM-001

## Required Context

## Boundary Classification

## Contract Gaps

## Fixture Profile

## Physical / Dataset / Training Boundaries

## Checks

## Evidence

## Repository Validation

## Task-specific Decision

## Independent Acceptance

## Downstream Eligibility

## Final Status
```

Required final state separation:

```text
TASK-SIM-001 implementation:
complete | incomplete

Task-specific decision:
SIM_CONTRACT_PROFILE_READY | SIM_CONTRACT_PROFILE_BLOCKED

Independent acceptance:
pending

TASK-SIM-002 authorized:
false
```

`TASK-SIM-002 authorized` remains false until separate independent acceptance and post-review acceptance binding satisfy Section 19.

---

# 23. Final Completion Rule

Implementation is complete when:

- all required artifacts exist;
- all Required Context bindings are recorded;
- all C01–C20 checks are evaluated;
- evidence/profile agree;
- repository validation passes;
- no downstream implementation was started.

The task becomes independently accepted only after separate review.

Only:

```text
ACCEPT
+
SIM_CONTRACT_PROFILE_READY
```

with valid immutable bindings may authorize `TASK-SIM-002`.
