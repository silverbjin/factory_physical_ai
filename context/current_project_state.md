# Factory Physical AI — Current Project State

> Purpose: Compact operational truth for the next engineering session.  
> Planning baseline: `Factory_Physical_AI_Project_Management_Task_Hierarchy.xlsx`  
> Operational truth is reconciled from the workbook plus the latest Git/evidence facts supplied after that workbook snapshot.

---

## 1. Current Phase

```text
Phase 0 / VLA Readiness Blocker Resolution
```

The Day-10 Factory Agent MVP has already been implemented and released.

The active engineering focus is now the VLA readiness path before Week-1 real VLA work.

---

## 2. Current Master Baseline

Latest known master after P0-004 PR merge:

```text
1c1faa1  Merge pull request #1 from silverbjin/task/p0-004-vla-readiness
```

Previous Day-10/portfolio baseline included:

```text
0c84097 docs(portfolio): document accepted MVP engineering case study
0b8c224 docs(mvp): publish day-10 physical AI portfolio release
95cb075 test(mvp): validate single-failure recovery end to end
6e5e549 test(mvp): validate canonical normal end-to-end mission
6561809 feat(mvp): persist mission lifecycle and structured evidence
cbb002d feat(mvp): implement timeout reconciliation and bounded recovery
2c0270c feat(mvp): add deterministic factory tool gateway and skill fakes
06fded7 feat(mvp): define durable mission and action state model
51a9bef feat(mvp): establish factory agent vertical slice
1e7cb88 docs(arch): reconcile day-10 scope and finalize architecture freeze
```

Interpretation:

- Day-10 MVP implementation is complete in Git.
- P0-004 readiness evidence has been merged after the workbook snapshot.
- The workbook's older task/branch status cells require later reconciliation.

---

## 3. Completed Major Work

### Architecture / Phase 0

```text
TASK-P0-001   complete
TASK-P0-002   complete
TASK-P0-002R  complete
Architecture Freeze / Day-10 scope reconciliation complete
```

### Day-10 MVP

```text
TASK-MVP-001 through TASK-MVP-008
```

are operationally complete based on supplied Git history.

The MVP demonstrated the frozen:

```text
1 Mission
+ 1 Failure
+ 1 Recovery
+ Evidence
```

scope.

Do not infer that all Week-3/Week-4 Backlog Exit Criteria are complete merely from the MVP precursor work.

---

## 4. TASK-P0-004 Result

Task:

```text
TASK-P0-004 — VLA Readiness Gate
```

Git status:

```text
Merged to master via PR #1
```

Gate result:

```text
VLA Readiness Gate = NO_GO
TASK-W1-001 authorized = false
```

Key blockers measured/documented by P0-004:

- PyTorch CUDA execution not verified at that time;
- LeRobot runtime absent;
- SmolVLA prerequisites unverified;
- manipulator/device path unresolved;
- camera path unresolved;
- teleoperation/safety path unresolved;
- training resource/budget unresolved.

Important:

`NO_GO` is a valid successful gate outcome.
It means the gate worked and blocked unauthorized VLA implementation.

---

## 5. New Runtime Facts After P0-004

The runtime environment changed after the original P0-004 measurement.

Latest user-measured WSL facts:

```text
WSL2 / Ubuntu 24.04

nvidia-smi = PASS

NVIDIA-SMI:
580.102.01

Driver Version:
581.57

Driver-reported CUDA Version:
13.0

GPU:
NVIDIA GeForce RTX 2060-class

VRAM:
6144 MiB

/dev/dxg:
present
```

Interpretation:

- WSL GPU exposure now appears available.
- This does **not** yet prove PyTorch CUDA works.
- `CUDA Version: 13.0` from `nvidia-smi` does not prove CUDA Toolkit 13.0 is installed.
- LeRobot and SmolVLA runtime remain unverified.
- RTX 2060 6GB training suitability remains unverified/limited and must not be assumed.

---

## 6. Active Task

```text
TASK-P0-005
```

Working title:

```text
VLA Runtime Environment Enablement & CUDA/LeRobot/SmolVLA Verification
```

Related Backlog:

```text
VLA-01
```

Git:

```text
branch:
task/p0-005-vla-runtime

worktree:
../factory_physical_ai_p0_005

base:
master @ 1c1faa1
```

Current task stage:

```text
TASK specification preparation / review
```

Do not assume `tasks/TASK-P0-005.md` exists until verified in the repository.

---

## 7. P0-005 Intended Boundary

P0-005 should resolve only the software/runtime readiness blockers:

