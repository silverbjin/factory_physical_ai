# TASK-SIM-C01 — Executable Simulation Contract Gap Resolution

> Lane: Simulation
> Type: Executable Contract Definition / Contract Gap Resolution
> Status: READY_FOR_IMPLEMENTATION
> Predecessor: `TASK-SIM-001` accepted blocked assessment
> Downstream Consumer: `TASK-SIM-001` re-evaluation
> Physical Authorization: NONE
> Runtime Implementation: FORBIDDEN
> `TASK-SIM-002` Authorization: NONE

---

# 1. Purpose

Resolve the six executable-contract gaps identified by `TASK-SIM-001` by defining the smallest protocol-neutral, simulation-only executable contract required for deterministic Simulation Lane validation.

This task shall convert the applicable planning-only contract surface into a bounded executable contract **only for Simulation Lane v1**.

This task shall not:

* implement the simulation runtime;
* implement deterministic skill fixtures;
* implement ROS/Nav2/MoveIt adapters;
* authorize physical execution;
* turn the entire project contract plan into an executable production contract;
* authorize `TASK-SIM-002`.

The intended flow is:

```text
accepted TASK-SIM-001 BLOCKED result
        ↓
TASK-SIM-C01
        ↓
simulation-only executable contract
        ↓
independent review
        ↓
SIM_CONTRACT_GAPS_RESOLVED
        ↓
TASK-SIM-001 re-evaluation
        ↓
SIM_CONTRACT_PROFILE_READY | BLOCKED
```

---

# 2. Core State Model

The following states are distinct:

```text
TASK-SIM-C01 implementation completion
≠
TASK-SIM-C01 task-specific decision
≠
Independent acceptance
≠
TASK-SIM-001 re-evaluation authorization
≠
TASK-SIM-002 authorization
```

Allowed task-specific decisions are exactly:

```text
SIM_CONTRACT_GAPS_RESOLVED
SIM_CONTRACT_GAPS_BLOCKED
```

An independently accepted:

```text
SIM_CONTRACT_GAPS_BLOCKED
```

means only that the blocker assessment is trustworthy.

It does not authorize modification or execution of `TASK-SIM-002`.

Likewise:

```text
SIM_CONTRACT_GAPS_RESOLVED
```

does not itself mean:

```text
SIM_CONTRACT_PROFILE_READY
```

Only a later rerun of `TASK-SIM-001` may produce that decision.

---

# 3. Analysis Baseline

The implementation is based on the analyzed repository state:

```text
Branch:
task/p0-SIM-

HEAD:
360c42ef2c61374788dfa0fdc36088305c309960
```

Analyzed authoritative bindings include:

```text
docs/simulation/simulation_contract_profile_v1.md
43da41ade5cf53230afc46b3092b733611f0c5989f4e8769286c67aa4a171d7a

results/simulation/SIM-001_contract_profile.json
98ae08b1ba664f7be42551a84b112608409362be5615c78a57f256a935a86559

tasks/TASK-SIM-001.md
7d2d097558a60e4806635e0a09abd8f61118e08bd039d8f5473e1943c49b85fb

docs/contracts/contract_plan.md
aa7f9fe1477d650b3648c18d5df1fb3b0dabc6d06df6eff33e28dcdcc05e87d0

docs/architecture/system_architecture_v1.md
50e57f517cf613b5b8e26e31ec74965d03c729526b94f39d9423fa0a15371e3d

docs/architecture/adr/ADR-Simulation-Lane-v1.md
1509577842464f48055f402f5a3f717efecaba77847ff4c70534d14086fb46e0

context/simulation_task_mapping_v1.md
c0cf1671d97f4cec768de1a2836b8ecdd89c7ceace947bab108ab549c11396b2

results/phase0/P0-004R_vla_readiness.json
f705896b9b6a48b08dde7401dfd3ca848d9fc46ac2711bd90fdd04d8b29f873d
```

Before implementation, recompute these bindings.

If a material authoritative source has changed since this analysis, do not silently implement against the stale analysis.

Return:

```text
SIM_CONTRACT_GAPS_BLOCKED
```

and report the changed source unless the current repository content can be proven semantically equivalent and the change is unrelated to the six gaps.

---

# 4. Required Context

Read and bind at minimum:

