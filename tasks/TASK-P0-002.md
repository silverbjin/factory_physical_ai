# TASK-P0-002 — Phase 0 Review Resolution & Architecture Freeze

> Status: READY FOR EXECUTION
> Phase: Phase 0
> Depends on: TASK-P0-001
> Gate: Architecture Freeze + Day-10 MVP Scope Freeze
> Date: 2026-08-28

## Goal

Resolve `docs/reviews/P0-001_architecture_review.md` and convert the Phase 0 artifacts into a consistent Architecture v1.0 and Day-10 MVP Scope.

This is a **planning, architecture, contract, and evidence-reconciliation task**.

Do not implement application features in this task.

### Mandatory outcomes

1. Resolve F-01~F-03.
2. Resolve the architecture boundaries in F-04~F-07 and F-10.
3. Explicitly gate F-08~F-09.
4. Preserve accepted decisions F-13/F-14/F-16.
5. Update applicable ADRs.
6. Freeze Day-10 MVP scope.
7. Remove contradictions between architecture, contracts, risks, ADRs, and task plan.
8. Produce an architecture-freeze evidence artifact.

## Required inputs

Read:

* `AGENTS.md`
* `context/*.md`
* `docs/reviews/P0-001_architecture_review.md`
* `docs/architecture/system_architecture_v1.md`
* `docs/contracts/contract_plan.md`
* `docs/environment/development_environment_v1.md`
* `plans/phase0_risks.md`
* `plans/next_tasks_after_phase0.md`
* `results/phase0/environment_verification.json`
* all ADRs under `docs/architecture/adr/`

## Critical findings

### F-01

Decouple Day-10 Agent MVP from VLA/hardware readiness.

Required dependency:

```text
P0-002
  ├── MVP-001 Agent Vertical Slice
  └── P0-003 VLA Readiness Gate
```

### F-02

Correct Nav2/Gazebo evidence.

Distinguish:

```text
installed
configured
connected
end-to-end validated
```

Do not infer simulator readiness from package installation.

### F-03

Create a VLA Readiness Go/No-Go Gate containing:

* owner
* deadline
* GPU/VRAM requirement
* CUDA/Torch/LeRobot verification
* camera
* manipulator
* connectivity
* remote-GPU fallback
* budget/approval
* safety authorization
* Go criteria
* No-Go criteria
* fallback action

Do not fabricate or replace real VLA fine-tuning evidence.

## High findings

### F-04

Day-10 must use:

* one mission executor
* one factory-tool gateway
* in-process deterministic fakes
* named navigation/VLA/verification fakes
* SQLite/JSONL
* native local processes

### F-05

Navigation authority:

**Nav2**

* navigation execution
* planner/controller behavior
* local recovery
* lifecycle behavior

**Deterministic Runtime**

* retry budget
* wait
* reroute request
* robot reassignment
* HITL

Agent must not issue raw Nav2 commands or paths.

### F-06

Manipulation authority:

**MoveIt**

* named poses
* planning scene
* collision validation
* pre-grasp/retreat
* trajectory planning/execution

**ros2_control**

* controller lifecycle
* hardware interfaces

**VLA**

* approved sensorimotor manipulation skill only

VLA cannot bypass safety gates or directly control actuators.

### F-07

Correct WSL interpretation:

> device not exposed to the current WSL development environment

Do not infer physical hardware absence from WSL device visibility.

### F-08

Defer camera validation to P0-004.

Validate:

* timestamps
* robot-state alignment
* calibration
* actual FPS/resolution
* storage bandwidth

### F-09

Keep fake provider for MVP.

Before real-provider claims validate:

* structured tool call
* model/version
* latency
* cost/token data where available
* malformed output
* timeout/outage behavior

### F-10

Define durable physical-action reconciliation:

```text
REQUESTED
  ↓
EXECUTING
  ↓
SUCCEEDED / FAILED
  ↓
UNKNOWN
  ↓
RECONCILING
  ↓
RESUMED / ESCALATED
```

Minimum fields:

```text
mission_id
action_id
idempotency_key
schema_version
timestamp
deadline
status
error
retryable
component_version
```

The LLM must never determine the result of an ambiguous physical action.

## Medium findings

### F-11

Use SQLite/JSONL for MVP.

PostgreSQL/collector telemetry becomes necessary only for explicitly gated multi-process/concurrent/long-running validation.

### F-12

Define an MVP Contract Profile containing:

* schema version
* mission/request/action or idempotency ID
* timestamp/deadline
* result/error/retryability
* component version

### F-13

Accept a bounded finite state machine.

Do not create a generic workflow engine.

### F-14

Accept native local processes for MVP.

Docker is not an MVP prerequisite.

## Low findings

### F-15

Keep ROS namespace/network values as placeholders until native robot/simulator validation.

### F-16

Accept fixture-first Day-10 validation.

Installed Nav2/Gazebo capability is an integration option, not an MVP obligation.

## Required architecture

Update:

`docs/architecture/system_architecture_v1.md`

The authority chain must be explicit:

```text
Factory Operator
      ↓
Factory Agent
      ↓
Structured Mission / Tool Call
      ↓
Deterministic Runtime / Policy
      ↓
 ┌────┴─────────────────┐
 ↓                      ↓
Factory Tools           Robot Skills
                        ↓
                  ┌─────┴─────┐
                  ↓           ↓
                 Nav2       MoveIt
                  ↓           ↓
                  └─────┬─────┘
                        ↓
                  ros2_control
                        ↓
                      Robot
```

## Required contract changes

Update:

`docs/contracts/contract_plan.md`

Define:

* Navigation Skill
* Manipulation/VLA Skill
* Physical Action Status
* Reconciliation
* MVP Contract Profile

## Required task-order change

Update:

`plans/next_tasks_after_phase0.md`

Use:

```text
P0-002 Architecture Freeze
       │
       ├──────────────→ P0-003 VLA Readiness Gate
       │
       ↓
MVP-001 Agent Vertical Slice
       ↓
MVP-002 Mission State
       ↓
MVP-003 Tool Gateway
       ↓
MVP-004 Failure / Recovery
       ↓
MVP-005 Persistence / Evidence
       ↓
MVP-006 Normal E2E
       ↓
MVP-007 Single Failure Recovery
       ↓
MVP-008 Day-10 Demo / Release
```

## ADR update matrix

Update applicable existing ADRs:

| ADR     | Required change                                                      |
| ------- | -------------------------------------------------------------------- |
| ADR-001 | hardware uncertainty, native robot-PC, MoveIt/ros2_control authority |
| ADR-002 | Nav2 reuse, local vs business recovery                               |
| ADR-003 | installed vs configured Gazebo, fixture-first MVP                    |
| ADR-004 | VLA readiness gate and fallback                                      |
| ADR-005 | camera settings as hypothesis                                        |
| ADR-006 | fake provider and real-provider validation gate                      |
| ADR-007 | bounded FSM and deterministic execution                              |
| ADR-008 | SQLite/JSONL and durable action records                              |
| ADR-009 | structured MVP evidence                                              |
| ADR-010 | native-process MVP                                                   |

Do not silently replace existing architecture decisions.

## Day-10 MVP

### Business scenario

A factory operator submits a natural-language parts-transfer mission.

The Factory Agent:

1. interprets the mission;
2. selects deterministic tools;
3. executes through a controlled skill interface;
4. observes the result;
5. handles one injected failure through bounded recovery.

### Normal path

```text
Operator
   ↓
Natural Language Mission
   ↓
Factory Agent
   ↓
Structured Tool Call
   ↓
Deterministic Runtime
   ↓
Factory/WMS Fake
   ↓
Robot Skill Fake
   ↓
Mission State
   ↓
Evidence / Trace
```

### Failure path

```text
Tool/Robot Failure
      ↓
Typed Failure Result
      ↓
UNKNOWN / Reconciliation if required
      ↓
Deterministic Recovery Policy
      ↓
Retry / Wait / Reassign / HITL
      ↓
Mission Complete or Escalated
```

### Explicitly out of scope

* physical robot
* physical camera
* VLA fine-tuning
* real WMS
* real MES
* real PHM
* real Fleet Manager
* multi-agent
* PostgreSQL
* Docker Compose
* Grafana
* Kubernetes
* custom navigation planner
* custom motion planner
* custom collision checker
* custom robot controller
* custom simulator

### Day-10 evidence

Generate machine-readable evidence for:

* mission result
* tool-call validity
* state-transition correctness
* timeout handling
* retry budget
* recovery result
* HITL escalation
* mission duration
* action correlation
* error category

Do not invent benchmark numbers.

## Architecture Freeze Gate

Freeze only if:

* [ ] F-01 resolved
* [ ] F-02 resolved
* [ ] F-03 resolved
* [ ] F-04 resolved
* [ ] F-05 boundary documented
* [ ] F-06 boundary documented
* [ ] F-07 wording corrected
* [ ] F-10 reconciliation documented
* [ ] Day-10 scope frozen
* [ ] applicable ADRs updated
* [ ] no contradiction remains across architecture/contracts/ADRs/risk/task plan

Allowed to remain deferred:

* F-08
* F-09
* F-11
* F-12
* F-15

Accepted:

* F-13
* F-14
* F-16

## Validation

Run:

```bash
git status
git diff --check
```

Then perform consistency review across:

```text
architecture
contracts
ADRs
risk register
task plan
Day-10 scope
```

Reject Freeze if:

* VLA still blocks MVP;
* Nav2 is incorrectly described as unavailable;
* Agent can issue raw ROS/Nav2 commands;
* VLA bypasses MoveIt/ros2_control/safety;
* physical timeout has no reconciliation;
* PostgreSQL/Docker/Grafana are MVP prerequisites;
* VLA has no Go/No-Go;
* MVP depends on physical hardware.

## Evidence

Create:

`results/phase0/P0-002_architecture_freeze.json`

Use:

```json
{
  "task": "TASK-P0-002",
  "status": "GO",
  "architecture_version": "v1.0",
  "mvp_scope": "day10",
  "critical_findings_resolved": [
    "F-01",
    "F-02",
    "F-03"
  ],
  "high_findings_resolved_for_architecture": [
    "F-04",
    "F-05",
    "F-06",
    "F-07",
    "F-10"
  ],
  "deferred_findings": [
    "F-08",
    "F-09",
    "F-11",
    "F-12",
    "F-15"
  ],
  "accepted_constraints": [
    "F-13",
    "F-14",
    "F-16"
  ],
  "physical_robot_authorized": false,
  "vla_runtime_authorized": false
}
```

If the gate fails, use:

```json
"status": "CONDITIONAL_GO"
```

and list the remaining blockers.

Never fabricate evidence.

## Scope restrictions

Do not modify:

```text
src/**
application implementation
physical robot configuration
production credentials/secrets
unrelated files
```

Do not install large models or datasets.

Do not silently change hardware topology.

## Final report

Report:

1. changed files;
2. F-01~F-16 disposition;
3. ADR changes;
4. final Agent/Runtime/VLA/ROS authority boundaries;
5. Day-10 MVP scope;
6. deferred risks;
7. validation results;
8. Architecture Freeze decision;
9. whether MVP-001 is authorized.

If the gate passes, state:

> `MVP-001 implementation is authorized.`

Otherwise:

> `MVP-001 implementation is NOT authorized.`

Do not start MVP implementation in this task.
