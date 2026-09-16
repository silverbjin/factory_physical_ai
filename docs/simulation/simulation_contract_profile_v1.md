# Simulation Contract Profile v1

> Task: `TASK-SIM-001`
> Profile revision: post-`TASK-SIM-C01` re-evaluation
> Implementation status: `COMPLETE`
> Task-specific decision: `SIM_CONTRACT_PROFILE_READY`
> Independent acceptance: `PENDING`
> Downstream authorization: `TASK-SIM-002 authorized = false`

## 1. Purpose and authority

This profile re-evaluates the project-facing Simulation Lane boundaries after the independently accepted resolution of `TASK-SIM-C01`. It defines the minimum executable behavior that a future bounded deterministic smoke runtime may implement. It does not implement that runtime or grant downstream, physical, Dataset V1, training, or Week-task authorization.

The project-wide `contract_plan.md` remains planning-only. Its explicit delegation makes only `simulation_execution_contract_v1.md` and its companion schema executable authority for Simulation Lane v1. `SIM-C01_acceptance.json` independently binds that delegation to the accepted C01 evidence, reviewed commit, contract, schema, contract plan, task specification, and review record.

| Required authoritative source | SHA-256 |
|---|---|
| `docs/architecture/adr/ADR-Simulation-Lane-v1.md` | `1509577842464f48055f402f5a3f717efecaba77847ff4c70534d14086fb46e0` |
| `context/simulation_task_mapping_v1.md` | `c0cf1671d97f4cec768de1a2836b8ecdd89c7ceace947bab108ab549c11396b2` |
| `docs/architecture/system_architecture_v1.md` | `50e57f517cf613b5b8e26e31ec74965d03c729526b94f39d9423fa0a15371e3d` |
| `docs/contracts/contract_plan.md` | `4fd3a4916fa118fdbb8792681a8450157cefc0473f495e8523842e3b09b59cde` |
| `docs/contracts/simulation_execution_contract_v1.md` | `0451e9abae4cee911d9468d11e68b8bbb0e3aff1a1a2d9cf104ed64264d28caa` |
| `docs/contracts/schemas/simulation_execution_contract_v1.schema.json` | `112b1e2e0d1fefb03d7b353e8ed4d875b025fe342380d5ba1cbf050bcc7d944a` |
| `results/reviews/SIM-C01_acceptance.json` | `1aee7a19f24cf52da3a2c0b232872420aafe7f1e644ed5fb1a493a025c5ee2d5` |
| `docs/hardware/hardware_target_selection_status_v1.md` | `fda8a33fe38fe1796f5d984d9b7a6c81dc4babe22e618f861375073043ad1109` |
| `docs/architecture/adr/ADR-001-manipulator.md` | `93c41a83e018adaecf5c482fba70ad32548bd940e98d5a391f459b2662873537` |
| `docs/architecture/adr/ADR-002-amr.md` | `4d56a32ac5e45fc9af169b3c591c518841067bc8f9544c496b2dabdbbe2727cf` |
| `docs/architecture/adr/ADR-005-camera-observation.md` | `2cb2e00d5271e6a2ba5b3401f16bfe4da7f44b9876451b98287ce48bbeb5d882` |
| `docs/architecture/adr/ADR-010-deployment-topology.md` | `018ec1b9e9e525bc70367ace55581ec04d6343c2571c1805169227c937eb0825` |
| `results/phase0/P0-004R_vla_readiness.json` | `f705896b9b6a48b08dde7401dfd3ca848d9fc46ac2711bd90fdd04d8b29f873d` |

## 2. Preserved topology and ownership

The executable Simulation Lane profile preserves exactly this topology:

```text
Deterministic Mission Executor
        |
        +-- Navigation Skill boundary
        +-- VLA Skill boundary
        +-- Verification boundary
```

The logical operations are exactly:

```text
mission.execute
navigation.execute
vla.execute
action_status.get
verification.verify
```

These identifiers are protocol-neutral. They do not define Python methods, ROS endpoints, HTTP routes, gRPC methods, Nav2 commands, MoveIt commands, or hardware interfaces. A runtime binding belongs to a separately authorized implementation task.

Ownership remains unchanged:

