# TASK-P0-004 — VLA Readiness Gate

> Status: READY FOR EXECUTION  
> Phase: Phase 0 / Parallel Readiness Track  
> Workstream: VLA  
> Related Backlog: `VLA-01`  
> Recommended Branch: `task/p0-004-vla-readiness`  
> Recommended Worktree: `../factory_physical_ai_p0_004`  
> Depends on: Architecture Freeze (`TASK-P0-002R = GO`)  
> Blocks MVP Lane: **NO**  
> Authorizes Dataset/Fine-tuning Work: **ONLY IF THIS GATE = GO**

---

# 1. Goal

Verify whether the current development environment is ready to begin the real VLA implementation track.

This task is a **readiness gate**, not a VLA feature implementation task.

The goal is to produce a reproducible and evidence-backed answer to:

> Can this repository and development environment safely proceed to the first VLA implementation task without introducing unresolved GPU, runtime, device, camera, teleoperation, dataset, or framework blockers?

This task must finish with one of:

```text
GO
CONDITIONAL_GO
NO_GO
```

`GO` authorizes the next VLA implementation task.

`CONDITIONAL_GO` means limited VLA work may proceed only under explicitly documented constraints.

`NO_GO` means real VLA implementation must not begin until the blocking conditions are resolved.

---

# 2. Why This Task Exists

The Agent MVP and VLA track are intentionally independent.

Architecture rule:

```text
Architecture Freeze
        │
        ├── Day-10 MVP / Agent Lane
        │
        └── VLA Readiness Lane
```

Therefore:

- failure of this task must **not** block the Agent/MVP lane;
- success of this task must **not** expand the frozen Day-10 MVP scope;
- this task does not authorize VLA integration into Day-10 MVP;
- this task only determines whether the independent VLA implementation track can start.

---

# 3. Scope

This task verifies readiness in the following areas.

## R1 — Host / OS / Python Environment

Verify and record:

- host OS / distribution;
- kernel;
- Python version;
- virtual environment strategy;
- package manager strategy;
- available disk space;
- available system memory;
- relevant environment variables.

The result must be reproducible by another engineer.

---

## R2 — GPU / CUDA Runtime

If a GPU is required for the selected VLA workflow, verify:

- GPU model;
- GPU visibility from the intended execution environment;
- driver visibility;
- CUDA runtime visibility where applicable;
- PyTorch CUDA availability;
- device count;
- basic tensor allocation on GPU;
- available GPU memory at verification time.

Do not assume that installed packages imply working GPU execution.

If the current task can proceed CPU-only for limited readiness checks, explicitly document which checks are CPU-only and which later tasks still require GPU.

---

## R3 — LeRobot Runtime

Verify the intended LeRobot environment at the minimum level required for the next task.

Confirm:

- package/import succeeds;
- package version or source revision is recorded;
- core runtime imports required by the planned VLA workflow succeed;
- no unresolved dependency conflict blocks execution;
- reproducible install/setup command is documented.

Do not fine-tune a model in this task.

---

## R4 — SmolVLA Model Readiness

Verify only model/runtime readiness required before the first real VLA task.

Minimum checks:

- planned model identifier is documented;
- model/config discovery succeeds where applicable;
- required dependencies are available;
- model-loading prerequisites are understood;
- expected compute/memory constraints are documented;
- no benchmark or training claim is fabricated.

A full fine-tuning run is out of scope.

---

## R5 — Robot / Manipulator Interface Readiness

Verify the selected manipulator path at the level available in the current environment.

Determine and record:

- target manipulator;
- connection method;
- SDK / ROS / serial / USB dependency;
- device visibility;
- command path expected for teleoperation;
- state feedback path;
- gripper path;
- safety limitations.

If physical hardware is not attached to this development PC:

```text
NOT EXPOSED IN CURRENT ENVIRONMENT
```

must not be interpreted as:

```text
HARDWARE UNSUPPORTED
```

In that case, define a separate native robot-PC or physical-device validation requirement.

