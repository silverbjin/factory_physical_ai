# Simulation Contract Profile v1

> Task: `TASK-SIM-001`
> Implementation status: `COMPLETE`
> Task-specific decision: `SIM_CONTRACT_PROFILE_BLOCKED`
> Independent acceptance: `PENDING`
> Downstream authorization: `TASK-SIM-002 authorized = false`

## 1. Purpose and authority

This profile records the existing project-facing boundaries that a future deterministic simulation fixture would have to emulate. It is a contract-readiness assessment, not an executable contract, simulator implementation, or authorization grant.

The assessment follows the required authority order: frozen architecture and ADRs, the frozen Simulation Lane mapping, the current planning contract, and accepted P0 authorization evidence. Implementation code and desired future implementation shapes were not used to create contract semantics.

| Authoritative source | SHA-256 |
|---|---|
| `docs/architecture/adr/ADR-Simulation-Lane-v1.md` | `1509577842464f48055f402f5a3f717efecaba77847ff4c70534d14086fb46e0` |
| `context/simulation_task_mapping_v1.md` | `c0cf1671d97f4cec768de1a2836b8ecdd89c7ceace947bab108ab549c11396b2` |
| `docs/architecture/system_architecture_v1.md` | `50e57f517cf613b5b8e26e31ec74965d03c729526b94f39d9423fa0a15371e3d` |
| `docs/contracts/contract_plan.md` | `aa7f9fe1477d650b3648c18d5df1fb3b0dabc6d06df6eff33e28dcdcc05e87d0` |
| `docs/hardware/hardware_target_selection_status_v1.md` | `fda8a33fe38fe1796f5d984d9b7a6c81dc4babe22e618f861375073043ad1109` |
| `docs/architecture/adr/ADR-001-manipulator.md` | `93c41a83e018adaecf5c482fba70ad32548bd940e98d5a391f459b2662873537` |
| `docs/architecture/adr/ADR-002-amr.md` | `4d56a32ac5e45fc9af169b3c591c518841067bc8f9544c496b2dabdbbe2727cf` |
| `docs/architecture/adr/ADR-005-camera-observation.md` | `2cb2e00d5271e6a2ba5b3401f16bfe4da7f44b9876451b98287ce48bbeb5d882` |
| `docs/architecture/adr/ADR-010-deployment-topology.md` | `018ec1b9e9e525bc70367ace55581ec04d6343c2571c1805169227c937eb0825` |
| `results/phase0/P0-004R_vla_readiness.json` | `f705896b9b6a48b08dde7401dfd3ca848d9fc46ac2711bd90fdd04d8b29f873d` |

## 2. Preserved topology

The only profiled execution topology is:

```text
Deterministic Mission Executor
        |
        +-- Navigation Skill boundary
        +-- VLA Skill boundary
        +-- Verification boundary
```

Future simulation fixtures belong behind the three skill/verification boundaries. This profile does not introduce `ManipulatorPort`, `NavigationPort`, `ObservationPort`, or any other mission-layer actuator port.

## 3. Boundary classification

All four boundaries are `PLANNING_CONTRACT_ONLY`. The architecture defines responsibilities and conceptual behavior, but `docs/contracts/contract_plan.md` explicitly states that it does not define executable APIs yet.

### 3.1 Deterministic Mission Executor

- Classification: `PLANNING_CONTRACT_ONLY`
- Ownership: contract validation, authorization and safety gates, deterministic state transitions, timeout and bounded retry policy, idempotency, persistence, metrics, and audit.
- Invocation concept: a validated mission and approved typed skill proposal are checked before dispatch.
- State/action concept: side effects use stable `idempotency_key` and `action_id`; timeout or restart leaves an action `unknown` until reconciliation.
- Completion concept: a typed terminal result and verification precede committed physical-action success.
- Failure concept: deterministic policy may retry within budget, request approved recovery, escalate, or create HITL.
- Missing executable contract: no authoritative callable mission interface, concrete request/result schema, transition schema, or reconciliation operation signature is defined.

### 3.2 Navigation Skill