- the Agent proposes approved semantic capabilities and never issues raw ROS/Nav2 or actuator commands;
- the Deterministic Mission Executor owns validation, authorization, mission state, business recovery, retry, reconciliation, persistence, and audit;
- Nav2 owns later local navigation planning, controller behavior, configured local recovery, and lifecycle;
- VLA owns only an approved bounded semantic skill and does not own raw actuators;
- MoveIt owns manipulation planning and safety boundaries;
- `ros2_control` owns controller and hardware interfaces;
- Verification reports evidence and verdict but does not commit mission completion.

No `ManipulatorPort`, `NavigationPort`, `ObservationPort`, or other mission-to-actuator public port is introduced.

## 3. Boundary classification

All four required boundaries are `EXECUTABLE_CONTRACT_AVAILABLE` for Simulation Lane v1 only.

### 3.1 Deterministic Mission Executor

- Classification: `EXECUTABLE_CONTRACT_AVAILABLE`
- Operation: `mission.execute`
- Request: closed `MissionExecuteRequest` with the common request envelope, `idempotency_key`, and an approved simulation-only structured line-side-supply goal.
- Result: closed `MissionExecuteResult` with canonical mission status, logical result, checkpoint revision, outcome, and conditionally required error/HITL data.
- Lifecycle: `created`, `ready`, `executing`, `reconciling`, `recovering`, `completed`, `failed`, and `escalated`, with only the transitions enumerated by the contract.
- Completion: requires all required actions to be authoritatively successful and verification verdict `pass`; verification does not mutate mission state directly.
- Failure/recovery: deterministic policy selects bounded retry, recovery, failure, or escalation. No Agent-selected physical outcome is accepted.

### 3.2 Navigation Skill

- Classification: `EXECUTABLE_CONTRACT_AVAILABLE`
- Operation: `navigation.execute`
- Request: closed `NavigationExecuteRequest` with stable action/idempotency identity, bounded attempt and retry budget, robot identity, allowlisted `destination_id`, and `speed_profile_id`.
- Result: closed `NavigationExecuteResult`; success requires `status=succeeded` and verified arrival at the requested destination.
- Failure/timeout: known failure is typed; `DEPENDENCY_TIMEOUT` or `MODEL_TIMEOUT` requires `result=pending`, `status=unknown`, and reconciliation.
- Ownership: no raw pose, path, trajectory, planner/controller parameter, ROS/Nav2 command, or lifecycle command is public contract input.

### 3.3 VLA Skill

- Classification: `EXECUTABLE_CONTRACT_AVAILABLE`
- Operation: `vla.execute`
- Request: closed `VLAExecuteRequest` for an approved bounded semantic task, policy version, immutable simulation observation references, and approved workspace profile.
- Result: closed `VLAExecuteResult` with action state, logical result, `skill_outcome`, verifier references, and latency.
- Failure/uncertainty: known failure is typed; pending/timeout remains `unknown` and `uncertain` until reconciliation.
- Ownership: joint, motor, gripper, trajectory, raw action chunk, MoveIt, `ros2_control`, and hardware-controller fields are forbidden.

### 3.4 Verification

- Classification: `EXECUTABLE_CONTRACT_AVAILABLE`
- Operation: `verification.verify`
- Request: closed `VerificationRequest` with action identity, verifier identity, exact expected `part_id`/`location_id`, immutable observation references, and `sim-exact-match-v1`.
- Result: closed `VerificationResult` separating invocation `result` from business `verdict=pass|fail|uncertain`.
- Determinism: valid exact match produces `pass`; valid mismatch produces `fail`; insufficient or ambiguous observation produces `uncertain`.
- Completion: `uncertain != pass`; confidence is metadata and cannot override the rule; verification alone cannot commit mission completion.

## 4. Common executable semantics

Every operation uses closed, versioned envelopes. Required request identity and timing fields include `schema_version`, `mission_id`, `request_id`, `trace_id`, `timestamp`, `deadline_at`, `timeout_ms`, and `component_version`. Side-effecting operations additionally use stable `idempotency_key`; action-bound dispatch uses stable `action_id`, `attempt`, and `retry_budget_remaining`.

Every result includes correlation identity, `source_kind=mock`, `status`, and `result`. Non-success results require a typed `error` whose canonical retryability field is `error.retryable`. No required field, enum, state, authorization, retry value, or unknown public field may be defaulted or coerced.

