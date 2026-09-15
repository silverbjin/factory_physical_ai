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

### Verified operational chain after P0-004R

`TASK-P0-004` produced `NO_GO`, therefore the simple workbook dependency
`P0-004 GO → W1-001` is currently not satisfied.

Merged/evidenced decomposition:

```text
TASK-P0-004
VLA Readiness Gate
      ↓
    NO_GO
      ↓
TASK-P0-005
Runtime / CUDA / PyTorch / LeRobot / SmolVLA = RUNTIME_READY [VERIFIED]
      ↓
TASK-P0-006 Device I/O = DEVICE_IO_BLOCKED [VERIFIED]
      ↓
TASK-P0-007 Training Resource = TRAINING_RESOURCE_BLOCKED [VERIFIED]
      ↓
TASK-P0-004R VLA Readiness Re-Gate = NO_GO [VERIFIED]
      ↓
TASK-W1-001 remains NOT AUTHORIZED
```

P0-006, P0-007, and P0-004R were originally operational proposals but are now merged facts. The workbook still requires reconciliation. A future physical remediation task or another re-gate remains `PROPOSED` until separately approved.

---

## 2. VLA Backlog Mapping

| Backlog | Project Goal | Workbook Implementation Task(s) | Relationship | Current Mapping Note |
|---|---|---|---|---|
| VLA-01 | LeRobot environment + HW I/O verification | `TASK-P0-004`, `TASK-W1-001` | Readiness Gate + Primary implementation | `P0-005=RUNTIME_READY`; `P0-006=DEVICE_IO_BLOCKED`; `P0-007=TRAINING_RESOURCE_BLOCKED`; `P0-004R=NO_GO`; `W1-001` unauthorized |
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

## 8. Verified Phase-0 Readiness Task Mapping

```text
Related Backlog:
VLA-01

TASK-P0-004   original readiness gate              NO_GO
TASK-P0-005   software runtime remediation          RUNTIME_READY
TASK-P0-006   robot/camera/device I/O readiness     DEVICE_IO_BLOCKED
TASK-P0-007   training resource readiness           TRAINING_RESOURCE_BLOCKED
TASK-P0-004R  evidence-based readiness re-gate      NO_GO
```

All five tasks are merged. They complete their bounded assessment/remediation scope, but they do not complete VLA-01 because its physical readiness and authorization Exit Criteria remain unsatisfied.

---

## 9. Independent Simulation Lane Mapping

The accepted frozen gate baseline is maintained in:

```text
context/simulation_task_mapping_v1.md
```

Post-gate planning is maintained separately in:

```text
context/simulation_task_mapping_v2.md
```

Do not edit v1 in place: SIM-GATE evidence binds its exact SHA-256. v2 is a `DRAFT / PROPOSED` overlay and does not change the accepted gate.

Verified operational sequence on `origin/master`:

```text
ADR-Simulation-Lane-v1
  -> TASK-SIM-C01  SIM_CONTRACT_GAPS_RESOLVED / ACCEPT
  -> TASK-SIM-001  SIM_CONTRACT_PROFILE_READY / ACCEPT
  -> TASK-SIM-002  SIM_SMOKE_READY / ACCEPT
  -> TASK-SIM-GATE SIM_GO / ACCEPT
  -> simulation_lane_authorized = true
```

Proposed post-gate backlog:

| Task | Proposed responsibility | Dependency | Status |
|---|---|---|---|
| `TASK-SIM-003` | freeze `SIM_BASELINE_V1` | accepted `SIM_GO` | `PROPOSED` |
| `TASK-SIM-004` | Navigation Skill deterministic backend | accepted SIM-003 baseline | `PROPOSED` |
| `TASK-SIM-005` | VLA Skill deterministic backend | accepted SIM-003 baseline | `PROPOSED` |
| `TASK-SIM-006` | Verification deterministic backend | accepted SIM-003 baseline | `PROPOSED` |
| `TASK-SIM-007` | Mission Executor/Simulation Skill integration | accepted SIM-004 through SIM-006 | `PROPOSED` |
| `TASK-SIM-008` | canonical normal Simulation E2E | accepted SIM-007 | `PROPOSED` |
| `TASK-SIM-009` | failure/recovery scenario suite | accepted SIM-008 | `PROPOSED` |
| `TASK-SIM-010` | observability/evidence/replay/regression | accepted SIM-009 | `PROPOSED` |
| `TASK-SIM-E2E` | Simulation Qualification Gate | accepted SIM-003 through SIM-010 | `PROPOSED` |

These are backlog definitions, not approved work orders. Only SIM-003 is currently eligible to proceed to Task-specification authoring. The Simulation Lane is independent of the workbook Week graph and cannot authorize W1, Dataset V1, training, hardware freeze, or physical motion.

Proposed post-Simulation hardware transition:

| Task | Proposed responsibility | Dependency | Status |
|---|---|---|---|
| `TASK-HW-SELECT-001` | evaluate manipulator, AMR, camera, and edge-compute candidates | accepted `SIM_E2E_QUALIFIED` | `PROPOSED` |

The intended follow-up is candidate evaluation, explicit ADR amendment/supersession, independent Architecture Review, and only then Hardware Target Freeze. Candidate inventory is not a selection decision.

---

## 10. Task Dependency Rules

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

The accepted `P0-004R=NO_GO` explicitly keeps W1-001 unauthorized. `SIM_GO` does not override that decision.

---

## 11. Workbook Reconciliation Queue

At the next workbook sync, review at least:

1. record P0-004, P0-005, P0-006, P0-007, and P0-004R as merged with their exact task-specific decisions;
2. keep VLA-01 Blocked/In Progress and W1-001 unauthorized;
3. add the frozen independent Simulation Lane and accepted SIM-C01/SIM-001/SIM-002/SIM-GATE facts;
4. record `SIM_GO` without changing any physical/Week authorization;
5. add SIM-003 through SIM-010 and SIM-E2E as `PROPOSED`, not approved/started;
6. add HW-SELECT-001 and its later ADR/review/freeze flow as `PROPOSED`;
7. reconcile MVP-001 through MVP-008 with actual Git history;
8. review G0/G1 milestone status against their exact evidence requirements;
9. revise original Week-1/Week-2 dates if readiness work materially shifted the schedule;
10. update GPU/resource and hardware/device/safety risks using accepted evidence.
