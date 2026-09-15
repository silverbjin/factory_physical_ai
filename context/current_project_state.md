# Factory Physical AI — Current Project State

> Purpose: Compact operational truth for the next engineering session.
> Last reconciled: 2026-09-15 (Asia/Seoul).
> Planning baseline: external `Factory_Physical_AI_Project_Management_Task_Hierarchy_Simulation_Updated.xlsx` (project-management workbook; not stored in this repository worktree).
> Operational truth: merged Git history and accepted machine-readable evidence take precedence over stale workbook cells.
> Simulation planning overlay: `context/simulation_task_mapping_v2.md`.

---

## 1. Executive State

```text
Architecture / Day-10 MVP        COMPLETE
VLA software runtime             READY
Physical device I/O              BLOCKED
Training resource path           BLOCKED
VLA readiness re-gate            NO_GO
Simulation Lane                  SIM_GO / AUTHORIZED
Simulation toolchain direction   ROS 2 Jazzy + Gazebo Harmonic + MuJoCo / PROPOSED FOR SIM-003 FREEZE
Post-gate SIM backlog            PROPOSED / DESIGNING
Week-1 physical VLA work         NOT AUTHORIZED
```

The project has split into two deliberately separate paths:

```text
Physical VLA path
P0-004 NO_GO
  -> P0-005 runtime READY
  -> P0-006 device I/O BLOCKED
  -> P0-007 training resource BLOCKED
  -> P0-004R NO_GO

Simulation Lane
ADR + executable contract remediation
  -> SIM-001 contract profile accepted
  -> SIM-002 deterministic smoke accepted
  -> SIM-GATE accepted as SIM_GO
  -> SIM-003 through SIM-E2E backlog PROPOSED
```

`SIM_GO` does not change the physical VLA gate, Week-task authorization, Dataset V1, fine-tuning, or physical-motion authorization.

---

## 2. Git Baselines and Worktree State

Last accepted integration baseline recorded by the previous reconciliation:

```text
origin/master @ e3cc92b
Merge pull request #12 from silverbjin/task/p0-SIM-
observed commit time: 2026-09-15 12:47:43 +0900
```

The repository tree supplied for this update already contains the accepted Simulation Lane artifacts, `_v2` Codex workflow prompts, `simulation_task_mapping_v2.md`, executable Simulation contract/schema, and SIM acceptance/evidence files.