```text
docs/simulation/simulation_contract_profile_v1.md
results/simulation/SIM-001_contract_profile.json

tasks/TASK-SIM-001.md

docs/contracts/contract_plan.md
docs/architecture/system_architecture_v1.md

docs/architecture/adr/ADR-Simulation-Lane-v1.md
context/simulation_task_mapping_v1.md

docs/architecture/adr/ADR-001-manipulator.md
docs/architecture/adr/ADR-002-amr.md
docs/architecture/adr/ADR-005-camera-observation.md
docs/architecture/adr/ADR-010-deployment-topology.md

docs/hardware/hardware_target_selection_status_v1.md

results/phase0/P0-004R_vla_readiness.json
```

Inspect accepted architecture-freeze evidence as supporting context where necessary.

Supporting evidence shall not silently override the named authoritative sources.

---

# 5. Exact Contract Gaps

The following six findings are authoritative inputs to this task and shall not be renamed, merged, split, or weakened.

## GAP-SIM-001 — Mission Executor

> “no executable Mission Executor invocation, state-transition, completion, or failure contract exists.”

Required resolution:

* protocol-neutral mission invocation;
* concrete request/result validation;
* canonical mission lifecycle;
* legal transitions;
* terminal completion semantics;
* failure semantics;
* idempotency semantics;
* Mission Executor ownership.

---

## GAP-SIM-002 — Navigation Skill

> “no executable Navigation Skill request/result or action-status reconciliation interface exists.”

Required resolution:

* Navigation Skill invocation;
* request/result schema;
* stable `action_id`;
* bounded timeout;
* typed failure;
* navigation result semantics;
* action-status lookup linkage;
* reconciliation linkage.

No raw Nav2 interface shall be exposed.

---

## GAP-SIM-003 — VLA Skill

> “no executable VLA Skill request/result, uncertainty, or bounded action interface exists.”

Required resolution:

* bounded VLA Skill invocation;
* approved semantic task;
* immutable synthetic observation references;
* concrete request/result schema;
* typed uncertainty/failure;
* stable `action_id`;
* bounded action outcome;
* verification linkage.

No raw actuator or controller interface shall be exposed.

---

## GAP-SIM-004 — Verification

> “no executable Verification request/result schema or deterministic acceptance-threshold contract exists.”

Required resolution:

* concrete verification request/result schema;
* operational result separated from verification verdict;
* deterministic pass/fail/uncertain semantics;
* expected-versus-observed predicates;
* mismatch representation;
* verification-profile version;
* immutable evidence references.

---

## GAP-SIM-005 — Lifecycle / Reconciliation

> “timeout and reconciliation rules are conceptual, but callable status lookup, concrete lifecycle values, and compatibility behavior are not executable contracts.”

Required resolution:

* concrete action lifecycle;
* legal transition table;
* timeout → `unknown`;
* callable action-status lookup;
* reconciliation semantics;
* retry guards;
* compatibility/version behavior;
* fail-closed handling of unsupported state/version values.

---

## GAP-SIM-006 — Observation Fixture

> “synthetic observation references are authorized conceptually, but their executable fixture shape and validation rules are undefined.”

Required resolution:

* immutable simulation observation references;
* fixture identity/version/hash;
* fixture manifest validation;
* `SIM_FIXTURE_SET_V1` identity;
* deterministic observation semantics;
* explicit physical-camera exclusion;
* explicit Dataset V1 exclusion.

---

# 6. Authority Model

Create:

```text
docs/contracts/simulation_execution_contract_v1.md
```

as the normative executable contract for Simulation Lane v1.

Create:

```text
docs/contracts/schemas/simulation_execution_contract_v1.schema.json
```

as the machine-verifiable structural contract.

The authority relationship shall become:

```text
Frozen architecture / ADRs
        ↓
Frozen Simulation Lane mapping
        ↓
docs/contracts/contract_plan.md
        ↓
Simulation Lane executable-contract delegation
        ↓
simulation_execution_contract_v1.md
        +
simulation_execution_contract_v1.schema.json
```

`contract_plan.md` itself remains a general planning contract.

It shall explicitly state that only the Simulation Lane v1 contract delegated to:

```text
simulation_execution_contract_v1.md
```

and its schema is executable for the scoped simulation boundary.

No physical/native integration contract becomes executable merely because this task completes.

