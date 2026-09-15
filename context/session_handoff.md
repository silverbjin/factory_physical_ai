# Factory Physical AI — Session Handoff

> Compact recovery context for a new planning/Codex session.
> Last reconciled: 2026-09-15.
> Detailed operational truth: `context/current_project_state.md`.

---

## Project

```text
Factory Physical AI Agent — autonomous parts supply & recovery system
```

Core boundary:

```text
LLM Agent
-> semantic mission/tool/replan
-> deterministic runtime
-> bounded robot/VLA skills
-> evidence-driven recovery
```

The LLM does not own raw physical control or ambiguous physical-success decisions.

---

## Current Position

```text
Architecture / Day-10 MVP      COMPLETE

Physical VLA lane:
P0-004 NO_GO
  -> P0-005 RUNTIME_READY
  -> P0-006 DEVICE_IO_BLOCKED
  -> P0-007 TRAINING_RESOURCE_BLOCKED
  -> P0-004R NO_GO

Independent Simulation Lane:
SIM-C01 accepted
  -> SIM-001 accepted
  -> SIM-002 accepted
  -> SIM-GATE accepted as SIM_GO
  -> simulation_lane_authorized = true
```

`SIM_GO` is simulation-only. It does not authorize Week-1 work, Dataset V1, VLA fine-tuning, hardware freeze, teleoperation, or physical motion.

---

## Git Context

Latest locally known remote-tracking integration baseline:

```text
origin/master @ e3cc92b
Merge pull request #12 from silverbjin/task/p0-SIM-
```

Current worktree:

```text
branch: task/PM_rev
HEAD: b145c9d
tracking origin/task/PM_rev
```

Important: local `master @ eb73a86` is 26 commits behind `origin/master`. This PM branch predates the Simulation Lane merges, so reconcile it with `origin/master` before integration.

---

## Current Authorization

```text
simulation_lane_authorized       true
TASK-W1-001 authorized           false
TASK-W1-002 authorized           false
Dataset V1 authorized            false
SmolVLA fine-tuning authorized   false
physical motion authorized       false
hardware target frozen           false
```

Known hardware is candidate inventory only:

```text
myCobot 280 Pi
myAGV JN 2023
Intel RealSense D455
Jetson Orin Nano
```

---

## Open Blockers

Physical path:

- official target hardware/camera selection;
- stable identity, access, state, command, and gripper paths;
- bounded camera acquisition;
- workspace/motion limits;
- abort/E-stop and supervised teleoperation prerequisites.

Training path:

- execution mode and primary compute resource;
- storage plan;
- budget policy/feasibility;
- fallback compute strategy;
- model-specific training fit.

The local CUDA/LeRobot/SmolVLA code/config runtime is ready, but model loading, inference, and training fit were not established.

---

## Next Work Selection

No product Implementation Task is active in this PM worktree.

Choose and specify one bounded direction:

1. Simulation Lane: create/review `TASK-SIM-003` under the accepted simulation mapping.
2. Physical readiness: create/review hardware-selection and device/safety remediation work before another physical VLA re-gate.

Do not start `TASK-W1-001` or downstream physical/training work while P0-004R remains `NO_GO`.

---

## New-Session Reading Order

For project planning:

```text
AGENTS.md
context/current_project_state.md
context/project_management_context.md
context/task_mapping.md
context/simulation_task_mapping_v1.md   # from current origin/master
relevant accepted evidence / TASK only
```

For a routed TASK command, follow `AGENTS.md` and the active Task's bounded context manifest instead of recursively reading the repository.

---

## Known Management Anomalies

- The workbook is not present in this worktree; milestone/workbook reconciliation remains pending.
- `AGENTS.md` points to five `_v2` workflow prompt paths that do not exist here; the Create workflow has no corresponding prompt file at all.
- Simulation Lane files exist on `origin/master` but not on this stale-base PM branch.

Resolve these branch/routing issues before treating the PM revision as integration-ready.

---

## After Each Merge

Update:

```text
context/current_project_state.md
context/session_handoff.md
```

Update `context/task_mapping.md` or `context/simulation_task_mapping_v1.md` only when mapping/dependencies change. Reconcile the workbook every 3–5 Tasks, weekly, or at a Gate/Milestone.
