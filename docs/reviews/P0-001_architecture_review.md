# P0-001 Architecture Review

> Reviewed: 2026-08-28  
> Scope: review of TASK-P0-001 artifacts only. This is an engineering decision artifact, not an architecture change. It does not modify any ADR status or authorize implementation work.

## Purpose and classification

This review preserves the findings from the three planning artifacts:

- `docs/architecture/system_architecture_v1.md`
- `plans/phase0_risks.md`
- `plans/next_tasks_after_phase0.md`

The actions below are recommendations for a subsequent planning/review step. `FIX_NOW` means resolve the planning inconsistency or establish the listed gate before starting the affected MVP work; it does **not** authorize a silent ADR change. `DEFER` requires its listed validation trigger. `ACCEPT` records a deliberate, bounded constraint.

| Severity | Meaning |
|---|---|
| **CRITICAL** | Can block the Day-10 MVP or invalidate the stated architecture basis if not resolved first. |
| **HIGH** | Can cause unsafe/incorrect boundary ownership, major rework, or material loss of evidence quality. |
| **MEDIUM** | Likely to add scope, cost, or migration risk but has a bounded workaround. |
| **LOW** | Clarity or maintainability concern with no near-term architecture block. |

## Findings

### CRITICAL — F-01: MVP sequencing makes the Agent vertical slice depend on VLA hardware readiness

- **Finding:** `MVP-001 Factory Agent/tool vertical slice` is ordered after the CUDA/LeRobot/hardware proof and teleoperation tasks. The plan therefore allows unavailable hardware, GPU access, or operator approval to delay the Day-10 Agent MVP.
- **Evidence:** `plans/next_tasks_after_phase0.md` orders P0-003 and P0-004 before MVP-001. `plans/phase0_risks.md` identifies unavailable teleoperation and blocked GPU/NVML access as high-impact risks.
- **Impact:** The project can miss its Day-10 demonstrable chain even though the intended MVP uses mocked navigation/VLA/factory boundaries and does not require physical hardware.
- **Affected artifact:** `plans/next_tasks_after_phase0.md`; `plans/phase0_risks.md`; `docs/architecture/system_architecture_v1.md`.
- **Recommended action:** Make P0-002 and MVP-001 the immediate software path. Run P0-003 as an independent, time-boxed VLA readiness path; P0-004 remains gated on actual hardware and operator authorization.
- **Action:** **FIX_NOW**
- **Reason:** This is a planning dependency correction, not a change to the accepted mock-first MVP architecture.
- **Validation trigger if deferred:** Not applicable. Resolve before beginning MVP-001 planning/implementation.

### CRITICAL — F-02: ROS/Nav2/Gazebo capability evidence was interpreted incorrectly

- **Finding:** The risk and architecture documents state or imply Nav2/Gazebo are unavailable based on absence of selected packages, although the installed ROS environment exposes Nav2 components, `nav2_simple_commander`, minimal TB3/TB4 simulation packages, MoveIt 2, `ros2_control`, and Gazebo `gz sim`.
- **Evidence:** Local package/executable inspection found `nav2_bt_navigator`, `nav2_controller`, `nav2_lifecycle_manager`, `nav2_simple_commander`, `nav2_minimal_tb3_sim`, `nav2_minimal_tb4_sim`, `moveit_ros_move_group`, `controller_manager`, `robot_localization`, `diagnostic_updater`, and `gz sim`. `plans/phase0_risks.md` R-06 instead says Nav2/Gazebo packages are absent.
- **Impact:** The project may recreate standard navigation/simulation infrastructure or make a simulator decision using incomplete facts. Installed packages are not a configured robot system, but they invalidate the stronger absence claim.
- **Affected artifact:** `plans/phase0_risks.md` R-06; `docs/environment/development_environment_v1.md`; ADR-002 and ADR-003 validation evidence.
- **Recommended action:** Correct the verified package inventory in a follow-up review/ADR update. Retain deterministic fixtures for Day-10, but explicitly select existing Nav2/Gazebo capability as the first integration option rather than assuming installation work.
- **Action:** **FIX_NOW**
- **Reason:** Factual validation evidence is part of the architecture freeze and must be accurate before downstream work relies on it.
- **Validation trigger if deferred:** Not applicable. Reconcile before a simulation or AMR integration task is authorized.