```text
project-local `.venv-vla`
→ Python version
→ uv environment management
→ PyTorch CUDA
→ actual CUDA tensor operation
→ LeRobot version/pin/import
→ SmolVLA module/config discovery
→ RTX 2060 6GB capability classification
```

P0-005 should not perform:

- manipulator I/O implementation;
- camera implementation;
- physical teleoperation;
- Dataset V1 collection;
- SmolVLA fine-tuning;
- VLA benchmark;
- Skill Server implementation;
- ROS/Agent integration.

P0-005 success by itself does **not** authorize W1-001.

---

## 8. Current Backlog Status — Operational Interpretation

### VLA-01

Workbook baseline:

```text
Not Started
```

Operational interpretation:

```text
BLOCKED / IN PROGRESS
```

because:

- readiness work has started;
- P0-004 completed with NO_GO;
- P0-005 blocker-resolution work has started;
- VLA-01 Exit Criteria are not satisfied.

Do not mark VLA-01 Done.

### VLA-02 through VLA-10

```text
Not Started / blocked by preceding VLA chain
```

### Agent / Integration / Validation Backlog

Use the workbook plan as baseline.
Day-10 MVP precursor work exists, but Week-level Backlog completion must be assessed against each Backlog Exit Criterion before changing status.

---

## 9. Open Blockers

### Runtime

```text
PyTorch CUDA               NOT VERIFIED
actual CUDA tensor op       NOT VERIFIED
LeRobot runtime             NOT VERIFIED
SmolVLA module/config       NOT VERIFIED
6GB VRAM suitability        NOT VERIFIED / likely constrained
```

### Physical Device

```text
manipulator selection       unresolved
robot USB/serial I/O        unresolved
camera identity/I/O         unresolved
state/gripper path          unresolved
```

### Safety / Teleoperation

```text
workspace limits            unresolved
manual abort/E-stop         unresolved
supervised teleop path      unresolved
```

### Resource

```text
training host/budget        unresolved
```

---

## 10. Proposed Follow-up Tasks

These are **PROPOSED**, not yet workbook-approved work orders:

```text
TASK-P0-006
Robot / Camera / Device I/O Readiness

TASK-P0-007
Training Resource / Budget Readiness

TASK-P0-004R
VLA Readiness Re-Gate
```

Dependency should be reviewed before creating these files.

In particular, do not automatically make P0-007 a hard blocker for W1-001 if W1-001 does not require model training.
A gate should block only what is necessary for the next authorized task.

---

## 11. Protected Next-Step Rule

Current protected path:

```text
P0-004 = NO_GO
       ↓
P0-005 runtime blocker resolution
       ↓
resolve remaining blockers required for next task
       ↓
P0-004R readiness re-gate
       ↓
GO / explicitly bounded CONDITIONAL_GO
       ↓
TASK-W1-001
```

Until a reviewed re-gate authorizes it:

```text
TASK-W1-001 = NOT AUTHORIZED
```

Also prohibited:

```text
Dataset V1
SmolVLA fine-tuning
real VLA benchmark claims
unreviewed physical motion
```

---

## 12. Current Risks

Relevant workbook risks:

### R-01 — VLA teleoperation/data collection delay

Still open.

### R-02 — GPU memory/training time

Still open and now has new measured context:

```text
RTX 2060-class
6GB VRAM
```

This should be reconciled into the workbook later.

### R-05 — Agent-VLA-ROS interface instability

Future integration risk; preserve typed bounded interfaces.

### R-06 — over-investment in existing ROS/Gazebo

Do not divert readiness work into unrelated ROS implementation.

---

## 13. Next Immediate Action

Recommended next action:

```text
Create/review `tasks/TASK-P0-005.md`
```

using:

- `AGENTS.md`;
- `context/project_management_context.md`;
- this file;
- `context/task_mapping.md`;
- relevant architecture/ADR/contracts;
- P0-004 report/evidence.

After human review:

```text
new Codex implementation session
→ Implement TASK-P0-005 only
→ Tests/Evidence
→ Independent Review
→ Commit
→ PR
→ Merge
→ update this file
```

---

## 14. Workbook Reconciliation Pending

The Excel workbook should be updated at the next sync point to reflect at least:

- P0-004 merged;
- P0-004 decision = NO_GO;
- VLA-01 blocked/in progress;
- P0-005 added;
- actual MVP-001…008 completion;
- branch/register status;
- risks R-01/R-02;
- original schedule impact.

Do not require this Excel sync before every individual Task.
