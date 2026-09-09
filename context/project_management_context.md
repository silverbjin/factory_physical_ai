# Factory Physical AI — Project Management Context

> Purpose: Lightweight project-management context for ChatGPT/Codex sessions.  
> Primary planning source: `Factory_Physical_AI_Project_Management_Task_Hierarchy.xlsx`  
> Scope: Project/WBS/Task/Git/Evidence operating rules.  
> This file intentionally does **not** replace Architecture/ADR/Contract documents.

---

## 1. Project Management Model

The project is managed through the following hierarchy:

```text
Project / 6-Week Roadmap
        ↓
Backlog / WBS
        ↓
Implementation Task Specification (`TASK-*.md`)
        ↓
Git Branch / Worktree / Codex Session
        ↓
Implementation
        ↓
Tests / Machine-readable Evidence
        ↓
Independent Read-only Review
        ↓
Commit / PR / Merge
        ↓
Backlog / Milestone / Deliverable Update
        ↓
Portfolio Evidence
```

### Backlog / WBS IDs

Examples:

```text
VLA-01 ... VLA-10
AGT-01 ... AGT-08
INT-01 ... INT-06
VAL-01 ... VAL-04
DOC-01 ... DOC-03
```

These IDs describe **project-management objectives**.

They are not Codex work orders and they are not Git branches.

### Implementation Task IDs

Examples:

```text
TASK-P0-004
TASK-P0-005
TASK-MVP-001
TASK-W1-001
TASK-W2-001
```

These are **bounded implementation specifications** that Codex can execute.

A Backlog item and an Implementation Task are not necessarily 1:1.

Example:

```text
VLA-01
  ├─ readiness gate
  ├─ blocker-resolution task(s)
  ├─ readiness re-gate
  └─ Week-1 primary implementation
```

---

## 2. Source-of-Truth Rules

Use the following authority model.

### Technical authority

When technical content conflicts:

```text
Frozen Architecture / ADR / Contract / Frozen Scope
        ↓
Approved Implementation Task
        ↓
Implementation
```

Architecture/ADR/Contract owns:

- system boundaries;
- component ownership;
- safety rules;
- API/contract semantics;
- frozen scope.

### Project-management authority

For planned work:

```text
Project Management Workbook
        ↓
project_management_context.md
        ↓
task_mapping.md
```

The workbook owns:

- WBS / Backlog;
- roadmap;
- priorities;
- planned dependencies;
- milestone definitions;
- deliverables;
- risk register;
- project-management decisions.

### Operational-state authority

For what has **actually happened**:

```text
Merged Git history + machine-readable Evidence
        ↓
current_project_state.md
```

If the workbook says `Planned` but Git/Evidence prove a task was merged, do not pretend the task is still Planned.
Instead, record the mismatch in `current_project_state.md` and reconcile the workbook at the next workbook-sync point.

### Completion authority

A feature or task is not complete because Codex says "implemented".

Completion requires:

```text
Implementation
→ Tests
→ Evidence
→ Exit Criteria
→ Independent Review
→ Commit
→ PR
→ Merge
```

---

## 3. 6-Week Roadmap Baseline

The workbook defines the following original roadmap.

| Week | Primary Focus | Objective | Exit Criteria / Key Result |
|---|---|---|---|
| Week 1 | VLA | VLA end-to-end lifecycle | Dataset V1 + fine-tuning + 30–50 quantitative trials |
| Week 2 | VLA | Dataset engineering + VLA service | Failure taxonomy + Dataset V2 + retraining + Skill Server |
| Week 3 | Agent | Factory Agent vertical slice | WMS/Fleet/PHM tools + 20 baseline missions |
| Week 4 | Agent | Production engineering | Persistence/retry/timeout/idempotency/HITL + 100 missions |
| Week 5 | Integration | Agent-AMR-VLA E2E | 3+ failure scenarios with recovery/replan |
| Week 6 | Validation | Production-like validation | Chaos + 24/72h soak + regression + readiness docs |

Important:

- These are the **original planning dates and objectives**.
- Readiness gates may delay or reshape execution.
- Do not silently compress or skip readiness/validation work to preserve the original calendar.
- Any revised schedule should be reconciled into the workbook at a milestone or weekly sync.

---

## 4. Milestone / Gate Baseline

| Gate | Milestone | Required Evidence | Exit Criterion |
|---|---|---|---|
| G0 | Phase 0 / Environment Freeze | ADR + environment manifest | Manipulator/AMR/VLA/Agent/DB/Observability choices |
| G1 | Day-10 Portfolio MVP | 3–5 min draft demo | Natural language → Agent → Robot/VLA → one recovery |
| G2 | VLA Engineering Complete | Dataset v2 + evaluation | Improvement + failure taxonomy + Skill Server |
| G3 | Agent Production Baseline | 100 Mission Eval | Persistence/retry/timeout/idempotency/HITL |
| G4 | E2E Physical AI Integration | Failure demos A/B/C | 3 failure types with recovery/replan |
| G5 | Production-like Validation | Chaos + Soak + Regression | 0 release blockers + production readiness |

Do not mark a Gate PASS merely because a related task was merged.
The Gate's own Required Evidence and Exit Criteria must be checked.

---

## 5. Backlog Completion Rules

A Backlog item is `Done` only when:

1. its Exit Criteria are satisfied;
2. required Implementation Tasks are merged;
3. required Evidence exists;
4. dependent deliverables are updated where applicable.

Examples:

```text
TASK-P0-004 merged
≠ VLA-01 Done
```

```text
TASK-MVP-002 merged
≠ AGT-01 necessarily Done
```

An Implementation Task only proves its own bounded scope.

---

## 6. Git / Branch / Worktree Operating Model

Accepted decision: `ADR-GIT-001`.

```text
master
= stable integration baseline

task/<task-id>-<slug>
= short-lived implementation branch

1 Task
= 1 Branch
= 1 Worktree
= 1 Codex implementation session
```

Recommended sequence:

```text
latest master
→ create task branch/worktree
→ Codex implements one task only
→ tests/evidence
→ read-only review
→ commit
→ PR
→ rebase on origin/master if needed
→ regression
→ merge
→ cleanup worktree/branch
```

### Parallelization allowed

Parallelize when:

- workstreams differ;
- file ownership does not overlap materially;
- shared contracts are already frozen/merged;
- neither task depends on the other's output.

### Parallelization prohibited / risky

Do not parallelize when:

- two tasks modify the same contract/state schema;
- one task depends on an unmerged contract change;
- two Codex sessions own the same core files;
- dependent tasks are being started before their predecessor merges.

### Merge Gate

Merge only when:

```text
Review = PASS
Tests = PASS
Evidence = PASS
Exit Criteria = PASS
```

For a gate task, `NO_GO` may still be a valid completed/merged outcome if the gate correctly produced evidence and a decision.

---

## 7. Implementation Task Specification Standard

Every new `TASK-P0-*`, `TASK-MVP-*`, `TASK-W1-*`, etc. should be derived from:

```text
Backlog / WBS
→ Current Project State
→ Dependency
→ Architecture / ADR / Contract
→ Existing Evidence
→ bounded implementation scope
```

Minimum structure:

1. Metadata
2. Related Backlog
3. Goal
4. Why This Task Exists
5. Inputs / Current Evidence
6. Dependency
7. Scope
8. Explicit Out-of-Scope
9. Architecture Constraints
10. Implementation Requirements
11. Required Outputs
12. Validation Plan
13. Evidence Rules
14. Exit Criteria
15. Gate / Decision Rules where applicable
16. Project State / Workbook Update Rules
17. Recommended Branch
18. Recommended Worktree
19. Recommended Commit Message
20. Codex Execution Prompt

### Task creation rule

Do not invent a new task number just because a problem appears.

Before creating a task:

- check `task_mapping.md`;
- check `current_project_state.md`;
- inspect existing `tasks/`;
- determine whether the work belongs to an existing task;
- if a new task is required, mark it `PROPOSED` until approved.

---

## 8. Evidence Policy

Portfolio and project claims must use measured evidence.

Valid evidence examples:

- test output;
- JSON/JSONL result;
- evaluation report;
- runtime version/device facts;
- benchmark data;
- failure/recovery trace;
- dataset manifest;
- Git commit linked to the evaluated artifact.

Invalid inference examples:

```text
unit tests 10/10 PASS
→ therefore Agent success rate = 100%
```

```text
CUDA visible
→ therefore SmolVLA training fits in VRAM
```

Use evidence labels when useful:

```text
MEASURED
DOCUMENTED
INFERRED
DEFERRED
NOT AVAILABLE
```

Never fabricate:

- VLA success rate;
- training improvement;
- latency;
- recovery rate;
- soak duration;
- benchmark counts.

---

## 9. Workbook Sync Policy

The workbook does **not** need to be attached or edited for every task.

### Every task / merge

Update lightweight repository context:

```text
context/current_project_state.md
context/task_mapping.md   # only if mapping/dependency changed
context/session_handoff.md
```

### Workbook sync

Reconcile the Excel workbook:

- every 3–5 tasks; or
- weekly; or
- at a milestone/gate; or
- when Backlog/dependency/roadmap materially changes.

Workbook reconciliation inputs:

```text
merged Git history
+ machine-readable Evidence
+ current_project_state.md
+ risk/decision changes
```

---

## 10. Workbook Risk Baseline

Current workbook risk categories include:

- `R-01` VLA teleoperation/data-collection stabilization delay;
- `R-02` GPU memory/training-time shortage;
- `R-03` LLM overreach into physical action;
- `R-04` ReAct runaway/token cost;
- `R-05` Agent-VLA-ROS interface instability;
- `R-06` over-investment in existing ROS/Gazebo functions;
- `R-07` soak test omitted due to schedule pressure;
- `R-08` portfolio becomes technology-listing rather than business result.

When a task exposes a concrete blocker, either:

- map it to an existing Risk; or
- create a proposed new Risk for the next workbook sync.

---

## 11. Accepted Project-Management Decisions

### ADR-GIT-001

Selected:

```text
master protection
+ short-lived Task branch
+ git worktree
+ PR/review/evidence before merge
```

### ADR-PM-001

Selected:

```text
Backlog/WBS
→ Implementation_Tasks (`TASK-*.md`)
→ Branch_Register (Git execution)
```

A Backlog may map to multiple Implementation Tasks.

---

## 12. Session Start Protocol

For a new Codex/ChatGPT engineering session, prefer reading:

```text
AGENTS.md
context/project_management_context.md
context/current_project_state.md
context/task_mapping.md
context/implementation_context.md
relevant architecture / ADR / contract
relevant TASK
relevant evidence
```

Do not require the Excel workbook unless:

- changing the project plan;
- performing workbook reconciliation;
- reviewing the full portfolio schedule;
- updating milestone/risk/dashboard data.