Do not implement robot-control application logic.

---

# 4. Camera / Observation Readiness

Verify the intended observation source.

Record:

- camera model;
- connection type;
- expected resolution;
- expected FPS;
- color format;
- timestamp source;
- intended mounting/location;
- expected VLA observation fields.

If the camera is physically available, perform a basic capture test.

If not available, mark the check as deferred with a concrete trigger.

This task does not require calibration or final dataset capture.

---

# 5. Teleoperation Readiness

The goal is not to build the full teleoperation workflow.

Verify that the planned control path is technically feasible.

Document:

```text
Human Input
    ↓
Teleoperation Interface
    ↓
Robot Command Interface
    ↓
Manipulator
```

and:

```text
Robot / Camera State
    ↓
Observation Capture
    ↓
Dataset Recorder
```

Confirm:

- intended teleoperation mechanism;
- command-rate expectation;
- state feedback availability;
- gripper control path;
- emergency stop / manual abort path;
- major unresolved blockers.

Actual sustained teleoperation validation belongs to the next implementation task.

---

# 6. Dataset Pipeline Readiness

Verify the expected Dataset V1 path without collecting the actual Dataset V1.

Define:

- dataset root;
- episode structure;
- observation fields;
- action fields;
- timestamps;
- task/language annotation;
- dataset versioning approach;
- validation approach;
- storage estimate.

Expected conceptual flow:

```text
Teleoperation
    ↓
Observation + Action
    ↓
Episode
    ↓
Dataset V1
    ↓
Validation
```

Do not claim a target episode count has been collected.

---

# 7. VLA Service Boundary Readiness

The future VLA component must remain independently integrable with the Agent/ROS system.

Review and confirm the intended service boundary.

Recommended conceptual surface:

```text
/health
/version
/execute
```

or repository-equivalent typed interfaces.

At minimum, document future fields such as:

```text
request_id
action_id
skill
instruction
observation/reference
deadline
status
error
component_version
```

This task does not implement the VLA service.

The purpose is only to ensure the future boundary does not violate the frozen architecture.

---

# 8. Architecture Constraints

The following are mandatory.

## 8.1 Agent Boundary

The Agent must not send:

- raw motor commands;
- joint-level control;
- arbitrary ROS commands;
- shell commands;
- direct actuator commands.

## 8.2 VLA Boundary

VLA may provide an approved manipulation skill.

VLA must not bypass:

- deterministic runtime authorization;
- safety boundary;
- MoveIt planning authority where MoveIt owns the motion;
- `ros2_control` hardware/controller authority.

## 8.3 Runtime Ownership

Deterministic Runtime owns:

- action authorization;
- timeout;
- retry budget;
- reconciliation;
- idempotency;
- business-level recovery.

VLA does not decide ambiguous physical outcomes.

---

# 9. Explicitly Out of Scope

Do NOT implement any of the following in this task:

- Dataset V1 collection;
- 50-episode dataset creation;
- VLA fine-tuning;
- VLA evaluation benchmark;
- Dataset V2;
- failure taxonomy;
- retraining;
- VLA Skill Server implementation;
- ROS 2 execution adapter;
- Nav2;
- MoveIt skill implementation;
- Agent integration;
- WMS/MES/PHM integration;
- real factory workflow;
- Day-10 MVP scope changes;
- second failure scenario;
- production benchmark claims;
- portfolio performance claims.

---

# 10. Required Repository Inspection

Before changing files, inspect at minimum:

```bash
pwd
git branch --show-current
git status
git log --oneline -5
```

Expected branch:

```text
task/p0-004-vla-readiness
```

Read:

```text
AGENTS.md
context/*
plans/next_tasks_after_phase0.md
docs/architecture/system_architecture_v1.md
docs/contracts/contract_plan.md
relevant ADRs
tasks/TASK-P0-004.md
```

Also inspect any existing:

```text
pyproject.toml
requirements*.txt
environment*.yml
Dockerfile*
scripts/
configs/
docs/environment/
results/phase0/
```

