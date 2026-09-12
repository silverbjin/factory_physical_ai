# Simulation Execution Contract v1

> Status: EXECUTABLE FOR SIMULATION LANE V1
> Contract version: `1.0`
> Structural schema: `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
> Physical authorization: NONE
> Runtime implementation: OUT OF SCOPE

## 1. Authority and scope

This document is the normative protocol-neutral executable contract delegated by `docs/contracts/contract_plan.md` for Simulation Lane v1 only. The companion JSON Schema is normative for message structure. This document is normative for invocation, lifecycle, correlation, reconciliation, retry, determinism, and ownership semantics that JSON Schema cannot express by itself.

The executable logical operation identifiers are exactly:

```text
mission.execute
navigation.execute
vla.execute
action_status.get
verification.verify
```

They do not prescribe Python classes or methods, ROS topics/services/actions, HTTP endpoints, gRPC methods, DDS QoS, Nav2 endpoints, or MoveIt endpoints. Runtime bindings belong to a later authorized task.

The frozen topology remains:

```text
Deterministic Mission Executor
        |
        +-- Navigation Skill
        +-- VLA Skill
        +-- Verification
```

Simulation fixtures sit behind these boundaries. No mission-to-actuator port is created.

## 2. Normative interpretation

The key words MUST, MUST NOT, REQUIRED, SHALL, and SHALL NOT are normative.

- A message is structurally valid only when it validates against exactly one root alternative in the companion schema.
- No required identity, deadline, timeout, lifecycle, authorization, or retry value may be defaulted.
- Unknown public fields, operations, versions, enums, states, or error categories fail closed.
- The only supported `schema_version` is `1.0`.
- `timeout_ms` is bounded to the inclusive range `1..60000` for Simulation Lane v1.
- `deadline_at` MUST be later than `timestamp`; contract tests enforce this relationship.
- UUID and timestamp formats require JSON Schema format checking. Timestamp validation MUST perform RFC 3339 UTC calendar validation; matching the lexical pattern alone is insufficient.
- All Simulation Lane results and fixtures use `source_kind = mock`.
- `error.retryable` is canonical. A duplicate top-level `retryable` field is forbidden.

## 3. Common envelopes

Every operation request contains:

```text
operation
message_type = request
schema_version
mission_id
request_id
trace_id
timestamp
deadline_at
timeout_ms
component_version
```

`mission.execute`, `navigation.execute`, and `vla.execute` additionally require `idempotency_key`. Navigation and VLA requests additionally require `action_id`, `attempt`, and `retry_budget_remaining`.

Every result contains:

```text
operation
message_type = result
schema_version
mission_id
request_id
trace_id
timestamp
component_version
source_kind = mock
status
result
```

Action-bound results also contain `action_id`. Allowed `result` values are exactly `success`, `failure`, `pending`, and `requires_human` where the operation schema permits them.

Every result other than `success` MUST contain `error` with:

```text
code
message
category
retryable
```

Allowed `error.category` values are exactly:

```text
VALIDATION
AUTHORIZATION
SAFETY_POLICY
DEPENDENCY_TIMEOUT
DEPENDENCY_MALFORMED
RESOURCE_UNAVAILABLE
EXECUTION_FAILED
VERIFICATION_MISMATCH
MODEL_TIMEOUT
MODEL_FAILURE
CANCELLED
INTERNAL
```

`DEPENDENCY_TIMEOUT` and `MODEL_TIMEOUT` are both timeout categories. For Navigation and VLA action results, either category MUST use `result = pending`, `status = unknown`, and reconciliation. A known terminal model failure uses `MODEL_FAILURE`, not `MODEL_TIMEOUT`.

A `success` result MUST NOT carry `error`. Structural validity does not itself authorize a mission transition; Sections 5–10 govern semantics.

## 4. Identity, idempotency, and compatibility

- `mission_id` MUST match across related calls.
- `request_id` MUST be new for every invocation.
- `trace_id` MAY equal `mission_id`.
- `action_id` remains stable through timeout, lookup, reconciliation, and safe retry.
- `idempotency_key` remains stable across safe retries of one logical side effect.
- A retry increments `attempt` by exactly one and uses a new `request_id`.
- A consumer supporting `1.0` MUST reject every other `schema_version`.
- Unknown states MUST NOT be coerced to `succeeded`, `completed`, `pass`, or another success value.
- There is no implicit extension mechanism. Adding a public field requires a versioned contract change.

## 5. `mission.execute`

### 5.1 Request

`MissionExecuteRequest` contains the common request envelope, `idempotency_key`, and a structured `goal`:

```text
mission_type = line_side_supply
priority: integer 0..100
line_id
part_id
quantity: integer >= 1
source_id
destination_id
approval_context:
  simulation_only = true
  approved = true
  authorized_by
