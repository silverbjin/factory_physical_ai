# Factory Physical AI — Session Handoff

> Use this file as the compact starting context for a new ChatGPT/Codex session.  
> For deeper PM rules read `context/project_management_context.md`.  
> For WBS/TASK mapping read `context/task_mapping.md`.  
> For current operational detail read `context/current_project_state.md`.

---

## Project

```text
Factory Physical AI Agent — autonomous parts supply & recovery system
```

Core engineering objective:

```text
LLM Agent
→ semantic mission/tool/replan
→ deterministic runtime
→ bounded robot/VLA skills
→ evidence-driven recovery
```

The LLM does not own raw physical control or ambiguous physical success decisions.

---

## Current Position

```text
Architecture Freeze
        ↓
Day-10 MVP complete
        ↓
TASK-P0-004 VLA Readiness Gate
        ↓
NO_GO
        ↓
TASK-P0-005 runtime blocker resolution   ← CURRENT
```

Latest known master:

```text
1c1faa1
Merge pull request #1 from silverbjin/task/p0-004-vla-readiness
```

---

## Current Task

```text
TASK-P0-005
VLA Runtime Environment Enablement & CUDA/LeRobot/SmolVLA Verification
```

Related Backlog:

```text
VLA-01
LeRobot development environment + hardware I/O verification
```

Branch:

```text
task/p0-005-vla-runtime
```

Worktree:

```text
../factory_physical_ai_p0_005
```

Current stage:

```text
Task specification preparation/review
```

Do not assume `TASK-P0-005.md` exists without checking the repo.

---

## Latest Runtime Facts

Latest measured in WSL:

```text
Ubuntu 24.04 / WSL2

nvidia-smi = PASS
GPU = NVIDIA GeForce RTX 2060-class
VRAM = 6144 MiB
Driver = 581.57
nvidia-smi CUDA field = 13.0
/dev/dxg = present
```

These facts mean GPU exposure now appears available.

They do **not** prove:

- PyTorch CUDA works;
- CUDA Toolkit 13.0 is installed;
- LeRobot is compatible;
- SmolVLA can train in 6GB VRAM.

P0-005 must re-measure and create evidence.

---

## P0-004 Decision

```text
VLA Readiness Gate = NO_GO
TASK-W1-001 authorized = false
```

P0-004 is already merged.

Do not rewrite P0-004 evidence to make it GO.
It is historical evidence of the earlier environment state.

---

## P0-005 Scope

P0-005 should cover only:

```text
.venv-vla
Python/uv
PyTorch CUDA
CUDA tensor execution
LeRobot version decision + import
SmolVLA module/config discovery
RTX 2060 6GB capability classification
machine-readable runtime evidence
```

Out of scope:

```text
robot/manipulator I/O
camera
physical teleoperation
Dataset V1
SmolVLA fine-tuning
benchmark
Skill Server
ROS integration
Agent integration
```

---

## Next-Task Protection

A successful P0-005 does **not** automatically authorize W1-001.

Current intended control flow:

```text
P0-005
  ↓
remaining readiness blockers
  ↓
P0-004R re-gate [PROPOSED]
  ↓
GO or explicitly bounded CONDITIONAL_GO
  ↓
W1-001
```

Possible but not yet workbook-approved blocker tasks:

```text
P0-006 device/camera readiness   [PROPOSED]
P0-007 training resource         [PROPOSED]
P0-004R readiness re-gate        [PROPOSED]
```

Review dependency necessity before creating them.

---

## Project-Management Rules

```text
Backlog
≠ Task

Task implemented
≠ Task complete

Task merged
≠ Backlog done

Portfolio claim
= measured evidence only
```

One task should use:

```text
1 Task
= 1 Branch
= 1 Worktree
= 1 Codex implementation session
```

Merge only after:

```text
Review PASS
Tests PASS
Evidence PASS
Exit Criteria PASS
```

A gate task may merge with `NO_GO` if the gate executed correctly.

---

## Files to Read at a New Session

Prefer:

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

Do not request the Excel workbook for an ordinary single-task implementation.

Use the workbook only for:

- weekly/milestone reconciliation;
- roadmap changes;
- backlog restructuring;
- risk/milestone/dashboard updates.

---

## Immediate Recommended Prompt

For the next task-specification session:

```text
First verify:
- pwd
- git branch --show-current
- git status

Read:
- AGENTS.md
- context/project_management_context.md
- context/current_project_state.md
- context/task_mapping.md
- context/implementation_context.md
- relevant architecture/ADR/contracts
- P0-004 report/evidence

Create `tasks/TASK-P0-005.md` only.

Derive it from VLA-01 and the current P0-004 NO_GO blockers.

Do not implement it.
Do not install packages.
Do not start W1-001.
Stop after reporting the created task specification for human review.
```

---

## After Each Merge

Update:

```text
context/current_project_state.md
context/session_handoff.md
```

Update `task_mapping.md` only if mapping/dependency changes.

Reconcile Excel every 3–5 Tasks, weekly, or at a Gate/Milestone.