---

# 7. Frozen Topology

The following topology shall remain unchanged:

```text
Deterministic Mission Executor
        │
        ├── Navigation Skill
        ├── VLA Skill
        └── Verification
```

Simulation fixtures sit behind these boundaries.

This task shall not introduce:

```text
Mission → NavigationPort
Mission → ManipulatorPort
Mission → ObservationPort
Mission → JointController
Mission → ros2_control
Mission → raw ROS command
```

or equivalent new public lower-level interfaces.

If resolving any gap requires changing this topology:

```text
decision = SIM_CONTRACT_GAPS_BLOCKED
```

and an ADR/architecture change shall be proposed as a separate task.

---

# 8. Protocol-Neutral Operations

The executable Simulation Lane v1 contract shall define exactly the following logical operation identifiers:

```text
mission.execute
navigation.execute
vla.execute
action_status.get
verification.verify
```

These identifiers are protocol-neutral.

They shall not prescribe:

* Python class names;
* Python method names;
* ROS topic names;
* ROS service names;
* ROS Action names;
* HTTP endpoints;
* gRPC methods;
* DDS QoS;
* Nav2 action endpoints;
* MoveIt action endpoints.

Mapping these protocol-neutral operations to concrete runtime calls belongs to later implementation work such as `TASK-SIM-002`.

---

# 9. Common Request Envelope

Applicable operation requests shall use an explicitly versioned envelope.

Required fields where applicable:

```text
schema_version
mission_id
request_id
trace_id
timestamp
deadline_at
timeout_ms
component_version
```

Side-effecting requests shall additionally contain:

```text
idempotency_key
```

Action-producing Navigation/VLA requests shall additionally contain:

```text
action_id
attempt
retry_budget_remaining
```

Requirements:

* identifiers shall be structurally validated;
* timestamps shall be validated;
* timeout shall be positive and bounded;
* deadline shall be explicit;
* unsupported `schema_version` shall fail closed;
* identity or lifecycle values shall never be silently defaulted.

---

# 10. Common Result Envelope

Applicable results shall define:

```text
schema_version
mission_id
request_id
trace_id
timestamp
component_version
source_kind
status
result
```

Where action-bound:

```text
action_id
```

Allowed logical `result` values shall be explicitly bounded, including where applicable:

```text
success
failure
pending
requires_human
```

For non-success results, define:

```text
error:
  code
  message
  category
  retryable
```

Requirements:

```text
source_kind = mock
```

for Simulation Lane v1 fixtures/runtime evidence.

A non-success result requiring an error shall not be accepted without the error object.

False-success payloads shall fail validation.

Do not introduce a duplicate top-level `retryable` field where `error.retryable` is the authoritative location.

---

# 11. Mission Execution Contract

`mission.execute` shall define:

## Request

A validated structured mission request containing the minimum existing canonical mission information, including where applicable:

```text
mission_id
request_id
trace_id
idempotency_key
timestamp
deadline_at
timeout_ms
structured mission goal
priority
part identity
quantity
source/destination context
approval context
```

Use existing repository terminology where a canonical field name already exists.

Do not create duplicate aliases.

## Result

At minimum:

```text
mission state
checkpoint/revision reference
outcome
failure/error where applicable
HITL request where applicable
```

Only the deterministic Mission Executor may mutate mission lifecycle state.

The LLM/Agent may propose semantics but shall not commit runtime mission state.

## Mission Lifecycle

Use the existing repository's canonical mission-state vocabulary where unambiguous.

The executable contract shall define:

* every allowed state;
* legal transition table;
* initial state;
* terminal success state;
* terminal failure/escalation state;
* relationship to action reconciliation.

If the existing authoritative sources contain incompatible mission lifecycle vocabularies that cannot be normalized without an architectural decision:

```text
SIM_CONTRACT_GAPS_BLOCKED
```

shall be returned.

Do not invent an unrelated replacement workflow engine.

---

# 12. Navigation Skill Contract

`navigation.execute` request shall contain only semantic navigation inputs permitted by the frozen architecture.

Minimum contract:

```text
destination_id
speed_profile_id
action_id
attempt
retry_budget_remaining
```

plus the common request envelope.

Explicitly forbidden fields include:

```text
raw_pose
raw_path
trajectory
planner_parameters
controller_parameters
ROS command
Nav2 command
Nav2 lifecycle command
```