- Classification: `PLANNING_CONTRACT_ONLY`
- Request concept: robot identity, allowlisted named destination or route, speed profile, stable `action_id`, and finite timeout/deadline.
- Result concept: execution state, arrival verification, diagnostic error, and retryability.
- Failure/timeout concept: a timeout must not be interpreted as success or failure; the same action must be reconciled before retry or resume.
- Ownership: the skill boundary accepts controlled navigation intent; a later Nav2 adapter owns local planning, controller behavior, recovery, and lifecycle.
- Prohibition: no Agent-provided raw pose, path, trajectory, ROS shell, or controller command.
- Missing executable contract: no authoritative request/result type, callable surface, terminal-state vocabulary, or action-status query is defined.

### 3.3 VLA Skill

- Classification: `PLANNING_CONTRACT_ONLY`
- Request concept: robot identity, task identity, policy/model version, synthetic observation references, approved workspace profile, and finite timeout.
- Result concept: bounded pick/place outcome, verifier input references, policy latency, and failure taxonomy.
- Failure/uncertainty concept: malformed, unavailable, timeout, model, execution, and uncertain outcomes must remain typed and must not be converted into asserted success.
- Authorization boundary: the executor owns mission authorization and retry policy; the VLA skill may operate only within the approved semantic skill/workspace boundary.
- Prohibition: no joint, motor, gripper, trajectory, ROS, MoveIt, or `ros2_control` command contract is introduced.
- Missing executable contract: no authoritative request/result type, invocation interface, bounded action representation, or executable uncertainty/reconciliation surface is defined.

### 3.4 Verification

- Classification: `PLANNING_CONTRACT_ONLY`
- Request concept: verifier identity/version, expected part/place, synthetic observation references, and timestamp.
- Result concept: `pass`, `fail`, or `uncertain`, with confidence and mismatch taxonomy.
- Completion/recovery concept: deterministic acceptance thresholds govern completion; mismatch or uncertainty leads to recovery or escalation rather than an invented success.
- Ownership: verification reports observed evidence and confidence but does not declare mission completion by itself.
- Missing executable contract: no authoritative callable verifier interface, concrete result schema, acceptance threshold, or reconciliation binding is defined.

## 4. Non-executable deterministic fixture requirements

The following are constraint-level behaviors supported by the authoritative planning sources. They are not executable API definitions and may not be treated as sufficient input for `TASK-SIM-002`.

| Boundary | Deterministic success | Deterministic failure | Timeout / ambiguous outcome | Reconciliation relationship |
|---|---|---|---|---|
| Mission Executor | Validate a known mission and record an auditable terminal transition after typed skill results and verification. | Reject invalid or unauthorized input; apply bounded deterministic recovery or HITL policy to typed failure. | Preserve `unknown`; do not infer an external action outcome. | Reconcile the same stable `action_id` before retry, resume, or escalation. |
| Navigation Skill | For a known allowlisted destination, return a structured arrival result. | Return a typed diagnostic failure with retryability; never fabricate arrival. | Return an ambiguous/timeout outcome without classifying physical success. | Expose enough status for the executor to reconcile the same `action_id`; the executable operation remains undefined. |
| VLA Skill | For known synthetic observation references and an approved semantic task/workspace, return a bounded structured outcome with verifier references. | Return a typed policy/model/execution failure; never emit direct actuator commands. | Return timeout or uncertain outcome without asserting task completion. | Route outcome evidence to verification and preserve ambiguity for executor policy; the executable operation remains undefined. |
| Verification | For known synthetic evidence, deterministically produce a threshold-backed verification result. | Produce mismatch or fail with typed reason. | Produce `uncertain` when evidence cannot support pass/fail. | Send mismatch/uncertainty to deterministic recovery or escalation; verification alone cannot commit mission completion. |

The common planning envelope calls for version, mission/request correlation, stable idempotency/action identifiers for side effects, timestamps/deadlines, result/error/retryability, component version, and optional evidence references. Concrete serialization, field types, allowed values, defaults, and compatibility tests remain undefined; this profile does not supply them.

## 5. Contract gaps and fail-closed result

The following unresolved gaps prevent an executable smoke path without inventing a public contract:

1. `GAP-SIM-001`: no executable Mission Executor invocation, state-transition, completion, or failure contract exists.
2. `GAP-SIM-002`: no executable Navigation Skill request/result or action-status reconciliation interface exists.
3. `GAP-SIM-003`: no executable VLA Skill request/result, uncertainty, or bounded action interface exists.
4. `GAP-SIM-004`: no executable Verification request/result schema or deterministic acceptance-threshold contract exists.
5. `GAP-SIM-005`: timeout and reconciliation rules are conceptual, but callable status lookup, concrete lifecycle values, and compatibility behavior are not executable contracts.
6. `GAP-SIM-006`: synthetic observation references are authorized conceptually, but their executable fixture shape and validation rules are undefined.