Exact current branch, HEAD, ahead/behind state, and worktree cleanliness were **not re-measured** as part of this context rewrite. Before creating or implementing `TASK-SIM-003`, refresh:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/master
git log --oneline --decorate -10
```

Do not reuse the earlier stale `task/PM_rev` branch-topology claim as current truth without revalidation.

---

## 3. Completed Major Work

### Architecture / Phase 0

```text
TASK-P0-001    complete
TASK-P0-002    complete
TASK-P0-002R   complete
Architecture Freeze / Day-10 scope reconciliation complete
```

### Day-10 MVP

```text
TASK-MVP-001 through TASK-MVP-008
```

are merged and operationally complete. The demonstrated frozen scope remains:

```text
1 Mission + 1 Failure + 1 Recovery + Evidence
```

This does not automatically complete the Week-3/Week-4 Backlog Exit Criteria.

### VLA readiness remediation and re-gate

| Task | Merge / acceptance state | Task-specific result |
|---|---|---|
| `TASK-P0-004` | merged | `NO_GO` |
| `TASK-P0-005` | merged; independent review accepted | `RUNTIME_READY` |
| `TASK-P0-006` | merged after finding fixes | `DEVICE_IO_BLOCKED` |
| `TASK-P0-007` | merged; independent review accepted | `TRAINING_RESOURCE_BLOCKED` |
| `TASK-P0-004R` | merged via PR #7 | `NO_GO` |

A blocked readiness result is a valid successful outcome for a gate/verifier task. It does not mean the implementation task failed.

### Simulation Lane

The following work is present on `origin/master` and accepted/merged:

| Work | Result |
|---|---|
| Simulation Lane ADR and task mapping | frozen independent lane |
| `TASK-SIM-C01` | `SIM_CONTRACT_GAPS_RESOLVED`, accepted |
| `TASK-SIM-001` | `SIM_CONTRACT_PROFILE_READY`, accepted |
| `TASK-SIM-002` | `SIM_SMOKE_READY`, accepted |
| `TASK-SIM-GATE` | `SIM_GO`, accepted; `simulation_lane_authorized = true` |

The simulation lane validates bounded software contracts and deterministic smoke behavior without physical devices. The proposed post-gate plan now escalates fidelity from deterministic contract fixtures to ROS 2 Jazzy / Gazebo Harmonic navigation and system simulation, plus MuJoCo manipulation-physics validation. The post-gate delivery sequence is planned in `context/simulation_task_mapping_v2.md`, but every `TASK-SIM-003+` item remains `PROPOSED` until its own specification is created and approved.

The accepted `context/simulation_task_mapping_v1.md` remains frozen and hash-bound to SIM-GATE evidence. It must not be edited in place to record later planning state.

---

## 4. Current Gate and Authorization Truth

The accepted P0-004R result is:

```text
VLA Readiness Gate = NO_GO
TASK-W1-001 authorized = false
TASK-W1-002 authorized = false
Dataset V1 authorized = false
SmolVLA fine-tuning authorized = false
Physical motion authorized = false
```

The accepted Simulation Gate result is:

```text
TASK-SIM-GATE = SIM_GO
simulation_lane_authorized = true
```

Preserved invariants:

```text
SIM_GO != W1 authorization
simulation fixture != Dataset V1
simulation behavior != physical execution evidence
owned/candidate hardware != frozen target
runtime ready != training ready
```

---

## 5. Resolved and Open Readiness Areas

### Resolved software runtime blockers

Accepted P0-005 evidence establishes:

```text
Python                    3.12.3 in isolated project-local environment
LeRobot                   0.4.4 pinned/import verified
PyTorch                   2.10.0+cu130
torchvision               0.25.0+cu130
GPU                       RTX 2060 Max-Q, 6144 MiB
PyTorch CUDA              PASS
actual CUDA tensor op     PASS
SmolVLA module/config     PASS at non-model, non-training scope
```

Not established by this evidence:

```text
model weight loading
local inference
local training/fine-tuning fit
6 GiB model-specific training feasibility
```

### Open physical-device and safety blockers

Accepted P0-006/P0-004R evidence leaves these mandatory areas blocked or not verified:

- final manipulator/controller and camera selection;
- stable robot/camera identity and host access;
- robot state-feedback and safe read-only observation;
- actuator/gripper command-path definition;
- bounded camera acquisition/configuration;
- workspace and motion constraints;
- manual abort/E-stop strategy;
- supervised teleoperation prerequisites.

Known owned/candidate hardware recorded on `origin/master`:

```text
Manipulator:  myCobot 280 Pi
AMR:          myAGV JN 2023
Camera:       Intel RealSense D455
Edge compute: Jetson Orin Nano
```

These are candidates only. They are not architecturally frozen, operationally ready, or physically authorized.

### Open training-resource blockers

Accepted P0-007/P0-004R evidence leaves unresolved:

- training execution mode;
- primary compatible compute resource;
- storage capacity/path for model, data, and checkpoints;
- budget policy and feasibility;
- fallback compute strategy.

The local RTX 2060 6 GiB runtime is useful for development, but accepted evidence does not prove SmolVLA training fit.

---

## 6. Active Work and Next Authorized Direction

There is no active product Implementation Task in this PM worktree. The active management activity is post-gate Simulation Lane backlog design:

```text
branch: task/PM_rev
planning state: TASK-SIM-003+ backlog design
simulation platform direction: ROS 2 Jazzy + Gazebo Harmonic + MuJoCo
all downstream SIM tasks: PROPOSED
```

### Proposed Simulation Platform Roles

The v2 planning direction assigns one clear responsibility to each simulation technology:

```text
ROS 2 Jazzy
= system middleware / launch / Skill integration / Nav2-facing execution

Gazebo Harmonic
= authoritative system-level simulator for AMR, sensors, navigation,
  ROS 2 integration, and normal system E2E

MuJoCo
= manipulation-physics engineering backend for VLA Skill validation,
  contact/grasp/action behavior, and manipulation fault scenarios

Deterministic fixtures
= L0 contract/lifecycle/failure semantics baseline
```

The v1 plan does **not** use Gazebo and MuJoCo as two simultaneously authoritative world simulators. Real-time Gazebo↔MuJoCo physics co-simulation is outside the current scope. MuJoCo supplies component-level manipulation evidence; Gazebo supplies the authoritative integrated system world.

Exact installed package/version facts, runnable entry points, bridge/runtime availability, and source hashes are **not yet accepted evidence**. `TASK-SIM-003` must capture and freeze them before downstream simulator implementation.

Proposed Simulation Lane sequence:

| Task | Proposed scope | Status |
|---|---|---|
| `TASK-SIM-003` | Simulation Toolchain Strategy & Baseline Freeze: bind accepted SIM artifacts plus ROS 2 Jazzy / Gazebo Harmonic / MuJoCo runtime identities, fidelity policy, and baseline hashes | `PROPOSED` |
| `TASK-SIM-004` | Navigation Skill ROS 2 Jazzy + Gazebo Harmonic backend, including Nav2-facing success/failure/timeout behavior | `PROPOSED` |
| `TASK-SIM-005` | VLA Skill MuJoCo manipulation-physics backend with deterministic contract regression | `PROPOSED` |
| `TASK-SIM-006` | simulator-independent Verification backend/adapters across deterministic, Gazebo, and MuJoCo observations | `PROPOSED` |
| `TASK-SIM-007` | Mission Executor + Skill integration with ROS 2 Jazzy orchestration and explicit backend profiles | `PROPOSED` |
| `TASK-SIM-008` | canonical normal Gazebo system E2E | `PROPOSED` |
| `TASK-SIM-009` | multi-layer failure/recovery suite: contract, Gazebo navigation/system, MuJoCo manipulation, and verification mismatch faults | `PROPOSED` |
| `TASK-SIM-010` | simulator-aware observability, evidence, replay, and regression | `PROPOSED` |
| `TASK-SIM-E2E` | Simulation Qualification Gate requiring deterministic, Gazebo, and MuJoCo evidence | `PROPOSED` |

Only `TASK-SIM-003` is the next candidate for specification. `SIM_GO` makes that specification eligible for consideration; it does not make an absent Task specification executable.

Planned delivery order:

```text
SIM Week A:
SIM-003
-> SIM-004 Gazebo Navigation
   + SIM-005 MuJoCo Manipulation