The result shall provide:

* action lifecycle status;
* success/arrival representation;
* typed diagnostic failure;
* immutable evidence references where applicable;
* reconciliation linkage.

Ownership remains:

```text
Nav2:
local navigation execution
planner/controller behavior
configured local navigation recovery
Nav2 lifecycle behavior

Deterministic Runtime:
business retry budget
wait
reroute request
robot reassignment
HITL/escalation
```

Simulation contract definition shall not claim that real Nav2 was executed.

---

# 13. VLA Skill Contract

`vla.execute` shall define a bounded semantic skill interface.

Minimum request information:

```text
task_id
policy_version
observation_refs
workspace_profile_id
action_id
attempt
retry_budget_remaining
```

plus the common request envelope.

The result shall provide:

* bounded skill result;
* action status;
* uncertainty/failure representation;
* verification input references;
* latency/evidence metadata where applicable.

Explicitly forbidden request/result fields or behavior include unrestricted:

```text
joint command
motor command
gripper command
trajectory command
raw action chunks exposed as public mission API
MoveIt command ownership
ros2_control ownership
hardware-controller ownership
```

Ownership remains:

```text
VLA:
approved bounded sensorimotor manipulation policy

MoveIt:
planning scene
collision checking
named pose / pre-grasp / retreat
motion/trajectory planning and applicable execution

ros2_control:
controller lifecycle
hardware interfaces
standard joint-state/control interfaces
```

VLA shall not bypass deterministic safety boundaries.

---

# 14. Action Lifecycle Contract

The Simulation Lane executable action lifecycle shall define at minimum:

```text
requested
running
succeeded
failed
unknown
reconciling
reconciled
```

`reconciling` is an active executor phase.

`reconciled` is the durable resolution record.

The legal transition model shall include:

```text
requested -> running

requested -> failed
requested -> unknown

running -> succeeded
running -> failed
running -> unknown

unknown -> reconciling

reconciling
    -> reconciled(resolved_status=succeeded)
    -> reconciled(resolved_status=failed)
    -> reconciled(resolved_status=unknown)
```

The implementation shall mechanically validate the transition table.

Mandatory invariant:

```text
unknown -> succeeded
```

is illegal.

A successful outcome discovered after an ambiguous timeout shall use:

```text
unknown
→ reconciling
→ action_status.get
→ authoritative matching status evidence
→ reconciled(resolved_status=succeeded)
```

Only after that durable reconciliation result may the Mission Executor resume success processing.

---

# 15. Timeout Semantics

Timeout shall mean:

```text
the caller did not receive a trustworthy terminal result
within the bounded execution contract
```

It shall not mean:

```text
failure
```

and shall not mean:

```text
success
```

Required behavior:

```text
deadline exceeded
        ↓
unknown
        ↓
reconciling
        ↓
action_status.get(action_id)
```

A timeout must never be converted directly into successful mission completion.

---

# 16. Action Status Lookup Contract

`action_status.get` shall be read-only.

Request shall contain:

```text
schema_version
mission_id
request_id
trace_id
action_id
timestamp
deadline_at
timeout_ms
```

The lookup uses:

```text
same mission_id
same action_id
new request_id
```

The result shall include at minimum:

```text
mission_id
request_id
action_id
observed_at
observed_status
component_version
evidence_refs
error where applicable
```

A missing or mismatched `action_id` shall fail closed.

Reconciliation evidence must be immutable and action-bound.

---

# 17. Retry Contract

Retry is allowed only when all are true:

```text
reconciliation completed
AND
resolved_status = failed
AND
error.retryable = true
AND
retry_budget_remaining > 0
```

A retry shall retain the logical:

```text
action_id
idempotency_key
```

and shall use:

```text
new request_id
attempt = previous attempt + 1
```

Retry shall be rejected if:

```text
status is still unknown
reconciliation did not occur
retryable != true
retry budget is exhausted
identity does not match
```

No unbounded retry loop is permitted.

---

# 18. Verification Contract

`verification.verify` shall separate operational execution from business verification verdict.

## Request

At minimum:

```text
schema_version
mission_id
request_id
trace_id
action_id
verifier_id
expected_state
observation_refs
verification_profile_version
timestamp
deadline_at
timeout_ms
```