### CRITICAL — F-03: VLA feasibility has no time-boxed go/no-go decision

- **Finding:** SmolVLA/LeRobot is only proposed, while CUDA/VRAM, Torch/LeRobot installation, manipulator, camera, USB access, safety path, and remote-GPU budget are unverified. The risk register identifies these individually but lacks a deadline and explicit fallback decision.
- **Evidence:** `results/phase0/environment_verification.json` records inaccessible GPU/NVML, absent `torch`/`lerobot`, and no camera or serial robot device. R-01 through R-03 identify the dependency chain.
- **Impact:** The direct VLA fine-tuning evidence—the central portfolio requirement—can become impossible late in the schedule, while the team continues on an assumption that hardware will appear.
- **Affected artifact:** ADR-001, ADR-004, ADR-005; `plans/phase0_risks.md`; `plans/next_tasks_after_phase0.md`.
- **Recommended action:** Define an owner, a short readiness deadline, minimum accepted GPU/VRAM/device evidence, an approved remote-CUDA budget path, and an escalation/stop decision. Preserve the requirement for direct VLA evidence; do not silently substitute a synthetic or model-free result.
- **Action:** **FIX_NOW**
- **Reason:** This is the critical path for the VLA workstream, not a normal implementation detail.
- **Validation trigger if deferred:** Not applicable; establish the go/no-go before beginning Dataset V1 collection planning.

### HIGH — F-04: Day-10 boundary decomposition is unnecessarily complex

- **Finding:** The MVP describes separate WMS, Fleet, PHM, navigation, VLA, verification, persistence, trace, and metric boundaries from the first vertical slice.
- **Evidence:** `docs/architecture/system_architecture_v1.md` lists all boundaries, while the MVP is explicitly mock-based. `docs/contracts/contract_plan.md` requires a rich cross-cutting envelope for every boundary.
- **Impact:** Implementation may spend Day-10 on service/adapter plumbing instead of proving the single mission, bounded recovery, durable state, and evidence flow.
- **Affected artifact:** `docs/architecture/system_architecture_v1.md`; `docs/contracts/contract_plan.md`; `plans/next_tasks_after_phase0.md`.
- **Recommended action:** For MVP-001, use in-process deterministic fakes behind the existing typed interfaces. Keep only one mission executor, one factory-tool gateway, and named navigation/VLA/verification fakes; defer service process separation.
- **Action:** **FIX_NOW**
- **Reason:** The interfaces remain intact, but scope must be constrained before implementation begins.
- **Validation trigger if deferred:** Not applicable; decide the MVP composition before MVP-001 is started.

### HIGH — F-05: Navigation recovery ownership is not separated from Nav2 ownership

- **Finding:** The deterministic executor is described as owning recovery, while a future navigation adapter is described without a precise split between business recovery and Nav2 local recovery.
- **Evidence:** `docs/architecture/system_architecture_v1.md` assigns executor retry/recovery and a navigation skill; `docs/contracts/contract_plan.md` defines navigation retryability but not the ownership boundary. Nav2 components and `nav2_simple_commander` are installed.
- **Impact:** A future adapter can duplicate Nav2 behavior-tree recovery, planner/controller behavior, lifecycle control, or blocked-route handling; duplicated policies can conflict and make failures hard to diagnose.
- **Affected artifact:** `docs/architecture/system_architecture_v1.md`; `docs/contracts/contract_plan.md`; ADR-002.
- **Recommended action:** Define that Nav2 owns local navigation execution and configured local recoveries. The executor owns only business-level decisions after a typed terminal result: retry budget, wait, reroute request, robot reassignment, or HITL. The Agent supplies no poses, paths, or Nav2 shell calls.
- **Action:** **FIX_NOW**
- **Reason:** This is a required ROS 2 ↔ Agent boundary clarification before adapter design.
- **Validation trigger if deferred:** Not applicable; resolve before INT-001 planning.

### HIGH — F-06: Manipulation/VLA safety boundary risks reimplementing MoveIt and ros2_control