-> SIM-006 Cross-Simulator Verification

SIM Week B:
SIM-007 Mission Integration
-> SIM-008 Gazebo Normal System E2E
-> SIM-009 Multi-layer Failure / Recovery
-> SIM-010 Observability / Regression
-> SIM-E2E Qualification Gate
-> proposed TASK-HW-SELECT-001
-> ADR amendment/review and explicit Hardware Target Freeze
```

`TASK-HW-SELECT-001` remains `PROPOSED`. It will evaluate myCobot 280 Pi, myAGV JN 2023, Intel RealSense D455, and Jetson Orin Nano as candidates after Simulation E2E qualification; the simulator models used before that point do not preselect physical targets.

Do not start `TASK-W1-001`, `TASK-W1-002`, Dataset V1, fine-tuning, or physical motion under the current authorization state.

---

## 7. Repository Structure

```text
AGENTS.md                 routing and context-budget guardrails
context/                  PM state, frozen v1/proposed v2 mappings, session recovery
plans/                    roadmap/risk/scope planning artifacts
tasks/                    bounded TASK specifications
prompts/codex/            implementation/review/fix/history workflows
docs/architecture/        system architecture and ADRs
docs/contracts/           typed contracts and schemas
docs/environment|hardware|vla|simulation/
                           readiness and engineering reports
docs/task_history/        implementation/review/fix audit trail
src/                      MVP and simulation runtime modules
scripts/                  bounded runners and evidence verifiers
tests/                    focused and regression tests
results/                  machine-readable evidence and acceptances
```

The current repository tree includes accepted `docs/simulation`, `results/simulation`, `results/reviews`, `src/simulation_runtime`, SIM task/test files, frozen v1 mapping, and proposed v2 planning overlay. Exact Git ancestry remains subject to the refresh commands in Section 2.

---

## 8. Project-Management Reconciliation Queue

The external project-management workbook has been revised to include Simulation Week A/B planning through the current post-gate state, but it is not stored in this repository worktree. Git/evidence remains the execution truth; workbook status remains the planning/control view. At the next workbook sync, update at least:

- P0-005, P0-006, P0-007, and P0-004R as merged tasks with their truthful task-specific outcomes;
- VLA-01 as blocked/in progress, not Done;
- the final P0-004R gate as `NO_GO` and Week-1 authorization as false;
- the independent Simulation Lane, accepted SIM tasks, and effective `SIM_GO` authorization;
- proposed SIM-003 through SIM-010, SIM-E2E, and HW-SELECT-001 backlog entries, without marking them approved or started;
- the proposed simulator-role split: ROS 2 Jazzy integration, Gazebo Harmonic system simulation, MuJoCo manipulation-physics validation, with no v1 real-time dual-engine co-simulation;
- candidate hardware inventory without marking targets frozen;
- R-01/R-02 and device/safety/resource risks;
- original Week-1/Week-2 schedule impact;
- completed MVP-001 through MVP-008 facts without auto-completing Week-3/Week-4 Backlogs.

---

## 9. Repository Management Issues

### Workflow prompt routing

The current repository tree supplied during this reconciliation contains the `_v2` Codex workflow prompts referenced by `AGENTS.md`, including task creation, implementation, review, fix, and task-history recording. Treat that routing issue as resolved for the current repository layout; verify the exact files again after any branch rebase/merge.

### Git state refresh required

The previous PM context recorded a stale-base `task/PM_rev` branch, but the current repository tree now contains Simulation Lane artifacts. Re-measure branch ancestry, HEAD, and worktree cleanliness before creating the next Task branch. This context update does not perform Git mutation or claim that the old branch divergence still exists.