The expected state shall use existing canonical domain terminology for the required part/location predicates.

## Result

Operational result and verification verdict are separate.

Verification verdict values:

```text
pass
fail
uncertain
```

At minimum also record:

```text
confidence
mismatch_code where applicable
verification_profile_version
evidence_refs
```

A successful invocation returning:

```text
verdict = fail
```

is not an operation/transport failure.

Verification shall not itself commit mission completion.

Only the Mission Executor owns the final mission-state transition.

---

# 19. Deterministic Verification Profile

Define a versioned simulation verification profile.

The v1 deterministic rule shall semantically provide:

```text
valid synthetic observation
+
exact mandatory expected predicates match
        ↓
pass
```

```text
valid synthetic observation
+
one or more mandatory expected predicates mismatch
        ↓
fail
```

```text
observation insufficient
or
observation explicitly ambiguous
        ↓
uncertain
```

Invariant:

```text
uncertain != pass
```

For the same:

```text
normalized verification request
fixture revision
verification profile version
```

the same verdict must be produced.

No physical-camera confidence threshold shall be invented.

A numeric `confidence` value, if carried as evidence metadata, shall not silently override the deterministic predicate rules unless a separately versioned authoritative profile explicitly defines such a threshold.

---

# 20. Simulation Observation Contract

Define:

```text
SimulationObservationRef
```

with at least:

```text
fixture_set_id
fixture_id
fixture_version
content_sha256
timestamp
source_kind
```

Required values:

```text
fixture_set_id = SIM_FIXTURE_SET_V1
source_kind = mock
```

Also define a minimal executable fixture-manifest structure sufficient to validate the referenced synthetic observations.

The schema shall make fixture content:

* immutable by reference/hash;
* versioned;
* deterministic;
* non-physical.

Explicit invariant:

```text
SIM_FIXTURE_SET_V1
!=
Dataset V1
```

The contract shall not require:

```text
camera serial number
/dev/video*
RealSense device ID
physical calibration file
physical camera access
physical robot state
```

Synthetic observation fixtures shall not be represented as training data or Dataset V1.

---

# 21. Schema Requirements

Create:

```text
docs/contracts/schemas/simulation_execution_contract_v1.schema.json
```

The schema shall contain reusable `$defs` for at least:

```text
CommonRequestEnvelope
CommonResultEnvelope
ContractError

MissionExecuteRequest
MissionExecuteResult

NavigationExecuteRequest
NavigationExecuteResult

VLAExecuteRequest
VLAExecuteResult

ActionStatusGetRequest
ActionStatusGetResult

VerificationRequest
VerificationResult

SimulationObservationRef
SimulationFixtureManifest
```

Requirements:

* JSON Schema shall itself validate successfully;
* required identity fields shall be mandatory;
* unsupported versions shall fail validation;
* unknown enum values shall fail validation;
* unknown public contract fields shall fail validation;
* use `additionalProperties: false` for normative public objects;
* any extension mechanism must be explicitly versioned;
* conditional requirements shall enforce error/status correctness.

No silent defaults for:

```text
identity
deadline
timeout
action status
authorization
retryability
```

are allowed.

---

# 22. Compatibility Rules

The contract shall define explicit compatibility behavior.

At minimum:

```text
supported schema version
→ validate normally

unsupported major schema version
→ fail closed

unknown enum/state
→ fail closed

unknown required operation
→ fail closed

optional explicitly versioned extension
→ permitted only under documented extension rules
```

Consumers shall not coerce unknown future states into known successful states.

---

# 23. Ownership Invariants

The executable contract shall preserve:

```text
Agent
= semantic proposal only

Deterministic Runtime / Mission Executor
= authorization, lifecycle, mission state, business recovery

Navigation Skill / Nav2
= bounded navigation execution and local recovery

VLA Skill
= approved bounded semantic manipulation skill

MoveIt
= manipulation planning and safety boundary

ros2_control
= controller/hardware interface ownership

Verification
= evidence/verdict provider, not mission completion authority
```

---

# 24. Physical / Training / Dataset Exclusions

This task grants no authorization for:

```text
physical robot access
physical camera access
physical motion
physical gripper execution
physical teleoperation
physical E-stop execution
real Nav2 execution
real MoveIt execution
real ros2_control execution
VLA fine-tuning
model training
Dataset V1 collection
remote paid GPU
candidate hardware freeze
```