Timeout is an ambiguous outcome, not success or failure. The action lifecycle permits:

```text
requested -> running|failed|unknown
running -> succeeded|failed|unknown
unknown -> reconciling
reconciling -> reconciled(resolved_status=succeeded|failed|unknown)
```

Direct `unknown -> succeeded` is forbidden. A success discovered after timeout is usable only after `action_status.get` returns matching immutable evidence and a durable reconciliation record resolves the same `mission_id`, `action_id`, and lookup `request_id` to `succeeded`.

Retry is permitted only after reconciliation resolves `failed`, `error.retryable=true`, budget remains, mission/action/idempotency identity is stable, `request_id` is new, and `attempt` increments exactly once. Unknown or unreconciled actions cannot be retried.

## 5. Deterministic fixture profile for TASK-SIM-002

The accepted executable contract supports the following minimum bounded cases. This section describes required behavior; it does not provide fixtures or runtime code.

| Boundary | Deterministic success | Deterministic failure | Timeout / ambiguity | Reconciliation / verification |
|---|---|---|---|---|
| Mission Executor | Known authorized simulation mission reaches `completed` only after action success and verification `pass`. | Invalid/unauthorized or terminal execution result remains typed and fail-closed. | Non-terminal `pending` preserves the reason no trustworthy result exists. | Unknown action drives `reconciling`; only authoritative resolution permits completion/recovery/failure/escalation. |
| Navigation Skill | Known allowlisted destination returns `succeeded` with matching verified arrival. | Known diagnostic failure returns `failed` plus typed error. | Timeout returns `pending/unknown`; it never fabricates arrival. | Same-action status lookup and reconciliation precede retry or success processing. |
| VLA Skill | Known semantic task plus valid synthetic observation returns bounded `succeeded` outcome and verifier refs. | Known policy/model/execution failure returns typed failure without actuator commands. | Timeout returns `pending/unknown` and `skill_outcome=uncertain`. | Same-action status lookup/reconciliation preserves ambiguity until evidence resolves it. |
| Verification | Valid exact fixture match returns `pass`. | Valid predicate mismatch returns `fail`; operational failure remains distinct. | Insufficient/ambiguous observation returns `uncertain`. | Only `pass` may support mission completion; identical normalized inputs and fixture hashes yield the same verdict. |

`SimulationFixtureManifest` and `SimulationObservationRef` bind `SIM_FIXTURE_SET_V1`, fixture identity/version, canonical observation content SHA-256, timestamp, and `source_kind=mock`. Fixture identity/version pairs must be unique, and consumers must recompute the content hash before use.

## 6. Gap disposition

The prior accepted profile recorded these six gaps. Their wording and identity remain preserved; the independently accepted C01 contract now supplies the executable resolution.

| Gap | Historical exact finding | Current authoritative resolution |
|---|---|---|
| `GAP-SIM-001` | no executable Mission Executor invocation, state-transition, completion, or failure contract exists. | Contract Section 5 plus Mission request/result and transition schemas. |
| `GAP-SIM-002` | no executable Navigation Skill request/result or action-status reconciliation interface exists. | Contract Sections 6 and 8 plus Navigation and status lookup schemas. |
| `GAP-SIM-003` | no executable VLA Skill request/result, uncertainty, or bounded action interface exists. | Contract Sections 7 and 8 plus VLA and status lookup schemas. |
| `GAP-SIM-004` | no executable Verification request/result schema or deterministic acceptance-threshold contract exists. | Contract Section 10 plus Verification schemas and `sim-exact-match-v1`. |
| `GAP-SIM-005` | timeout and reconciliation rules are conceptual, but callable status lookup, concrete lifecycle values, and compatibility behavior are not executable contracts. | Contract Sections 4, 8, and 9 plus lifecycle, reconciliation, and retry schemas. |
| `GAP-SIM-006` | synthetic observation references are authorized conceptually, but their executable fixture shape and validation rules are undefined. | Contract Section 11 plus observation-reference and fixture-manifest schemas. |

Current unresolved contract gaps: none.

## 7. Physical, hardware, dataset, training, and Week boundaries