- **Finding:** The architecture reserves a VLA skill and manipulator execution adapter but does not specify how MoveIt, `ros2_control`, collision checking, controller lifecycle, and VLA action output divide authority.
- **Evidence:** `docs/architecture/system_architecture_v1.md` names a VLA server and ROS execution adapter; `docs/contracts/contract_plan.md` prohibits a direct actuator contract but provides no staged-motion ownership. The host has `move_group`, MoveIt planning packages, `controller_manager`, and `ros2_control`.
- **Impact:** The project could build custom trajectory generation, collision logic, controller management, or joint safety logic that existing ROS 2/MoveIt capabilities already provide; an unclear VLA path also creates a safety risk.
- **Affected artifact:** `docs/architecture/system_architecture_v1.md`; `docs/contracts/contract_plan.md`; ADR-001 and ADR-004.
- **Recommended action:** Before physical integration, document the control split: MoveIt owns named poses, planning scene, pre-grasp/retreat, collision validation, and trajectory execution; `ros2_control` owns controller/hardware lifecycle; VLA is constrained to the approved manipulation skill/action interface and cannot bypass those gates.
- **Action:** **FIX_NOW**
- **Reason:** The current contract is intentionally incomplete, but this boundary must be explicit before a real VLA or robot adapter is designed.
- **Validation trigger if deferred:** Not applicable; resolve before P0-004 or INT-001 begins.

### HIGH — F-07: Development-PC observations are being generalized to robot availability

- **Finding:** The review environment found no camera or serial device inside WSL, but that does not prove that no physical robot or camera is available on the host or can be exposed through a native robot PC.
- **Evidence:** `results/phase0/environment_verification.json` records no `/dev/video*` or `/dev/ttyUSB*`/`ttyACM*`; the environment manifest correctly identifies WSL as development-only. R-01 and R-08 use the absence as hardware-risk evidence.
- **Impact:** Hardware procurement, integration, or safety planning may be delayed by a false negative; conversely, WSL might be incorrectly chosen as a robot-runtime path.
- **Affected artifact:** `docs/environment/development_environment_v1.md`; ADR-001; ADR-005; `plans/phase0_risks.md`.
- **Recommended action:** Treat the finding strictly as “not exposed to this WSL environment.” Obtain a native robot-PC/device inventory and connectivity check before choosing hardware topology. Maintain the accepted rule that drivers and motion remain native to the robot PC.
- **Action:** **FIX_NOW**
- **Reason:** Correcting the evidence interpretation protects both schedule and hardware safety without changing the topology decision.
- **Validation trigger if deferred:** Not applicable; resolve before any physical-hardware task is scheduled.

### HIGH — F-08: VLA observation feasibility is assumed before camera timing/calibration evidence exists

- **Finding:** The one-camera 640x480@30 FPS strategy and calibration/timestamp expectations are sensible defaults but are not hardware-validated.
- **Evidence:** ADR-005 sets those values; the environment result records no camera device and no `v4l2-ctl`.
- **Impact:** Dataset/action synchronization, observation quality, and evaluation repeatability may fail after teleoperation work starts, forcing costly recollection.
- **Affected artifact:** ADR-005; ADR-004; `plans/phase0_risks.md` R-08.
- **Recommended action:** Keep the minimal one-camera decision, but treat resolution/FPS and timing alignment as explicit hypotheses. Validate monotonic capture timestamps, robot-state alignment, calibration revision, and storage bandwidth with a short supervised recording before Dataset V1.
- **Action:** **DEFER**
- **Reason:** It cannot be validated until a camera is available; it does not block the mocked Agent MVP.
- **Validation trigger if deferred:** P0-004 short smoke recording on the selected hardware path.

### HIGH — F-09: Real hosted-model production behavior is not yet feasible evidence

- **Finding:** A provider-neutral interface and fake provider are planned, but no credential-safe typed-tool call, model allowlist, latency/cost observation, or provider failure behavior has been validated.
- **Evidence:** ADR-006 explicitly defers provider credential/runtime validation. `results/phase0/environment_verification.json` shows no provider SDK evidence. The contract requires typed tool envelopes and timeout behavior.
- **Impact:** Fake-provider tests can establish deterministic mission behavior but cannot prove structured-call conformance, provider latency/cost, malformed output handling, or outage recovery.
- **Affected artifact:** ADR-006; ADR-007; `docs/contracts/contract_plan.md`; `plans/phase0_risks.md` R-10.
- **Recommended action:** Use the fake provider for deterministic MVP tests, then execute one explicit, credential-safe real-provider structured-tool smoke check before claiming hosted Agent integration. Capture only safe model/version, latency, token/cost fields, and result category.
- **Action:** **DEFER**
- **Reason:** The real provider is not required to demonstrate the mock-first Day-10 mission, but is required before a production-oriented hosted-Agent claim.
- **Validation trigger if deferred:** Before the first real-provider demo or Agent benchmark run.

