# Factory Physical AI — Backlog ↔ Implementation Task Mapping

> Purpose: Lightweight mapping derived from the project-management workbook.  
> Rule: `Backlog ID != Implementation Task ID`.  
> Status labels used below:
>
> - `WORKBOOK` — directly defined in the current workbook.
> - `VERIFIED` — confirmed by current Git/evidence supplied after the workbook snapshot.
> - `PROPOSED` — operational follow-up not yet reconciled into the workbook.

---

## 1. Current VLA Dependency Chain

### Workbook baseline

```text
VLA-01
  ├─ TASK-P0-004  Readiness Gate
  └─ TASK-W1-001  Primary environment/HW I/O implementation
        ↓
VLA-02 / TASK-W1-002  Teleoperation
        ↓
VLA-03 / TASK-W1-003  Dataset V1
        ↓
VLA-04 / TASK-W1-004  Fine-tuning V1
        ↓
VLA-05 / TASK-W1-005  Baseline Evaluation
```

### Operational override after P0-004

`TASK-P0-004` produced `NO_GO`, therefore the simple workbook dependency
`P0-004 GO → W1-001` is currently not satisfied.

Current working decomposition:

```text
TASK-P0-004
VLA Readiness Gate
      ↓
    NO_GO
      ↓
TASK-P0-005
Runtime / CUDA / PyTorch / LeRobot / SmolVLA readiness
      ↓
additional blocker-resolution tasks as required [PROPOSED]
      ↓
TASK-P0-004R
VLA Readiness Re-Gate [PROPOSED]
      ↓ only if GO
TASK-W1-001
```

Possible additional tasks discussed operationally but **not yet approved in the workbook**:

```text
TASK-P0-006  Robot / Camera / Device I/O Readiness       [PROPOSED]
TASK-P0-007  Training Resource / Budget Readiness        [PROPOSED]
TASK-P0-004R VLA Readiness Re-Gate                       [PROPOSED]
```

Do not treat these as approved work orders until their necessity/dependency is reviewed.

---

## 2. VLA Backlog Mapping

| Backlog | Project Goal | Workbook Implementation Task(s) | Relationship | Current Mapping Note |
|---|---|---|---|---|
| VLA-01 | LeRobot environment + HW I/O verification | `TASK-P0-004`, `TASK-W1-001` | Readiness Gate + Primary implementation | `P0-004=NO_GO`; `P0-005` is an operational blocker-resolution task linked to VLA-01 |
| VLA-02 | Teleoperation workflow | `TASK-W1-002` | Primary implementation | Blocked until VLA-01/authorization chain |
| VLA-03 | Dataset V1 (~50 episodes) | `TASK-W1-003` | Primary implementation | Must follow stable teleoperation |
| VLA-04 | SmolVLA baseline fine-tuning | `TASK-W1-004` | Primary implementation | Requires Dataset V1 + approved runtime/resource |
| VLA-05 | Baseline evaluation 30–50 trials | `TASK-W1-005` | Validation/evidence | Measured results only |
| VLA-06 | Failure taxonomy | `TASK-W2-001` | Primary implementation | Follows baseline evaluation |
| VLA-07 | Targeted Dataset V2 | `TASK-W2-002` | Primary implementation | Driven by measured failures |
| VLA-08 | VLA v2 retraining/regression | `TASK-W2-003` | Training + regression | Compare against V1 |
| VLA-09 | VLA Skill Server | `TASK-W2-004` | Skill/API implementation | `/health`, `/version`, `/execute` or contract-equivalent |
| VLA-10 | Model/Dataset version registry | `TASK-W2-005` | Registry/evidence | Link model ↔ data ↔ commit ↔ eval |

---

## 3. Agent Backlog Mapping

| Backlog | Project Goal | Workbook Implementation Task(s) | Relationship |
|---|---|---|---|
| AGT-01 | Factory mission state schema | `TASK-MVP-002`, `TASK-W3-003` | MVP precursor + Week implementation |
| AGT-02 | WMS/Fleet/PHM mock API | `TASK-MVP-003`, `TASK-W3-001`, `TASK-W3-002` | MVP precursor + Factory tools/contracts |
| AGT-03 | Agent graph + tool routing | `TASK-MVP-001`, `TASK-MVP-006`, `TASK-W3-004`, `TASK-W3-005` | MVP precursor/validation + Week implementation |
| AGT-04 | Mission persistence/checkpoint | `TASK-MVP-005`, `TASK-W4-002` | MVP precursor + persistence |
| AGT-05 | Retry/backoff/timeout | `TASK-MVP-004`, `TASK-MVP-007`, `TASK-W4-001`, `TASK-W4-003` | MVP recovery precursor + Week reliability |
| AGT-06 | Idempotency / duplicate prevention | `TASK-W4-004` | Primary implementation |
| AGT-07 | Human-in-the-loop approval gate | `TASK-W4-005` | Primary implementation |
| AGT-08 | 100 Mission Evaluation harness | `TASK-W4-007`, `TASK-W4-008` | Benchmark + regression |