Historical:

```text
P0-004R = NO_GO
```

shall remain unchanged.

---

# 25. Required File Changes

Implementation may create:

```text
docs/contracts/simulation_execution_contract_v1.md

docs/contracts/schemas/simulation_execution_contract_v1.schema.json

tests/test_simulation_execution_contract.py

results/simulation/SIM-C01_contract_resolution.json

docs/task_history/TASK-SIM-C01/01_implementation.md
docs/task_history/TASK-SIM-C01/README.md
```

Implementation may update only as required:

```text
docs/contracts/contract_plan.md

tasks/TASK-SIM-001.md

docs/task_history/README.md
```

## `contract_plan.md` change

The minimum edit shall:

1. retain its existing project-wide planning-only status;
2. add an explicit Simulation Lane executable-contract delegation;
3. reference:

   * `simulation_execution_contract_v1.md`;
   * `simulation_execution_contract_v1.schema.json`;
4. state that the delegation does not freeze physical/native interfaces.

## `TASK-SIM-001.md` change

Add the new contract and schema to its authoritative Required Context.

Add immutable bindings for both.

Require future SIM-001 evaluation to determine executable readiness from the new contract rather than inferring from implementation code.

A rerun shall preserve the historical accepted blocked assessment in task history.

Regenerating SIM-001 canonical profile/evidence shall automatically make the prior canonical acceptance binding stale until a new independent review and post-review acceptance record exist.

---

# 26. Files That Must Not Change

Do not modify:

```text
docs/simulation/simulation_contract_profile_v1.md
results/simulation/SIM-001_contract_profile.json

docs/architecture/adr/ADR-Simulation-Lane-v1.md
context/simulation_task_mapping_v1.md

docs/architecture/system_architecture_v1.md

docs/architecture/adr/ADR-001-manipulator.md
docs/architecture/adr/ADR-002-amr.md
docs/architecture/adr/ADR-005-camera-observation.md
docs/architecture/adr/ADR-010-deployment-topology.md

docs/hardware/hardware_target_selection_status_v1.md

results/phase0/P0-004R_vla_readiness.json

tasks/TASK-SIM-002.md
tasks/TASK-SIM-GATE.md

src/**
```

Do not rewrite existing accepted implementation/review history.

If resolving a gap truly requires changing a frozen architecture or ADR:

```text
SIM_CONTRACT_GAPS_BLOCKED
```

shall be returned instead.

---

# 27. Focused Contract Tests

Create:

```text
tests/test_simulation_execution_contract.py
```

This is a contract/schema validation test only.

It shall not implement the smoke runtime or production adapters.

At minimum test positive valid vectors for:

```text
mission.execute
navigation.execute
vla.execute
action_status.get
verification.verify
SimulationObservationRef
SimulationFixtureManifest
```

Required negative tests include:

```text
missing mission_id
missing request_id
missing deadline
missing required action_id

unsupported schema_version

malformed UUID
malformed timestamp
malformed SHA-256

unknown lifecycle state
unknown result
unknown error category

forbidden navigation raw pose
forbidden raw path
forbidden trajectory
forbidden ROS/Nav2 command

forbidden VLA joint/motor/gripper command
forbidden controller command

physical source_kind

Dataset V1 alias

mismatched mission_id
mismatched action_id

non-success requiring error but error absent

unknown -> succeeded direct transition

reconciliation with wrong action_id

retry before reconciliation

retry when retryable != true

retry with exhausted budget

verification uncertain treated as pass
```

---

# 28. Lifecycle Validation

The transition table shall be machine-tested.

At minimum prove:

```text
requested -> running
running -> succeeded
running -> failed
running -> unknown
unknown -> reconciling
```

are accepted where defined.

Prove:

```text
unknown -> succeeded
```

is rejected.

Prove success after timeout is possible only through:

```text
unknown
→ reconciling
→ matching action_status.get evidence
→ reconciled(resolved_status=succeeded)
```

---

# 29. Determinism Validation

For identical:

```text
normalized request
fixture_set_id
fixture_id
fixture_version
fixture content hash
verification_profile_version
initial state
```

the contract validation logic shall produce semantically identical results.

No random or wall-clock-dependent business decision shall be required by the contract.

