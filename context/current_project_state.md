# Factory Physical AI — Current Project State

> Purpose: Compact operational truth for the next engineering session.
> Last reconciled: 2026-09-15 (Asia/Seoul).
> Planning baseline: `Factory_Physical_AI_Project_Management_Task_Hierarchy.xlsx` (not present in this worktree).
> Operational truth: merged Git history and accepted machine-readable evidence take precedence over stale workbook cells.

---

## 1. Executive State

```text
Architecture / Day-10 MVP        COMPLETE
VLA software runtime             READY
Physical device I/O              BLOCKED
Training resource path           BLOCKED
VLA readiness re-gate            NO_GO
Simulation Lane                  SIM_GO / AUTHORIZED
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
  -> future SIM-003+ may be specified separately
```

`SIM_GO` does not change the physical VLA gate, Week-task authorization, Dataset V1, fine-tuning, or physical-motion authorization.

---

## 2. Git Baselines and Worktree State

Latest locally known remote-tracking integration baseline:

```text
origin/master @ e3cc92b
Merge pull request #12 from silverbjin/task/p0-SIM-
observed commit time: 2026-09-15 12:47:43 +0900
```

Current PM worktree:

```text
branch: task/PM_rev
HEAD:   b145c9d chore(codex): PM rev_2
tracking: origin/task/PM_rev (in sync at inspection time)
working tree before this reconciliation: clean
```

Branch topology anomaly:

```text
local master @ eb73a86
origin/master @ e3cc92b
local master is 26 commits behind origin/master
task/PM_rev is based on local master and therefore does not contain
the 51 Simulation Lane files already present on origin/master
```

Before merging `task/PM_rev`, reconcile it with current `origin/master` and rerun the relevant checks. Do not interpret absent Simulation Lane files in this worktree as deleted project work.

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

The simulation lane validates bounded software contracts and deterministic smoke behavior without physical devices. Future `TASK-SIM-003+` work remains unspecified/proposed until a separately reviewed Task specification exists.

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

There is no active product Implementation Task in this PM worktree. The current branch is project-management/workflow maintenance:

```text
task/PM_rev
```

The next product work must be selected explicitly from one of two lanes:

1. Simulation: create and review a bounded `TASK-SIM-003` specification under the accepted Simulation Lane mapping.
2. Physical readiness: define bounded hardware-selection/device/safety remediation before another physical VLA re-gate.

Do not start `TASK-W1-001`, `TASK-W1-002`, Dataset V1, fine-tuning, or physical motion under the current authorization state.

---

## 7. Repository Structure

```text
AGENTS.md                 routing and context-budget guardrails
context/                  PM state, mappings, and session recovery
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

The `docs/simulation`, `results/simulation`, `results/reviews`, `src/simulation_runtime`, and SIM task/test files are currently visible on `origin/master`, not in this stale-base PM worktree.

---

## 8. Project-Management Reconciliation Queue

The workbook is not present in this repository worktree, so Excel synchronization remains pending. At the next workbook sync, update at least:

- P0-005, P0-006, P0-007, and P0-004R as merged tasks with their truthful task-specific outcomes;
- VLA-01 as blocked/in progress, not Done;
- the final P0-004R gate as `NO_GO` and Week-1 authorization as false;
- the independent Simulation Lane, accepted SIM tasks, and effective `SIM_GO` authorization;
- candidate hardware inventory without marking targets frozen;
- R-01/R-02 and device/safety/resource risks;
- original Week-1/Week-2 schedule impact;
- completed MVP-001 through MVP-008 facts without auto-completing Week-3/Week-4 Backlogs.

---

## 9. Repository Management Issues

### Broken prompt references on `task/PM_rev`

`AGENTS.md` currently routes to these paths:

```text
prompts/codex/implement_task_v2.md
prompts/codex/fix_review_findings_v2.md
prompts/codex/read_only_review_v2.md
prompts/codex/create_task_spec_v2.md
prompts/codex/task_history_recording_v2.md
```

None of those files exists in this worktree. The only corresponding workflow files currently present are the non-`_v2` implementation, fix, review, and history files; there is no task-creation prompt. This makes exact TASK routing incomplete until the references and files are reconciled.

### Branch reconciliation required

Because `task/PM_rev` predates the Simulation Lane merges, rebase/merge conflict handling and validation are required before this PM revision can be safely integrated. No Git history rewrite or branch update was performed during this state-document reconciliation.