```

The Agent may propose this semantic goal. Only the Deterministic Mission Executor validates authorization and mutates mission state.

### 5.2 Result and lifecycle

`MissionExecuteResult` records `status`, `result`, `checkpoint_revision`, and `outcome`. `hitl_request` is required when `result = requires_human`.

Canonical mission states are:

```text
created
ready
executing
reconciling
recovering
completed
failed
escalated
```

Legal transitions are:

| From | To | Required semantic cause |
|---|---|---|
| `created` | `ready` | validated and authorized request |
| `created` | `escalated` | validation or authorization cannot proceed safely |
| `ready` | `executing` | deterministic dispatch begins |
| `ready` | `escalated` | authorization or dependency prevents dispatch |
| `executing` | `completed` | required actions succeeded and verification verdict is `pass` |
| `executing` | `reconciling` | an action becomes `unknown` |
| `executing` | `failed` | terminal non-retryable execution failure |
| `executing` | `escalated` | deterministic policy requires human action |
| `reconciling` | `completed` | reconciliation resolves `succeeded`, followed by verification `pass` |
| `reconciling` | `recovering` | reconciliation resolves retryable `failed` and retry is authorized |
| `reconciling` | `failed` | matching evidence resolves terminal failure |
| `reconciling` | `escalated` | ambiguity persists or safe recovery is unavailable |
| `recovering` | `executing` | a bounded retry is authorized and dispatched |
| `recovering` | `failed` | recovery fails terminally |
| `recovering` | `escalated` | recovery cannot proceed safely |

`completed`, `failed`, and `escalated` are terminal. Verification never mutates mission state directly.

Result consistency:

- `success` requires `status = completed`, `outcome = completed`, and no `error`.
- `failure` requires `status = failed`, `outcome = failed`, and `error`.
- `requires_human` requires `status = escalated`, `outcome = requires_human`, `error`, and `hitl_request`.
- `pending` requires a non-terminal state, `outcome = in_progress`, and `error` explaining why no trustworthy terminal result exists.

## 6. `navigation.execute`

`NavigationExecuteRequest` contains the common request envelope plus:

```text
robot_id
idempotency_key
action_id
attempt
retry_budget_remaining
destination_id
speed_profile_id
```

Only allowlisted semantic destinations and speed profiles are valid. The closed schema rejects raw pose, raw path, trajectory, planner/controller parameters, ROS/Nav2 commands, and lifecycle commands.

`NavigationExecuteResult` uses action lifecycle `status` and logical `result`.

- `success` requires `status = succeeded` and `arrival.verified = true` for the requested destination.
- `failure` requires `status = failed` and `error`.
- `pending` requires `status = running` or `unknown` and `error`; timeout uses `DEPENDENCY_TIMEOUT` with `status = unknown`.
- `requires_human` requires `status = failed` and a non-retryable `error`.

Nav2 retains local navigation execution, planner/controller behavior, configured local recovery, and lifecycle ownership. The Deterministic Mission Executor owns business retry, wait, reroute request, reassignment, and HITL/escalation. This contract makes no real Nav2 execution claim.

## 7. `vla.execute`

`VLAExecuteRequest` contains the common request envelope plus:

```text
robot_id
idempotency_key
action_id
attempt
retry_budget_remaining
task_id
policy_version
observation_refs
workspace_profile_id
```

`observation_refs` are immutable `SimulationObservationRef` objects. The request is an approved bounded semantic skill, not an actuator command.

`VLAExecuteResult` contains action `status`, logical `result`, `skill_outcome`, `verifier_input_refs`, and `latency_ms`.

- `success` requires `status = succeeded`, `skill_outcome = succeeded`, verifier references, and no `error`.
- `failure` requires `status = failed`, `skill_outcome = failed`, and `error`.
- `pending` requires `status = running` or `unknown`, `skill_outcome = uncertain`, and `error`.
- `requires_human` requires `status = failed`, `skill_outcome = uncertain`, and a non-retryable `error`.

The closed schema rejects joint, motor, gripper, trajectory, controller, raw action-chunk, MoveIt, `ros2_control`, and hardware-controller fields.

VLA owns only the approved bounded sensorimotor policy. MoveIt owns planning scene, collision checks, named poses, pre-grasp/retreat, and trajectory planning/execution. `ros2_control` owns controller lifecycle and hardware interfaces. VLA cannot bypass these boundaries.

## 8. Action lifecycle, timeout, and status lookup

Canonical action states are:

```text
requested
running
succeeded
failed
unknown
reconciling
reconciled
```

`reconciling` is the active executor phase. `reconciled` is the durable resolution record.

Legal action transitions are exactly:

```text
requested -> running
requested -> failed
requested -> unknown
running -> succeeded
running -> failed
running -> unknown
unknown -> reconciling
reconciling -> reconciled(resolved_status=succeeded|failed|unknown)
```

All other transitions fail closed. In particular, `unknown -> succeeded` is illegal.

A timeout means the caller did not receive a trustworthy terminal result before `deadline_at`/`timeout_ms`. It means neither failure nor success. The executor records `unknown` and invokes `action_status.get`.

`ActionStatusGetRequest` is read-only and uses the same `mission_id` and `action_id`, a new `request_id`, and a bounded deadline/timeout.

`ActionStatusGetResult` separates lookup-operation status from `observed_status`. A successful lookup requires immutable evidence and `observed_status = running|succeeded|failed|unknown`. Lookup failure requires `error` and provides no authoritative observed outcome.

The request/result and reconciliation record MUST match on `mission_id`, `action_id`, and lookup `request_id`. Reconciliation evidence MUST be immutable, action-bound, time-stamped, and component-versioned.

A success found after timeout follows only:

```text
unknown
-> reconciling
-> action_status.get
-> matching authoritative evidence
-> reconciled(resolved_status=succeeded)
```

Only then may the executor resume success processing.

## 9. Retry authorization

Retry is allowed only when all conditions are true:

```text
reconciliation_completed = true
resolved_status = failed
error.retryable = true
retry_budget_remaining > 0
same mission_id
same action_id
same idempotency_key
new request_id
next_attempt = previous_attempt + 1
```

`RetryAuthorization` is the machine-testable record for these inputs. Retry is rejected while status is `unknown`, before reconciliation, on non-retryable failure, when budget is exhausted, or when identity/attempt relationships do not match. Retry loops are bounded.

## 10. `verification.verify`

`VerificationRequest` contains the common request envelope plus `action_id`, `verifier_id`, `expected_state`, `observation_refs`, and `verification_profile_version`.

`ExpectedState` contains exact `part_id` and `location_id` predicates.

`VerificationResult` separates operational `result` from business `verdict = pass|fail|uncertain`. A successful invocation may return any verdict. Therefore `result = success, verdict = fail` is valid and is not an operation/transport failure. An operational failure has `result = failure`, `status = failed`, and `error`, and carries no verdict.

Simulation Lane v1 defines:

```text
verification_profile_version = sim-exact-match-v1
```

Its deterministic rule is:

```text
valid observation + exact part_id/location_id match -> pass
valid observation + either predicate mismatch -> fail
insufficient or ambiguous observation -> uncertain
```

`uncertain != pass`. Numeric confidence is evidence metadata only and does not override this rule. Identical normalized request, fixture identity/version/hash, verification profile version, and initial state produce the same verdict. Verification does not commit mission completion.

## 11. Simulation observation fixtures

`SimulationObservationRef` contains:

```text
fixture_set_id = SIM_FIXTURE_SET_V1
fixture_id
fixture_version
content_sha256
timestamp
source_kind = mock
```

`SimulationFixtureManifest` contains versioned `SimulationFixtureEntry` objects. Each `(fixture_id, fixture_version)` pair MUST occur exactly once. Each entry binds identity/version/hash fields to deterministic observation content. `content_sha256` is the SHA-256 of the canonical observation object using sorted keys and compact separators, and a consumer MUST recompute and compare it before using the observation.

Observation quality is exactly `valid`, `insufficient`, or `ambiguous`. A valid observation requires `part_id` and `location_id`. Insufficient or ambiguous observations may omit them and always produce `uncertain`.

Explicit invariant:

```text
SIM_FIXTURE_SET_V1 != Dataset V1
```

Fixtures are contract-test data only. They are not training data or demonstrations. The schema rejects camera serial numbers, `/dev/video*`, RealSense IDs, calibration files, physical camera access, and physical robot state.

## 12. Gap disposition

| Gap | Finding preserved verbatim | Executable resolution |
|---|---|---|
| `GAP-SIM-001` | no executable Mission Executor invocation, state-transition, completion, or failure contract exists. | Section 5 and Mission schemas/transitions |
| `GAP-SIM-002` | no executable Navigation Skill request/result or action-status reconciliation interface exists. | Section 6 and Navigation schemas/status linkage |
| `GAP-SIM-003` | no executable VLA Skill request/result, uncertainty, or bounded action interface exists. | Section 7 and VLA schemas/observation linkage |
| `GAP-SIM-004` | no executable Verification request/result schema or deterministic acceptance-threshold contract exists. | Section 10 and Verification schemas/profile |
| `GAP-SIM-005` | timeout and reconciliation rules are conceptual, but callable status lookup, concrete lifecycle values, and compatibility behavior are not executable contracts. | Sections 4, 8, and 9 plus transition/reconciliation/retry schemas |
| `GAP-SIM-006` | synthetic observation references are authorized conceptually, but their executable fixture shape and validation rules are undefined. | Section 11 and observation/manifest schemas |

## 13. Prohibited authority and behavior

This contract does not authorize or require physical robot/camera access, physical motion, gripper execution, teleoperation, E-stop execution, real Nav2/MoveIt/`ros2_control`, VLA inference/training, Dataset V1, paid compute, candidate hardware freeze, any `TASK-W*` authorization change, or `TASK-SIM-002`.

`P0-004R = NO_GO` remains historical and unchanged. Contract availability is not runtime correctness, independent acceptance, downstream readiness, or physical authorization.