---

# 30. Mandatory C01 Checks

Record all checks individually.

```text
C01  Analysis baseline resolved
C02  Exact six gaps preserved
C03  Simulation Lane ADR unchanged
C04  Simulation task mapping unchanged
C05  System architecture unchanged
C06  ADR-001 unchanged
C07  ADR-002 unchanged
C08  ADR-005 unchanged
C09  ADR-010 unchanged
C10  P0-004R unchanged

C11  Simulation executable contract exists
C12  JSON Schema exists and meta-validates
C13  contract_plan remains planning-only globally
C14  Simulation-only executable delegation exists
C15  TASK-SIM-001 Required Context updated

C16  mission.execute executable semantics defined
C17  navigation.execute executable semantics defined
C18  vla.execute executable semantics defined
C19  verification.verify executable semantics defined
C20  action_status.get executable semantics defined
C21  synthetic fixture contract defined

C22  lifecycle transition table executable
C23  timeout -> unknown semantics executable
C24  unknown -> succeeded prohibited
C25  reconciliation evidence requirements executable
C26  bounded retry guard executable
C27  compatibility/fail-closed rules executable
C28  deterministic verification profile executable

C29  no direct actuator public contract
C30  no physical dependency
C31  no Dataset V1 alias
C32  no training dependency
C33  no Week authorization modification
C34  no candidate hardware freeze

C35  focused positive tests PASS
C36  focused negative tests PASS
C37  relevant regression tests PASS
C38  git diff --check PASS
C39  evidence/schema/hash validation PASS
C40  final task decision consistent with all mandatory predicates
```

A mandatory failed or ambiguous check prevents:

```text
SIM_CONTRACT_GAPS_RESOLVED
```

---

# 31. Machine-readable Evidence

Create:

```text
results/simulation/SIM-C01_contract_resolution.json
```

At minimum record:

```text
task_id
implementation_complete
decision

generation_timestamp
generation_git_head
worktree_state

analysis_baseline

input_bindings

contract:
  path
  sha256

schema:
  path
  sha256

contract_plan:
  path
  sha256

task_sim_001_spec:
  path
  sha256

gap_resolution:
  GAP-SIM-001
  GAP-SIM-002
  GAP-SIM-003
  GAP-SIM-004
  GAP-SIM-005
  GAP-SIM-006

operation_identifiers

lifecycle_contract

reconciliation_contract

verification_contract

fixture_contract

frozen_source_before_after_hashes

physical_authorization_modified
week_authorization_modified
dataset_v1_introduced
training_dependency_introduced
direct_actuator_contract_introduced
architecture_modified
adr_modified

focused_tests
regression_tests
checks

unresolved_blockers

payload_sha256
```

Allowed `decision` values exactly:

```text
SIM_CONTRACT_GAPS_RESOLVED
SIM_CONTRACT_GAPS_BLOCKED
```

---

# 32. Decision Rules

Return:

```text
SIM_CONTRACT_GAPS_RESOLVED
```

only when:

1. all six exact gaps have executable authoritative coverage;
2. the human-readable contract exists;
3. the structural schema validates;
4. focused positive and negative tests pass;
5. lifecycle/reconciliation invariants pass;
6. deterministic verification semantics exist;
7. fixture semantics are executable;
8. no frozen topology is changed;
9. no physical/native authorization is introduced;
10. no Dataset V1 or training requirement is introduced;
11. no direct actuator public interface is introduced;
12. all mandatory checks pass.

Return:

```text
SIM_CONTRACT_GAPS_BLOCKED
```

if any required executable semantic remains ambiguous, contradictory, insufficiently authoritative, or requires an architecture/ADR change.

Do not weaken a contract rule merely to obtain RESOLVED.

---

# 33. Required Implementation Report

Return:

```markdown
# Implementation Result — TASK-SIM-C01

## Repository State

## Analysis Baseline Validation

## Files Changed

## Exact Six Gap Disposition

## Executable Contract

## Schema

## Operation Contracts

## Lifecycle / Timeout / Reconciliation

## Verification Contract

## Fixture Contract

## Frozen Authority Preservation

## Tests

## Checks

## Evidence

## Task-specific Decision

## Independent Acceptance

## TASK-SIM-001 Re-evaluation Eligibility

## TASK-SIM-002 Authorization

## Repository Validation

## Final Status
```