- Real robot/camera access, physical motion, gripper motion, physical teleoperation, physical E-stop execution, and physical state feedback remain excluded and unauthorized.
- myCobot 280 Pi, myAGV JN 2023, Intel RealSense D455, and Jetson Orin Nano remain candidates only; this profile freezes none of them.
- `SIM_FIXTURE_SET_V1 != Dataset V1`. Simulation fixtures are synthetic deterministic contract-test inputs, not demonstrations, collected data, or the existing Dataset V1 deliverable.
- SmolVLA fine-tuning, optimizer execution, model training, training compute, and paid compute remain neither required nor authorized.
- No `TASK-W*` identity or authorization is modified.
- The accepted historical `P0-004R` result remains `NO_GO`; `TASK-W1-001`, `TASK-W1-002`, Dataset V1, fine-tuning, and physical motion authorization remain false.

## 8. Checks

| Check | Result | Basis |
|---|---|---|
| C01 Governing Simulation ADR frozen | `PASS` | Governing ADR is `FROZEN`. |
| C02 Simulation task mapping frozen | `PASS` | Mapping is `FROZEN` and orders SIM-001 before SIM-002 before SIM-GATE. |
| C03 Required Context resolved | `PASS` | All thirteen exact Required Context paths exist and are SHA-256 bound. |
| C04 Existing architecture located | `PASS` | Frozen executor/skill/verification topology is unchanged. |
| C05 Mission execution boundary identified | `PASS` | `mission.execute` and its closed schemas/lifecycle are authoritative. |
| C06 Navigation Skill boundary classified | `PASS` | Simulation-only executable contract and ownership boundary verified. |
| C07 VLA Skill boundary classified | `PASS` | Bounded semantic contract and actuator prohibitions verified. |
| C08 Verification boundary classified | `PASS` | Exact-match deterministic contract and schemas verified. |
| C09 Executable/planning status truthful | `PASS` | Project plan stays planning-only; only accepted delegated Simulation Lane contract is executable. |
| C10 Direct actuator ownership absent | `PASS` | Closed schemas and normative contract reject lower-level commands/ports. |
| C11 Deterministic fixture semantics defined where supported | `PASS` | Section 5 profiles only contract-supported bounded behavior. |
| C12 Failure path defined where supported | `PASS` | Typed errors and result/status consistency are defined. |
| C13 Timeout behavior defined where supported | `PASS` | Both timeout categories require `pending/unknown` and reconciliation. |
| C14 Reconciliation relationship defined where applicable | `PASS` | Status lookup, immutable evidence, legal transitions, and retry guards are defined. |
| C15 Physical dependency absent | `PASS` | Contract, schema, and profile require mock/synthetic inputs only. |
| C16 Dataset V1 not aliased | `PASS` | Fixture set identifier and explicit inequality are preserved. |
| C17 Training not required | `PASS` | No training or fine-tuning is part of the profile. |
| C18 Week authorization unchanged | `PASS` | P0-004R `NO_GO` and false authorization values are preserved. |
| C19 No existing contract silently rewritten | `PASS` | The accepted versioned delegation is used without expanding its scope. |
| C20 Evidence/profile/source bindings internally consistent | `PASS` | Companion evidence binds this profile and every Required Context source. |

## 9. Historical preservation and state separation

The prior canonical revision remains recoverable in Git and immutable task history:

```text
Historical profile SHA-256: 43da41ade5cf53230afc46b3092b733611f0c5989f4e8769286c67aa4a171d7a
Historical evidence SHA-256: 98ae08b1ba664f7be42551a84b112608409362be5615c78a57f256a935a86559
Historical task-specific decision: SIM_CONTRACT_PROFILE_BLOCKED
Historical independent review: ACCEPT
```

That `ACCEPT + BLOCKED` remains a trustworthy historical finding and never authorized `TASK-SIM-002`. Regenerating the canonical profile/evidence invalidates any prior acceptance binding to those old hashes. This re-evaluation requires a new independent review and separate post-review acceptance record.

```text
TASK-SIM-001 implementation: complete
Task-specific decision: SIM_CONTRACT_PROFILE_READY
Independent acceptance: pending
TASK-SIM-002 authorized: false
```

`READY` means only that the accepted authoritative contract is sufficiently precise for a future bounded smoke implementation. It is not implementation completion, independent acceptance, downstream authorization, `SIM_GO`, or any physical/training/dataset/Week authorization.