Do not assume missing files are errors until repository structure is inspected.

---

# 11. Required Outputs

Create or update the following artifacts.

## O1 — VLA Readiness Report

```text
docs/vla/vla_readiness_v1.md
```

Minimum contents:

```text
Environment
GPU / CUDA
LeRobot
SmolVLA
Manipulator
Camera
Teleoperation
Dataset Pipeline
Service Boundary
Blockers
Deferred Checks
Final Gate
```

## O2 — Machine-readable Evidence

```text
results/phase0/P0-004_vla_readiness.json
```

Minimum structure:

```json
{
  "task": "TASK-P0-004",
  "status": "GO | CONDITIONAL_GO | NO_GO",
  "host": {},
  "python": {},
  "gpu": {},
  "lerobot": {},
  "smolvla": {},
  "robot": {},
  "camera": {},
  "teleoperation": {},
  "dataset_pipeline": {},
  "service_boundary": {},
  "checks": [],
  "blockers": [],
  "deferred_checks": [],
  "next_task_authorized": false
}
```

Only record verified facts.

## O3 — Verification Script

Create:

```text
scripts/verify_vla_readiness.py
```

or, if shell is clearly more appropriate:

```text
scripts/verify_vla_readiness.sh
```

The script should automate only safe, non-destructive checks.

Examples:

- Python/runtime versions;
- package imports;
- PyTorch GPU visibility;
- filesystem paths;
- relevant device visibility;
- camera enumeration where safe;
- package/version checks.

It must not:

- move a physical robot;
- command actuators;
- start training;
- download large models without explicit requirement;
- modify system drivers;
- install privileged packages automatically.

## O4 — Risks / Deferred Validation

Update or create:

```text
plans/vla_readiness_risks.md
```

Record:

```text
risk
impact
current evidence
mitigation
trigger
owner
blocking?
```

## O5 — Next Task Recommendation

Create or update:

```text
plans/next_vla_task_after_p0_004.md
```

It must state one of:

```text
GO
→ authorize TASK-W1-001
```

or:

```text
CONDITIONAL_GO
→ authorize only explicitly listed limited work
```

or:

```text
NO_GO
→ do not start real VLA implementation
```

---

# 12. Recommended Verification Checks

At minimum, implement and execute checks equivalent to the following.

## C1 — Python

```bash
python3 --version
```

## C2 — PyTorch

Example intent:

```python
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.device_count())
```

If CUDA is available, record the actual device name.

## C3 — LeRobot Import

Verify the package/import path required by the repository.

Do not assume a specific installed version without checking.

## C4 — Device Visibility

Inspect expected hardware interfaces safely.

Examples may include:

```text
/dev/video*
/dev/ttyUSB*
/dev/ttyACM*
```

Absence only means:

```text
not exposed in this environment
```

unless additional evidence proves otherwise.

## C5 — Camera

If available, verify one non-destructive frame capture or equivalent device-open test.

Do not begin dataset recording.

## C6 — Disk / Memory

Record sufficient free disk and memory information for upcoming Dataset V1 / fine-tuning work.

Do not invent a required threshold unless it is justified in the report.

---

# 13. Readiness Matrix

The final report must contain a table equivalent to:

| Area | Status | Evidence | Blocking? | Next Action |
|---|---|---|---|---|
| Python | PASS/FAIL/DEFERRED | ... | Yes/No | ... |
| GPU | PASS/FAIL/DEFERRED | ... | Yes/No | ... |
| LeRobot | PASS/FAIL | ... | Yes/No | ... |
| SmolVLA | PASS/FAIL/DEFERRED | ... | Yes/No | ... |
| Robot I/O | PASS/FAIL/DEFERRED | ... | Yes/No | ... |
| Camera | PASS/FAIL/DEFERRED | ... | Yes/No | ... |
| Teleoperation | PASS/FAIL/DEFERRED | ... | Yes/No | ... |
| Dataset Pipeline | PASS/FAIL | ... | Yes/No | ... |
| Service Boundary | PASS/FAIL | ... | Yes/No | ... |