Because these are required smoke-path semantics, the fail-closed task-specific decision is:

```text
SIM_CONTRACT_PROFILE_BLOCKED
```

Resolving these gaps requires a separately reviewed and versioned contract-change task. This profile must not be reinterpreted as that contract.

## 6. Physical, hardware, dataset, and training boundaries

- Real robot access, real camera access, physical motion, gripper motion, physical teleoperation, physical E-stop execution, and physical state feedback are excluded.
- myCobot 280 Pi, myAGV JN 2023, Intel RealSense D455, and Jetson Orin Nano remain candidates only. No target is selected or frozen here.
- `SIM_FIXTURE_SET_V1 != Dataset V1`. Simulation fixtures are synthetic deterministic contract-test inputs, not collected demonstrations or the Week deliverable.
- SmolVLA fine-tuning, optimizer execution, model training, training compute, paid compute provisioning, and Dataset V1 are not required or authorized.
- The accepted historical `P0-004R` result remains `NO_GO`; its Week, Dataset V1, fine-tuning, and physical-motion authorization values remain false.

## 7. Checks

| Check | Result | Basis |
|---|---|---|
| C01 Governing Simulation ADR frozen | `PASS` | `ADR-Simulation-Lane-v1.md` is `FROZEN`. |
| C02 Simulation task mapping frozen | `PASS` | `simulation_task_mapping_v1.md` is `FROZEN`. |
| C03 Required Context resolved | `PASS` | All ten required paths exist and are SHA-256 bound above. |
| C04 Existing architecture located | `PASS` | `system_architecture_v1.md` defines the executor/skill/verification topology. |
| C05 Mission execution boundary identified | `PASS` | Ownership and conceptual lifecycle are recorded in Section 3.1. |
| C06 Navigation Skill boundary classified | `PASS` | Classified `PLANNING_CONTRACT_ONLY` in Section 3.2. |
| C07 VLA Skill boundary classified | `PASS` | Classified `PLANNING_CONTRACT_ONLY` in Section 3.3. |
| C08 Verification boundary classified | `PASS` | Classified `PLANNING_CONTRACT_ONLY` in Section 3.4. |
| C09 Executable/planning status truthful | `PASS` | No executable API is claimed; the aggregate status is blocked. |
| C10 Direct actuator ownership absent | `PASS` | No lower-level mission port or command contract was introduced. |
| C11 Deterministic fixture semantics defined where supported | `PASS` | Only source-supported constraint-level behavior is recorded in Section 4. |
| C12 Failure path defined where supported | `PASS` | Typed failure and fail-closed behavior are recorded without inventing schemas. |
| C13 Timeout behavior defined where supported | `PASS` | Timeout preserves an ambiguous `unknown` outcome. |
| C14 Reconciliation relationship defined where applicable | `PASS` | Same-`action_id` reconciliation before retry/resume/escalation is preserved. |
| C15 Physical dependency absent | `PASS` | All physical/device dependencies are excluded. |
| C16 Dataset V1 not aliased | `PASS` | `SIM_FIXTURE_SET_V1` is explicitly distinct from Dataset V1. |
| C17 Training not required | `PASS` | No model training or training resource is required. |
| C18 Week authorization unchanged | `PASS` | P0-004R authorization remains unchanged and false where recorded. |
| C19 No existing contract silently rewritten | `PASS` | This profile remains non-executable and records gaps instead of filling them. |
| C20 Evidence/profile/source bindings internally consistent | `PASS` | The companion evidence binds this profile and all required sources. |

## 8. State separation

```text
TASK-SIM-001 implementation: complete
Task-specific decision: SIM_CONTRACT_PROFILE_BLOCKED
Independent acceptance: pending
TASK-SIM-002 authorized: false
```

Implementation completion means the bounded assessment and evidence exist. It does not mean the contract is ready, independently accepted, or available for downstream execution. Even a future independent `ACCEPT` of this blocked result would only establish that the blocked assessment is trustworthy.