### HIGH — F-10: ROS 2 ↔ Agent ↔ VLA coupling lacks a reconciliation rule for ambiguous physical outcomes

- **Finding:** The contracts correctly state that a timeout is neither success nor failure, but they do not yet define a physical action-status/reconciliation path across the executor, VLA skill, and ROS adapter.
- **Evidence:** `docs/contracts/contract_plan.md` requires reconciliation after timeout; system architecture describes structured results but does not define action-status source or reconciliation state.
- **Impact:** A process restart or VLA/ROS timeout can cause duplicate pick/place attempts or a false completion, violating idempotency and safety goals.
- **Affected artifact:** `docs/contracts/contract_plan.md`; `docs/architecture/system_architecture_v1.md`; ADR-007 and ADR-008.
- **Recommended action:** Before implementing a non-mock skill, define a durable `action_id`, a queryable action-status result, and a deterministic `unknown -> reconcile -> resume/escalate` transition. Do not let the Agent decide the outcome.
- **Action:** **FIX_NOW**
- **Reason:** This is the central production-engineering boundary for safe physical side effects.
- **Validation trigger if deferred:** Not applicable; resolve before INT-001 or any physical skill call implementation.

### MEDIUM — F-11: Persistence and observability scope can prematurely require unavailable infrastructure

- **Finding:** The plan correctly selects SQLite/JSONL for MVP, but wording around PostgreSQL before soak and a future OpenTelemetry/Prometheus/Grafana stack can be interpreted as a prerequisite for early reliability evidence.
- **Evidence:** ADR-008 targets PostgreSQL before multi-process deployment, while the decision register says before concurrent/soak deployment. ADR-009 adds multiple future telemetry components. Docker daemon access is currently denied.
- **Impact:** Docker access and service provisioning could block a useful single-process regression, Chaos fixture, or short soak unnecessarily.
- **Affected artifact:** ADR-008; ADR-009; `docs/architecture/system_architecture_v1.md`; ADR-010.
- **Recommended action:** Preserve SQLite and JSONL for one-process MVP, deterministic regressions, and bounded early soak. Require PostgreSQL and collector-based telemetry only for concurrent/multi-service or long-running deployment claims; ensure each run still emits the existing machine-readable evidence fields.
- **Action:** **DEFER**
- **Reason:** The current MVP choice is sound; the escalation threshold needs clarification at the point multi-process validation is planned.
- **Validation trigger if deferred:** Before concurrent workers, external service deployment, or a portfolio claim that depends on cross-service telemetry.

### MEDIUM — F-12: The contract envelope may overburden the first mock implementation

- **Finding:** Every boundary is planned to carry many fields, including multiple IDs, versions, timeout fields, retry counters, and evidence references.
- **Evidence:** `docs/contracts/contract_plan.md` cross-cutting envelope lists 12 required/optional field groups for every request/event/result.
- **Impact:** A naïve MVP can spend excessive effort serializing and maintaining metadata rather than testing state transitions and failure policies.
- **Affected artifact:** `docs/contracts/contract_plan.md`; MVP-001 recommendation.
- **Recommended action:** Keep the full contract plan as the target. Define an MVP profile with the non-negotiable fields: schema version, mission/request/action or idempotency ID, timestamp/deadline, result/error/retryability, and component version. Add evidence references and remaining optional metadata incrementally.
- **Action:** **DEFER**
- **Reason:** The document is a forward-looking contract plan; trimming the first implementation profile does not weaken the final contract.
- **Validation trigger if deferred:** At MVP-001 contract-test design; expand before cross-process integration.

### MEDIUM — F-13: The custom state machine must remain deliberately small