Important:

The Day-10 MVP tasks are implementation precursors/evidence, not automatic proof that the Week-3/Week-4 Backlog Exit Criteria are already complete.

---

## 4. Integration Backlog Mapping

| Backlog | Project Goal | Workbook Implementation Task(s) | Relationship |
|---|---|---|---|
| INT-01 | ROS 2 execution adapter | `TASK-W5-001` | Integration contract/adapter |
| INT-02 | AMR navigation mission | `TASK-W5-002` | AMR integration |
| INT-03 | VLA manipulation mission | `TASK-W5-003`, `TASK-W5-004` | VLA/Vision + handoff |
| INT-04 | Inventory mismatch recovery | `TASK-W5-006` | Failure injection/recovery |
| INT-05 | VLA failure recovery | `TASK-W5-006`, `TASK-W5-008` | Failure injection + analysis |
| INT-06 | PHM robot reassignment | `TASK-W5-006`, `TASK-W5-008` | Failure injection + analysis |

---

## 5. Validation Backlog Mapping

| Backlog | Project Goal | Workbook Implementation Task(s) | Relationship |
|---|---|---|---|
| VAL-01 | Agent/VLA/ROS observability | `TASK-W4-006`, `TASK-W6-002` | Observability + regression evidence |
| VAL-02 | Chaos test harness | `TASK-W6-003` | Chaos validation |
| VAL-03 | 24h soak | `TASK-W6-004` | Soak validation |
| VAL-04 | 72h soak / regression | `TASK-W6-004`, `TASK-W6-005` | Long soak + rollback |

---

## 6. Documentation / PM Mapping

| Backlog | Project Goal | Workbook Implementation Task(s) | Relationship |
|---|---|---|---|
| DOC-01 | ADR / architecture governance | `TASK-P0-001`, `TASK-P0-002`, `TASK-P0-002R` | Architecture/ADR governance |
| DOC-02 | Production Readiness | `TASK-W6-006` | Production readiness |
| DOC-03 | 3–5 min E2E Demo + README | `TASK-MVP-008`, `TASK-W6-007` | MVP release + final portfolio release |

---

## 7. Verified Day-10 MVP Operational State

The current Git history supplied after the workbook snapshot confirms that the following MVP implementation sequence has already been completed on `master`:

```text
TASK-MVP-001  Factory Agent Vertical Slice
TASK-MVP-002  Mission / Action State Model
TASK-MVP-003  Deterministic Tool Gateway + Fakes
TASK-MVP-004  Timeout / Reconciliation / Bounded Recovery
TASK-MVP-005  Persistence + Structured Evidence
TASK-MVP-006  Canonical Normal E2E
TASK-MVP-007  Canonical Single-Failure Recovery E2E
TASK-MVP-008  Day-10 Portfolio Release
```

Therefore the workbook's old `Planned` values for these tasks are stale and should be reconciled during the next workbook sync.

Do **not** automatically mark the related Week-3/Week-4 Backlog items Done.
Their Backlog Exit Criteria remain separate.

---

## 8. Current Task Mapping: P0-005

```text
Implementation Task:
TASK-P0-005

Related Backlog:
VLA-01

Relationship:
Blocker resolution after VLA Readiness NO_GO

Current branch:
task/p0-005-vla-runtime

Current worktree:
../factory_physical_ai_p0_005

Purpose:
Establish and verify isolated VLA software runtime:
- `.venv-vla`
- PyTorch CUDA
- actual CUDA tensor operation
- LeRobot pinned runtime/import
- SmolVLA module/config discovery
- RTX 2060 6GB capability classification

Does not complete:
- VLA-01
- physical robot I/O
- camera I/O
- teleoperation
- Dataset V1
- fine-tuning
- W1 authorization
```

---

## 9. Task Dependency Rules

Before generating a new `TASK-*.md`:

1. identify Related Backlog;
2. inspect existing mapped tasks;
3. inspect current operational state;
4. check predecessor merge/evidence;
5. determine whether the work is:
   - existing task scope;
   - corrective/re-gate scope;
   - a genuinely new task;
6. mark new task IDs `PROPOSED` until approved.

### Current protected dependency

```text
TASK-W1-001
```

must **not** begin while VLA readiness authorization remains false.

A successful P0-005 alone does not automatically authorize W1-001.

---

## 10. Workbook Reconciliation Queue

At the next workbook sync, review at least:

1. `TASK-P0-004`
   - Planned → Merged
   - Gate Result → NO_GO
2. `VLA-01`
   - Not Started → Blocked/In Progress as appropriate
3. add `TASK-P0-005` to `Implementation_Tasks` / `Branch_Register`
4. reconcile MVP-001 through MVP-008 with actual Git history
5. review G0/G1 milestone status against their exact evidence requirements
6. revise original Week-1/Week-2 dates if readiness work materially shifted the schedule
7. update `R-02` GPU/resource risk with measured RTX 2060 6GB facts
