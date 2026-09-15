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

Post-gate planning direction:

```text
ROS 2 Jazzy      = simulation/system integration middleware
Gazebo Harmonic  = authoritative AMR/navigation/sensor/system simulator
MuJoCo           = VLA/manipulation physics engineering backend
Deterministic    = contract/lifecycle regression baseline
```

`TASK-SIM-003` must freeze exact runtime/version/source identities and the fidelity policy before SIM-004+ implementation. v1 real-time Gazebo↔MuJoCo dual-world co-simulation is not planned.

---

## Git Context

Last accepted integration baseline recorded by prior reconciliation:

```text
origin/master @ e3cc92b
Merge pull request #12 from silverbjin/task/p0-SIM-
```

The current repository tree includes Simulation Lane artifacts and `_v2` Codex workflow prompts, so the previous stale `task/PM_rev` topology note must not be treated as current truth.

Before creating `TASK-SIM-003` or a new Task worktree, refresh:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin
git rev-parse origin/master
```

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

The immediate planning action is:

```text
Create and review TASK-SIM-003
— Simulation Toolchain Strategy & Baseline Freeze
```

The specification should bind accepted SIM evidence and freeze the proposed simulator roles:

```text
ROS 2 Jazzy
Gazebo Harmonic
MuJoCo
L0/L1/L2 fidelity policy
no real-time dual-authority Gazebo↔MuJoCo co-simulation
```

It must verify/capture exact runnable toolchain facts before authorizing SIM-004+; it must not implement the downstream Gazebo or MuJoCo backends itself.

Physical readiness remains a separate future track. Do not start `TASK-W1-001` or downstream physical/training work while P0-004R remains `NO_GO`.

---

## New-Session Reading Order

For project planning:

```text
AGENTS.md
context/current_project_state.md
context/project_management_context.md
context/task_mapping.md
context/simulation_task_mapping_v2.md   # current proposed post-gate backlog
context/simulation_task_mapping_v1.md   # frozen historical gate input; read only when required
relevant accepted evidence / TASK only
```

For a routed TASK command, follow `AGENTS.md` and the active Task's bounded context manifest instead of recursively reading the repository.

---

## Known Management / Reconciliation Notes

- The external project-management workbook has been updated with Simulation Week A/B planning, but the workbook is intentionally managed outside this repository.
- The current repository tree supplied during reconciliation contains the `_v2` Codex workflow prompts referenced by `AGENTS.md`; treat the earlier missing-prompt note as resolved, subject to branch verification.
- The last recorded PM branch was based on a stale local master, but the current tree contains the Simulation Lane files. Revalidate branch ancestry/HEAD rather than assuming the old divergence still exists.
- `simulation_task_mapping_v1.md` is immutable accepted history; post-gate simulator planning belongs in `simulation_task_mapping_v2.md`.

Resolve any remaining branch divergence before treating the PM revision as integration-ready.

---

## After Each Merge

Update:

```text
context/current_project_state.md
context/session_handoff.md
```

Update `context/task_mapping.md` only when global mapping changes. Never edit frozen `context/simulation_task_mapping_v1.md` in place. Update `context/simulation_task_mapping_v2.md` only when the proposed post-gate backlog/dependencies change, and version/freeze it through review when it becomes authoritative. Reconcile the external workbook every 3–5 Tasks, weekly, or at a Gate/Milestone.