- **Finding:** Choosing a custom deterministic mission state machine is appropriate, but it can reimplement graph persistence, HITL, and orchestration capabilities while LangGraph remains a possible later addition.
- **Evidence:** ADR-007 accepts a custom state machine and defers LangGraph; R-04 identifies framework complexity.
- **Impact:** Implementing both a rich custom graph engine and a LangGraph spike would consume the six-week schedule without adding safety evidence.
- **Affected artifact:** ADR-007; `plans/phase0_risks.md` R-04; `plans/next_tasks_after_phase0.md`.
- **Recommended action:** Constrain the MVP to an explicit, finite mission transition table, SQLite checkpoint/action records, and one HITL state. Do not add a LangGraph dependency unless a compatibility spike shows a measurable benefit with unchanged executor contracts.
- **Action:** **ACCEPT**
- **Reason:** The accepted decision is viable if its scope remains bounded; no architecture reversal is justified now.
- **Validation trigger if deferred:** Not applicable. Re-review only after restart/idempotency tests identify a concrete missing capability.

### MEDIUM — F-14: Docker unavailability is a deployment constraint, not an MVP blocker

- **Finding:** Docker CLI is available but the daemon is inaccessible; the plan correctly permits native local processes but still lists Docker verification as a future gate.
- **Evidence:** `results/phase0/environment_verification.json` records Docker CLI success and Docker-daemon warning. ADR-010 selects native local MVP processes.
- **Impact:** Treating Compose as mandatory would delay the Agent MVP; ignoring the constraint would make later service reproducibility claims unsupported.
- **Affected artifact:** ADR-010; `docs/environment/development_environment_v1.md`; `plans/phase0_risks.md` R-07.
- **Recommended action:** Continue with native local MVP processes. Request Docker access only when a containerized service-plane task has an explicit exit criterion; do not run an image pull without authorization.
- **Action:** **ACCEPT**
- **Reason:** The existing deployment decision already contains the correct bounded workaround.
- **Validation trigger if deferred:** Before Docker Compose, PostgreSQL container, or multi-service deployment validation.

### LOW — F-15: ROS namespace and discovery details are too early to freeze operationally

- **Finding:** The architecture proposes final ROS namespaces and dedicated discovery configuration before a cell ID, native robot PC, physical network, or hardware topology exists.
- **Evidence:** `docs/architecture/system_architecture_v1.md` lists planned namespaces; the environment verification could not inspect usable interface statistics and identifies the WSL host as development-only.
- **Impact:** Premature values can create churn, but the conceptual boundary is correct and poses no MVP block.
- **Affected artifact:** `docs/architecture/system_architecture_v1.md`; `docs/environment/development_environment_v1.md`.
- **Recommended action:** Retain namespace patterns as placeholders and finalize actual `ROS_DOMAIN_ID`, discovery scope, network ACLs, and cell ID only during native robot-network validation.
- **Action:** **DEFER**
- **Reason:** No current evidence supports operational values; placeholder names preserve the architecture intent safely.
- **Validation trigger if deferred:** Before first native ROS 2 robot/simulator integration run.

### LOW — F-16: Fixture-first simulation is the correct MVP choice despite installed simulation capability

- **Finding:** Existing Nav2/Gazebo capability could tempt the project into premature simulator work, but deterministic fixture-driven failures remain the shortest path to Agent reliability evidence.
- **Evidence:** The installed package inventory includes Nav2/Gazebo components, while `docs/architecture/system_architecture_v1.md` and ADR-003 specify fixture-driven MVP simulation.
- **Impact:** Without an explicit acceptance, correcting F-02 could be misread as a mandate to build a simulator immediately.
- **Affected artifact:** ADR-003; ADR-002; `plans/next_tasks_after_phase0.md`.
- **Recommended action:** Keep fixture-first Day-10 validation. Use the available Nav2/Gazebo stack only when a later integration task needs to prove a real ROS adapter or an otherwise uncovered failure mode.
- **Action:** **ACCEPT**
- **Reason:** This aligns with the project’s scope priority: deepen Agent/VLA evidence before simulator polish.
- **Validation trigger if deferred:** Not applicable. Reassess only when INT-001 has a specific ROS integration criterion.

## Required use of existing ROS 2 capabilities