---

# 14. Gate Decision Rules

## GO

Use `GO` only when:

- all blockers for the next VLA implementation task are resolved;
- the next task can start reproducibly;
- any deferred checks are explicitly non-blocking;
- architecture boundaries remain intact.

Set:

```json
"next_task_authorized": true
```

## CONDITIONAL_GO

Use when:

- limited software-side work is possible;
- one or more hardware/native-device checks remain unresolved;
- those limitations are explicitly documented;
- the next task is constrained accordingly.

Example:

```text
software dataset schema work allowed
physical teleoperation not yet authorized
```

`next_task_authorized` must reflect the exact authorized next task, not a generic VLA approval.

## NO_GO

Use when a blocking condition prevents meaningful VLA implementation.

Examples:

- required LeRobot runtime cannot import;
- GPU execution required by next task but unusable;
- required robot/camera interface is unknown and no viable validation path exists;
- architecture/service boundary is unresolved.

---

# 15. Test / Validation Requirements

Run:

```bash
python3 -m compileall -q scripts
```

if a Python verification script is added.

Run the verification script and save its measured output in machine-readable evidence.

Also run:

```bash
git diff --check
```

Before commit, after staging intended task files:

```bash
git diff --cached --check
```

Do not claim `git diff --check` validated untracked files before staging.

---

# 16. Evidence Integrity Rules

Evidence must distinguish:

```text
MEASURED
INFERRED
DEFERRED
NOT AVAILABLE
```

Do not report:

- benchmark success rate;
- training performance;
- dataset episode count;
- VLA improvement;
- production readiness;

unless actually measured in an authorized later task.

Record actual versions and device information only from executed checks.

---

# 17. Exit Criteria

All of the following must be satisfied.

- [ ] working branch is `task/p0-004-vla-readiness`;
- [ ] Agent/MVP source is not modified;
- [ ] VLA runtime readiness is explicitly assessed;
- [ ] LeRobot readiness is verified or blocking reason is documented;
- [ ] SmolVLA prerequisites are assessed;
- [ ] GPU/CUDA status is measured, not assumed;
- [ ] robot interface status is measured or correctly marked deferred;
- [ ] camera status is measured or correctly marked deferred;
- [ ] teleoperation path is documented;
- [ ] Dataset V1 pipeline is documented without collecting Dataset V1;
- [ ] VLA service boundary is architecture-compliant;
- [ ] `docs/vla/vla_readiness_v1.md` exists;
- [ ] `results/phase0/P0-004_vla_readiness.json` exists;
- [ ] verification script exists and runs safely;
- [ ] blockers and deferred checks are explicit;
- [ ] final gate is `GO`, `CONDITIONAL_GO`, or `NO_GO`;
- [ ] next-task authorization is explicit;
- [ ] no VLA fine-tuning or Dataset V1 implementation was started;
- [ ] `git diff --check` passes;
- [ ] no unrelated application files were changed.

---

# 18. Completion Message

If `GO`:

```text
TASK-P0-004 is complete.
VLA Readiness Gate = GO.
TASK-W1-001 implementation is authorized.
Agent/MVP lane remains independent.
```

If `CONDITIONAL_GO`:

```text
TASK-P0-004 is complete.
VLA Readiness Gate = CONDITIONAL_GO.
Only the explicitly documented next work is authorized.
Unresolved hardware/runtime gates remain.
Agent/MVP lane remains independent.
```

If `NO_GO`:

```text
TASK-P0-004 is complete.
VLA Readiness Gate = NO_GO.
Real VLA implementation is NOT authorized.
Blocking conditions are documented.
Agent/MVP lane remains independent.
```

---

# 19. Recommended Commit

If the gate work is complete:

```text
chore(vla): validate VLA runtime and hardware readiness
```

Do not combine `TASK-W1-001` implementation with this commit.