Required initial state separation:

```text
TASK-SIM-C01 implementation:
complete | incomplete

Task-specific decision:
SIM_CONTRACT_GAPS_RESOLVED | SIM_CONTRACT_GAPS_BLOCKED

Independent acceptance:
pending

TASK-SIM-001 re-evaluation authorized:
false

TASK-SIM-002 authorized:
false
```

---

# 34. Independent Review

After implementation, a separate READ-ONLY review shall verify:

* exact six-gap traceability;
* source authority;
* simulation-only executable scope;
* schema correctness;
* operation semantics;
* lifecycle transition semantics;
* timeout/unknown behavior;
* reconciliation correctness;
* retry guard correctness;
* verification determinism;
* fixture determinism;
* compatibility rules;
* no actuator ownership expansion;
* no physical authorization;
* no Dataset V1 alias;
* no training dependency;
* frozen-file hash preservation;
* test adequacy;
* evidence integrity.

The READ-ONLY reviewer shall not modify files and shall not create acceptance evidence.

---

# 35. Post-review Acceptance Artifact

After an independent review, use a separate recording step to create:

```text
results/reviews/SIM-C01_acceptance.json
```

Minimum fields:

```text
task_id: TASK-SIM-C01

review_decision:
  ACCEPT | REJECT

task_specific_decision:
  SIM_CONTRACT_GAPS_RESOLVED
  | SIM_CONTRACT_GAPS_BLOCKED

reviewed_commit

evidence_path
evidence_sha256

contract_path
contract_sha256

schema_path
schema_sha256

contract_plan_sha256
task_sim_001_spec_sha256

review_record_path
review_record_sha256

recorded_at
recording_commit
```

Self-reported acceptance inside implementation evidence has no independent authority.

---

# 36. TASK-SIM-001 Re-evaluation Eligibility

`TASK-SIM-001` may be rerun against the revised contract authority only when all are true:

```text
TASK-SIM-C01 implementation_complete = true

AND

TASK-SIM-C01 independent review = ACCEPT

AND

TASK-SIM-C01 decision =
SIM_CONTRACT_GAPS_RESOLVED

AND

acceptance hashes =
current canonical contract/schema/evidence hashes

AND

reviewed commit exists

AND

frozen authority preservation checks pass
```

Until then:

```text
TASK-SIM-001 re-evaluation authorized = false
```

Regardless of C01 result:

```text
TASK-SIM-002 authorized = false
```

---

# 37. Historical SIM-001 Preservation

The previously accepted blocked SIM-001 assessment remains valid historical evidence for the old source revision.

It shall not be rewritten as if it had originally been READY.

When SIM-001 is later rerun:

```text
old source revision
→ historical ACCEPT + SIM_CONTRACT_PROFILE_BLOCKED

new source revision
→ new implementation result
→ new independent review
→ new acceptance binding
```

The historical review/history must remain recoverable.

Once canonical SIM-001 profile/evidence are regenerated, the old canonical acceptance binding must be treated as stale for downstream authorization until a new independent acceptance record binds the new hashes.

---

# 38. Out of Scope

Do not:

* implement `TASK-SIM-002`;
* create the smoke runtime;
* create Navigation/VLA runtime fakes;
* run Gazebo/Nav2/MoveIt;
* run physical hardware;
* collect observations from a physical camera;
* collect Dataset V1;
* train/fine-tune VLA;
* modify Week tasks;
* modify P0 authorization;
* create new actuator ports;
* modify frozen architecture merely to satisfy the task;
* claim that contract resolution proves runtime correctness.

---

# 39. Final Completion Rule

Implementation is complete when:

* all required C01 artifacts exist;
* all six gap dispositions are recorded;
* contract/schema validation is complete;
* mandatory checks are evaluated;
* focused tests and applicable regression tests have run;
* evidence is internally consistent;
* no later task was started.

Task-specific success is:

```text
SIM_CONTRACT_GAPS_RESOLVED
```

Independent success is:

```text
ACCEPT
+
SIM_CONTRACT_GAPS_RESOLVED
```

Only that combination, with valid immutable bindings, authorizes a fresh `TASK-SIM-001` re-evaluation.

It never directly authorizes `TASK-SIM-002`.