The following is a boundary rule for future work, not an implementation instruction:

| Capability | Reuse | Do not reimplement |
|---|---|---|
| AMR navigation | Nav2 actions/commander, planner/controller stack, behavior-tree local recovery, lifecycle manager | route planner, local obstacle recovery, controller, Nav2 lifecycle manager |
| Manipulator staging/execution | MoveIt planning scene, named poses, collision checking, pre-grasp/retreat, trajectory execution | custom motion planner, collision checker, generic trajectory generator |
| Hardware control | `ros2_control`, controller manager, standard joint-state interfaces | controller lifecycle and hardware-interface framework |
| Diagnostics | ROS diagnostics / `diagnostic_updater`; map the result into PHM eligibility policy | a second generic robot health transport |
| Localization and frames | `robot_localization` and TF2 | custom state fusion or frame transform system |
| Simulation | installed Gazebo/Nav2 minimal packages where they validate a real adapter | a bespoke simulator when fixtures already cover the failure case |

## Architecture-freeze recommendation

| Category | Findings |
|---|---|
| **Critical findings** | F-01 MVP sequencing; F-02 inaccurate ROS/simulator capability evidence; F-03 missing VLA go/no-go. |
| **High findings** | F-04 MVP complexity; F-05 Nav2 recovery ownership; F-06 MoveIt/ros2_control authority; F-07 WSL/device inference; F-08 camera hypothesis; F-09 hosted-model validation; F-10 physical-action reconciliation. |
| **Must be fixed before MVP** | F-01, F-02, F-03, F-04. F-05, F-06, and F-10 must be fixed before their ROS/VLA/physical integration work begins. F-07 must be fixed before scheduling physical hardware work. |
| **Can be deferred** | F-08, F-09, F-11, F-12, F-15, each with the stated trigger. |
| **Explicitly accepted** | F-13 bounded custom state machine, F-14 native-process MVP without Docker daemon, F-16 fixture-first simulation. |

**Current recommendation: CONDITIONAL GO for architecture freeze.** The core separation of Agent semantics, deterministic execution, VLA skill, and ROS 2 integration is sound. However, freeze is conditional on reconciling the three critical planning/evidence findings and constraining the Day-10 scope before MVP implementation starts. No physical robot or VLA runtime work is authorized by this review.

## P0-002 resolution record

> Recorded: 2026-08-28. Resolutions update the referenced planning/architecture artifacts; no application feature or physical validation was performed.

| Finding | Resolution status | Resolution evidence |
|---|---|---|
| F-01 | Resolved | Next-task plan places MVP-001 directly after tooling and makes VLA readiness parallel. |
| F-02 | Resolved | Environment manifest, ADR-002, and ADR-003 record verified installed Nav2/Gazebo capability without claiming a configured robot environment. |
| F-03 | Resolved as gate | ADR-004 and risk R-01 define a two-working-day VLA `GO`/`NO-GO`; a real readiness result remains deferred. |
| F-04 | Resolved | `day10_mvp_scope_v1.md` freezes a single-process fixture composition. |
| F-05 | Resolved | Architecture and contract plan assign Nav2 local recovery versus executor business recovery. |
| F-06 | Resolved | Contract plan assigns MoveIt and `ros2_control` staging/collision/trajectory/controller ownership. |
| F-07 | Resolved | WSL observations are labeled environment-local; native robot-PC inventory is a later gate. |
| F-08, F-09 | Deferred with trigger | Camera and real-provider smoke checks remain explicitly gated before Dataset V1 and real-provider claims. |
| F-10 | Resolved | `action_id` and `unknown -> reconcile` semantics are added to the contract/architecture. |
| F-11, F-12 | Deferred with bounded MVP | SQLite/JSONL and the MVP contract profile are retained; multi-service escalation has explicit triggers. |
| F-13, F-14, F-16 | Accepted | Bounded custom state machine, native-process MVP, and fixture-first simulation remain accepted. |
| F-15 | Deferred | ROS network values remain placeholders until native network validation. |

**P0-002 architecture-freeze result: CONDITIONAL GO.** The Day-10 software architecture is frozen. Physical VLA/robot, real-provider, and multi-service deployment decisions remain conditional on their stated gates.
