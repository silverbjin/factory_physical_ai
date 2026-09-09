# TASK-P0-004R — VLA Readiness Re-Gate

## Metadata

* **Task ID:** `TASK-P0-004R`
* **Title:** `VLA Readiness Re-Gate`
* **Task Type:** `Readiness Re-Gate / Evidence Validation`
* **Related Backlog:** `VLA-01`
* **Phase:** `Phase 0 — VLA Readiness`
* **Status:** `READY_FOR_EXECUTION_AFTER_HUMAN_REVIEW`
* **Recommended Branch:** `task/p0-004r-vla-readiness-regate`
* **Recommended Worktree:** `../factory_physical_ai_p0_004r`
* **Primary Purpose:** Re-evaluate the original `TASK-P0-004` `NO_GO` decision using accepted machine-readable evidence from `TASK-P0-005`, `TASK-P0-006`, and `TASK-P0-007`.
* **Feature Implementation:** `PROHIBITED`
* **Week 1 Work:** `PROHIBITED`
* **Commit During Execution:** `PROHIBITED until review/acceptance`

---

## 1. Goal

Re-evaluate the VLA readiness gate originally executed by `TASK-P0-004`.

The task must determine whether the blockers that caused the original `NO_GO` result have been:

* resolved;
* partially resolved;
* deferred to a later bounded stage; or
* left unresolved and blocking.

The result must determine the exact authorization boundary for subsequent VLA work.

This task is **not** intended to make the gate pass.

It is intended to produce the correct gate decision from the available evidence.

A valid result may therefore be:

```text
GO
CONDITIONAL_GO
NO_GO
```

A `NO_GO` result is a successful completion of this task when it is correctly supported by evidence.

---

## 2. Why This Task Exists

`TASK-P0-004` completed the original VLA readiness assessment with:

```text
final gate = NO_GO
TASK-W1-001 authorized = false
```

The original gate identified blocking deficiencies in:

* GPU / CUDA execution;
* LeRobot runtime;
* SmolVLA runtime prerequisites;
* Robot / Manipulator I/O;
* Camera I/O;
* Teleoperation / safety prerequisites;
* Training resource / budget readiness.

Corrective readiness tasks were subsequently executed:

```text
TASK-P0-005
→ VLA software runtime / CUDA / LeRobot / SmolVLA readiness

TASK-P0-006
→ Robot / Camera / Device-I/O readiness

TASK-P0-007
→ Training compute / resource / budget readiness
```

`TASK-P0-004R` must now aggregate those results without introducing new implementation and issue a new bounded readiness decision.

---

# 3. Context Budget Contract

This task is a **self-contained work order**.

Codex must not reconstruct the full project history before performing this task.

The task itself contains:

* original gate areas;
* blocker traceability;
* stage-specific authorization rules;
* final decision rules;
* validation requirements.

Read only the explicitly listed `Required Context`.

---

## 4. Required Context

Read only:

```text
results/phase0/P0-004_vla_readiness.json
results/phase0/P0-005_vla_runtime.json
results/phase0/P0-006_robot_io_readiness.json
results/phase0/P0-007_training_resource_readiness.json
```

Also read:

```text
AGENTS.md
tasks/TASK-P0-004R.md
```

No other file is required by default.

### Conditional Context

Read an additional Architecture / ADR / Contract file only when:

1. a concrete gate claim cannot be resolved from this Task and the four evidence files;
2. the exact missing fact is identified first;
3. the exact file expected to contain that fact is identified.

Do not expand context speculatively.

---

## 5. Context Explicitly Not Required

Do **not** recursively read:

```text
context/*
plans/*
docs/*
tasks/*
```

Do not read by default:

* previous MVP Task specifications;
* Day-10 implementation history;
* portfolio documents;
* Week 2–6 plans;
* Agent implementation history;
* unrelated ROS / integration implementation;
* full Git history;
* the project-management workbook;
* unrelated architecture documents;
* `TASK-CONTEXT-TEMPLATE.md`;
* `context/project_management_context.md`;
* `context/task_mapping.md`;
* `context/current_project_state.md`;
* `context/session_handoff.md`.

Those documents were used during Task authoring and are not part of the normal P0-004R execution context.

---

# 6. Inputs / Accepted Evidence

## 6.1 Original Gate — TASK-P0-004

Evidence:

```text
results/phase0/P0-004_vla_readiness.json
```

Original decision:

```text
NO_GO
```

Original gate areas:

| Original Check | Area             | Original State | Original Blocking |
| -------------- | ---------------- | -------------: | ----------------: |
| C1             | Python           |           PASS |                No |
| C2             | GPU              |           FAIL |               Yes |
| C3             | LeRobot          |           FAIL |               Yes |
| C4             | SmolVLA          |           FAIL |               Yes |
| C5             | Robot I/O        |       DEFERRED |               Yes |
| C6             | Camera           |       DEFERRED |               Yes |
| C7             | Teleoperation    |       DEFERRED |               Yes |
| C8             | Dataset Pipeline |           PASS |                No |
| C9             | Service Boundary |           PASS |                No |
| C10            | Training Budget  |           FAIL |               Yes |

P0-004 must remain immutable historical evidence.

Do not rewrite it to reflect later improvements.

---

## 6.2 Runtime Corrective Evidence — TASK-P0-005

Evidence:

```text
results/phase0/P0-005_vla_runtime.json
```

Expected task identity:

```text
task = TASK-P0-005
```

Expected runtime decision from accepted evidence:

```text
runtime_decision = RUNTIME_READY
```

Key accepted facts include:

```text
isolated Python environment      PASS
uv environment management        PASS
NVIDIA GPU visibility            PASS
PyTorch CUDA                     PASS
actual CUDA tensor operation     PASS
LeRobot runtime/import           PASS
SmolVLA module/config discovery  PASS
runtime_blockers                 []
```

The accepted evidence classifies the local machine approximately as:

```text
CUDA runtime + SmolVLA code/config ready
model loading not verified
local inference not verified
local fine-tuning not verified
6 GB SmolVLA training fit not verified
```

Therefore:

```text
Runtime readiness
≠
Training readiness
```

P0-005 does not authorize Week 1 by itself.

---

## 6.3 Device-I/O Corrective Evidence — TASK-P0-006

Evidence:

```text
results/phase0/P0-006_robot_io_readiness.json
```

Expected task identity:

```text
task = TASK-P0-006
```

Expected decision from accepted evidence:

```text
device_io_decision = DEVICE_IO_BLOCKED
```

Expected authorization state:

```text
task_w1_001_authorized = false
task_w1_002_authorized = false
p0_004r_required = true
```

Known unresolved areas include:

```text
target hardware selection
robot/controller discovery
stable device identity
host permission/access
state-feedback path
safe state observation
future actuator command path
gripper path
camera selection
camera discovery
bounded frame acquisition
camera configuration
workspace/motion limits
manual abort/E-stop
teleoperation prerequisites
```

P0-006 also confirms that no physical motion, teleoperation, Dataset V1 work, or model work was executed by the readiness verifier.

---

## 6.4 Training Resource Corrective Evidence — TASK-P0-007

Evidence:

```text
results/phase0/P0-007_training_resource_readiness.json
```

Expected task identity:

```text
task = TASK-P0-007
```

Expected decision from accepted evidence:

```text
training_resource_decision = TRAINING_RESOURCE_BLOCKED
```

Known unresolved areas include:

```text
training execution mode
primary training resource
primary-path compatibility
storage capacity/readiness
budget policy
budget feasibility
fallback compute
model-specific training fit
```

Accepted evidence preserves the P0-005 runtime baseline and confirms no actual training, optimizer update, Dataset V1 implementation, or paid compute provisioning occurred.

Training-resource readiness must be evaluated separately from the minimum authorization required to begin `TASK-W1-001`.

---

# 7. Evidence Integrity Requirements

Before making a Re-Gate decision:

1. all four JSON files must exist;
2. all four must parse as valid JSON;
3. their `task` identifiers must match their filenames/task roles;
4. their decision fields must be extracted from the evidence itself;
5. unresolved blockers must be read from the evidence rather than inferred from Task completion;
6. evidence provenance/hash information must be preserved when present;
7. no original evidence file may be modified.

Known predecessor integrity bindings should be checked when present.

At minimum, accepted evidence currently establishes the following predecessor hashes:

```text
P0-005 evidence SHA-256
aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae

P0-006 evidence SHA-256
486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506
```

If the repository copy differs from a predecessor-bound expected hash:

```text
Evidence integrity = FAIL
Final Gate = NO_GO
```

unless the difference is explained by an explicitly accepted later evidence revision.

Do not silently substitute a different artifact.

---

# 8. Gate Traceability

The Re-Gate must produce traceability in this form:

```text
Original P0-004 Check
→ Corrective Task
→ Corrective Evidence
→ P0-004R Check
→ PASS / FAIL / DEFERRED
```

Use the following minimum mapping.

| P0-004 Area                | Original | Corrective Source       | P0-004R Interpretation Rule                                                                                           |
| -------------------------- | -------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Python                     | PASS     | P0-005                  | PASS only if isolated runtime remains evidenced                                                                       |
| GPU / CUDA                 | FAIL     | P0-005                  | PASS only if PyTorch CUDA and real CUDA tensor execution are evidenced                                                |
| LeRobot                    | FAIL     | P0-005                  | PASS only if selected/pinned LeRobot runtime and required imports are evidenced                                       |
| SmolVLA                    | FAIL     | P0-005                  | PASS for **runtime prerequisite** only if module/config discovery succeeds; model inference/training remains separate |
| Robot I/O                  | DEFERRED | P0-006                  | FAIL while mandatory device-I/O prerequisites remain BLOCKED/NOT_VERIFIED                                             |
| Camera                     | DEFERRED | P0-006                  | FAIL while camera identity/access/bounded acquisition remain BLOCKED/NOT_VERIFIED                                     |
| Teleoperation / Safety     | DEFERRED | P0-006                  | FAIL for teleoperation authorization while mandatory safety/teleoperation prerequisites remain BLOCKED                |
| Dataset Pipeline           | PASS     | P0-004 + later evidence | PASS as design readiness unless later evidence contradicts it; Dataset V1 must remain uncollected                     |
| Service Boundary           | PASS     | P0-004 + later evidence | PASS as architecture readiness unless later evidence contradicts it; no Skill Server implementation required          |
| Training Resource / Budget | FAIL     | P0-007                  | FAIL while training execution/resource/budget/fallback readiness remains BLOCKED                                      |

Task completion itself is never evidence of blocker resolution.

---

# 9. Re-Gate Status Vocabulary

Each Re-Gate check must return exactly one of:

```text
PASS
FAIL
DEFERRED
```

Interpretation:

### PASS

The required condition is supported by accepted evidence at the scope required by the authorization being evaluated.

### FAIL

A mandatory prerequisite for the authorization being evaluated is:

```text
BLOCKED
FAIL
NOT_VERIFIED
missing
inconsistent
```

and cannot be safely ignored.

### DEFERRED

The item is not required for the currently considered authorization boundary and is explicitly assigned to a later Task/stage.

`DEFERRED` must never be used to hide a blocker that is mandatory for the authorization being granted.

---

# 10. Stage-Specific Readiness Model

P0-004R must not collapse all VLA work into one Boolean.

Evaluate the following stages separately.

---

## 10.1 Runtime Readiness

Minimum requirements:

```text
isolated Python runtime
PyTorch CUDA available
actual CUDA tensor execution
LeRobot runtime/import
SmolVLA code/config discovery
```

This stage may be:

```text
READY
BLOCKED
```

Model weight loading, inference performance, and training fit are not required for this runtime-only stage unless a later authorization explicitly requires them.

---

## 10.2 TASK-W1-001 Readiness

`TASK-W1-001` is the primary VLA environment / hardware-I/O implementation stage.

Before authorizing it, P0-004R must confirm that the prerequisites intentionally moved into Phase-0 readiness have been satisfied.

Minimum hard blockers include, at least:

```text
runtime readiness
target hardware selected
robot/controller discoverable
stable hardware identity
required host access
credible state-feedback path
future command path identified
gripper path identified or explicitly N/A
camera selected where required by W1-001
camera discoverability/access where required
bounded safe camera acquisition where required
workspace/motion constraints documented before physical motion
manual abort/E-stop strategy documented before physical motion
```

The Re-Gate must respect P0-006 mandatory checks.

If P0-006 remains:

```text
device_io_decision = DEVICE_IO_BLOCKED
```

and mandatory W1-001 prerequisites remain unresolved:

```text
TASK-W1-001 authorized = false
```

Do not reinterpret missing physical prerequisites as implementation work merely to force authorization.

---

## 10.3 TASK-W1-002 / Teleoperation Readiness

Teleoperation implementation itself belongs to the later task, but its safety prerequisites must be explicitly classified.

Authorization requires at minimum:

```text
required device-I/O prerequisites ready
workspace/motion boundaries documented
manual abort/E-stop path documented
supervised teleoperation prerequisites no longer BLOCKED
```

If those conditions are not satisfied:

```text
TASK-W1-002 authorized = false
Physical motion authorized = false
```

---

## 10.4 Dataset V1 Readiness

Dataset collection must remain unauthorized unless the prerequisites for safe and valid collection are satisfied.

Minimum expected prerequisites include:

```text
authorized teleoperation path
robot state observation path
camera acquisition path
timestamped/synchronized observation/action design
safe operator/abort boundary
```

P0-004's Dataset Pipeline design PASS alone does not authorize Dataset V1 collection.

---

## 10.5 SmolVLA Fine-Tuning Readiness

Fine-tuning authorization requires more than runtime readiness.

Minimum expected prerequisites include:

```text
Dataset V1 available and validated
training execution mode selected
training resource identified
runtime compatibility verified for selected resource
storage strategy/capacity verified
budget policy resolved
budget feasibility classified
fallback/stop/escalation strategy defined
```

While P0-007 remains:

```text
training_resource_decision = TRAINING_RESOURCE_BLOCKED
```

then:

```text
SmolVLA fine-tuning authorized = false
```

This condition does **not**, by itself, prove that `TASK-W1-001` must remain blocked.

---

# 11. Authorization Matrix

The machine-readable result must explicitly contain authorization decisions.

Minimum authorization object:

```text
TASK-W1-001 authorized
TASK-W1-002 authorized
Dataset V1 authorized
SmolVLA fine-tuning authorized
Physical motion authorized
```

Use explicit Boolean values.

Do not emit ambiguous statements such as:

```text
VLA work authorized
VLA generally ready
Hardware mostly ready
```

Every authorization must be traceable to specific gate checks.

---

# 12. Predecessor Authorization Interpretation

P0-005, P0-006, and P0-007 may contain conservative fields such as:

```text
task_w1_001_authorized = false
p0_004r_required = true
```

These fields mean the predecessor Task did not grant final Phase-0 authorization.

`TASK-P0-004R` is the dedicated task responsible for producing the final bounded Re-Gate authorization.

However:

* P0-004R must not ignore unresolved blocker evidence;
* P0-004R may distinguish blockers by the stage they actually protect;
* training-specific blockers must not automatically be converted into W1-001 blockers unless W1-001 actually depends on them;
* device/safety blockers documented as mandatory for W1-001 must remain blocking.

---

# 13. Final Gate Decision

The top-level Re-Gate must return exactly one:

```text
GO
CONDITIONAL_GO
NO_GO
```

No other final value is allowed.

---

## 13.1 GO

Return `GO` only when:

1. all original blockers have either:

   * been resolved; or
   * been legitimately reclassified as non-blocking for all immediately authorized VLA stages;
2. `TASK-W1-001` is authorized;
3. no unresolved blocker contradicts the scope represented by `GO`;
4. the authorization matrix is internally consistent.

A `GO` does not automatically authorize every future VLA task unless the authorization matrix explicitly says so.

---

## 13.2 CONDITIONAL_GO

Return `CONDITIONAL_GO` when:

1. `TASK-W1-001` hard blockers are resolved;
2. `TASK-W1-001` can safely and reproducibly begin;
3. one or more later-stage blockers remain;
4. those blockers are explicitly mapped to prohibited later activities.

Example only:

```text
TASK-W1-001 authorized       = true
TASK-W1-002 authorized       = false
Dataset V1 authorized        = false
SmolVLA fine-tuning          = false
Physical motion              = false
```

A `CONDITIONAL_GO` must list:

* exactly what is authorized;
* exactly what remains prohibited;
* every remaining blocker;
* the later stage protected by each blocker.

If `TASK-W1-001` itself remains blocked:

```text
CONDITIONAL_GO is not allowed.
```

---

## 13.3 NO_GO

Return `NO_GO` when any hard prerequisite for `TASK-W1-001` remains:

```text
FAIL
BLOCKED
NOT_VERIFIED
missing
evidence-inconsistent
```

or evidence integrity is insufficient to grant authorization.

Expected behavior:

```text
TASK-W1-001 authorized = false
```

A `NO_GO` result must still identify any blockers that were successfully resolved.

Do not collapse all checks to failure merely because the final gate is `NO_GO`.

---

# 14. Current Evidence Baseline for Re-Gate

The current accepted evidence should cause the Re-Gate implementation to verify, not blindly copy, the following baseline:

```text
P0-005:
runtime_decision = RUNTIME_READY

P0-006:
device_io_decision = DEVICE_IO_BLOCKED

P0-007:
training_resource_decision = TRAINING_RESOURCE_BLOCKED
```

Therefore the expected trace direction before execution is:

```text
Runtime blockers
→ likely resolved

Device / Camera / physical prerequisite blockers
→ currently unresolved

Training resource blockers
→ currently unresolved
```

This is **not** a pre-authorized final gate result.

The Re-Gate implementation must derive the final result from the evidence and the rules in this Task.

Do not force `GO`, `CONDITIONAL_GO`, or `NO_GO` merely to match this expectation.

---

# 15. Scope

P0-004R may:

1. read and validate the four required Evidence files;
2. compare original P0-004 blockers against corrective evidence;
3. classify checks as `PASS / FAIL / DEFERRED`;
4. produce the authorization matrix;
5. produce the final gate;
6. create the required Re-Gate report;
7. create machine-readable Re-Gate evidence;
8. reuse an existing non-mutating verifier if its exact invocation is already established;
9. add a minimal evidence-aggregation/verifier script only if required for reproducibility.

---

# 16. Explicit Out-of-Scope

P0-004R must **not**:

* install or upgrade Python;
* create a new runtime;
* install or upgrade NVIDIA drivers;
* install or upgrade CUDA;
* install or upgrade PyTorch;
* upgrade LeRobot;
* download VLA model weights for a new capability test;
* implement a robot adapter;
* implement a camera adapter;
* select or procure new hardware;
* change device permissions/security policy;
* implement teleoperation;
* command robot movement;
* command gripper movement;
* execute trajectories;
* collect Dataset V1;
* execute model fine-tuning;
* run optimizer updates;
* perform a VLA benchmark;
* implement VLA Skill Server;
* implement ROS integration;
* implement Agent integration;
* refactor Architecture;
* create a new readiness-remediation Task;
* start `TASK-W1-001`;
* start `TASK-W1-002`;
* provision paid compute;
* create billing credentials;
* modify existing P0-004/P0-005/P0-006/P0-007 evidence.

If a new blocker is discovered:

```text
record it
classify it
mark it UNRESOLVED / BLOCKING where applicable
stop remediation
```

Do not solve it inside P0-004R.

---

# 17. Architecture Constraints

The Re-Gate must preserve the existing architecture boundaries.

At minimum:

1. VLA owns bounded manipulation policy behavior, not unrestricted physical control.
2. Deterministic runtime retains authorization and execution-policy responsibilities.
3. Physical success/failure must not be inferred from an LLM.
4. MoveIt / ros2_control remain owners of validated motion/controller boundaries where applicable.
5. Evidence from WSL must not be generalized into unsupported physical-device claims.
6. Runtime readiness must not be generalized into training readiness.
7. Code/config discovery must not be generalized into model inference or fine-tuning readiness.
8. No evidence-free benchmark or capability claim may be introduced.

If an architecture interpretation is genuinely required and not contained in this Task:

```text
identify exact missing fact
→ identify exact ADR/Contract
→ read that file only
```

---

# 18. Required Outputs

The minimum required outputs are:

```text
docs/vla/vla_readiness_regate_v1.md
results/phase0/P0-004R_vla_readiness.json
```

Optional, only when necessary:

```text
scripts/verify_vla_readiness_regate.py
tests/test_verify_vla_readiness_regate.py
```

Do not create the optional verifier/test merely for ceremony.

Prefer reuse of safe existing validation logic when possible.

Any verifier used by P0-004R must:

* be non-motion;
* not install packages;
* not change drivers;
* not modify device/security permissions;
* not collect a dataset;
* not download/train a model;
* not provision external compute;
* not remediate failed readiness checks.

---

# 19. Required Report Content

`docs/vla/vla_readiness_regate_v1.md` must include at minimum:

1. Task identity
2. Re-Gate purpose
3. Evidence inputs and hashes
4. Original P0-004 decision
5. Corrective-task decisions
6. Original blocker → corrective evidence traceability
7. Re-Gate check matrix
8. Resolved blockers
9. Remaining blockers
10. Deferred checks
11. Stage-specific readiness
12. Authorization matrix
13. Final Gate
14. Explicit prohibitions after the gate
15. Evidence limitations
16. No-new-implementation confirmation

The report must distinguish:

```text
MEASURED
DOCUMENTED
DERIVED / INFERRED
DEFERRED
NOT_VERIFIED
```

according to the evidence sources.

---

# 20. Machine-Readable Evidence

Create:

```text
results/phase0/P0-004R_vla_readiness.json
```

The exact schema may follow existing project evidence conventions, but it must express at least:

```text
schema_version
task
generated_at

original_gate

evidence_inputs
  P0-004
  P0-005
  P0-006
  P0-007

corrective_tasks

checks

resolved_blockers
remaining_blockers
deferred_checks

stage_readiness
  runtime
  device_io
  teleoperation
  dataset
  training

authorization
  task_w1_001
  task_w1_002
  dataset_v1
  smolvla_fine_tuning
  physical_motion

final_gate

scope_safety
content_binding
git
```

---

## 20.1 Original Gate Object

Must identify:

```text
task = TASK-P0-004
decision = NO_GO
evidence path
evidence SHA-256
```

---

## 20.2 Corrective Task Objects

For each:

```text
TASK-P0-005
TASK-P0-006
TASK-P0-007
```

record:

* evidence path;
* evidence SHA-256;
* decision field/value;
* whether the evidence is accepted for Re-Gate use.

---

## 20.3 Checks

Each check should contain enough information to establish:

```text
id
area
original_status
corrective_task
corrective_evidence
regate_status
blocking_for
provenance
detail
```

`blocking_for` may identify one or more stages such as:

```text
TASK-W1-001
TASK-W1-002
Dataset V1
Fine-tuning
Physical motion
```

---

## 20.4 Authorization

Authorization must use explicit Booleans.

Example schema shape:

```text
authorization:
  task_w1_001: true/false
  task_w1_002: true/false
  dataset_v1: true/false
  smolvla_fine_tuning: true/false
  physical_motion: true/false
```

Each authorization should have a reason or supporting check reference.

---

## 20.5 Final Gate

Must contain exactly one of:

```text
GO
CONDITIONAL_GO
NO_GO
```

The final gate must be algorithmically consistent with the authorization matrix and remaining blockers.

---

# 21. Evidence Rules

1. Use machine-readable predecessor Evidence as the primary factual source.
2. Task completion or merge status is not proof of readiness.
3. A `PASS` must be traceable to evidence.
4. A `FAIL` must identify the blocking fact.
5. A `DEFERRED` must identify why it is not blocking the currently considered authorization.
6. Do not convert `NOT_VERIFIED` into PASS.
7. Do not infer physical availability from planned hardware declarations.
8. Do not infer training capacity from working CUDA.
9. Do not infer fine-tuning readiness from SmolVLA import/config success.
10. Preserve original evidence files unchanged.
11. Record hashes for all four input Evidence files.
12. Do not fabricate benchmark, inference, training, latency, or success-rate results.

---

# 22. Required Validation Commands

Run from the P0-004R worktree root.

## 22.1 Precondition

```bash
pwd
git branch --show-current
git status --short
```

Expected branch:

```text
task/p0-004r-vla-readiness-regate
```

Before execution, verify that the branch is based on the intended current `master` containing the accepted P0-005/P0-006/P0-007 evidence.

Do not reconstruct full Git history.

A concise check is sufficient:

```bash
git merge-base HEAD master
git rev-parse master
```

If remote state matters:

```bash
git fetch origin
git rev-parse origin/master
```

---

## 22.2 Required Input Existence

```bash
test -f results/phase0/P0-004_vla_readiness.json
test -f results/phase0/P0-005_vla_runtime.json
test -f results/phase0/P0-006_robot_io_readiness.json
test -f results/phase0/P0-007_training_resource_readiness.json
```

All must return success.

---

## 22.3 JSON Syntax Validation

```bash
python3 -m json.tool \
  results/phase0/P0-004_vla_readiness.json \
  >/dev/null

python3 -m json.tool \
  results/phase0/P0-005_vla_runtime.json \
  >/dev/null

python3 -m json.tool \
  results/phase0/P0-006_robot_io_readiness.json \
  >/dev/null

python3 -m json.tool \
  results/phase0/P0-007_training_resource_readiness.json \
  >/dev/null
```

After P0-004R evidence is generated:

```bash
python3 -m json.tool \
  results/phase0/P0-004R_vla_readiness.json \
  >/dev/null
```

---

## 22.4 Evidence Hashes

```bash
sha256sum \
  results/phase0/P0-004_vla_readiness.json \
  results/phase0/P0-005_vla_runtime.json \
  results/phase0/P0-006_robot_io_readiness.json \
  results/phase0/P0-007_training_resource_readiness.json
```

Record these hashes in P0-004R evidence/report.

Where predecessor evidence contains an expected SHA-256, verify it matches the current artifact.

Known bindings that should be checked include:

```text
P0-005:
aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae

P0-006:
486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506
```

A mismatch must not be ignored.

---

## 22.5 Evidence Decision Validation

Use the repository's available JSON inspection mechanism.

The implementation must verify at minimum:

```text
P0-004:
task = TASK-P0-004
status = NO_GO

P0-005:
task = TASK-P0-005
runtime_decision = RUNTIME_READY

P0-006:
task = TASK-P0-006
device_io_decision = DEVICE_IO_BLOCKED

P0-007:
task = TASK-P0-007
training_resource_decision = TRAINING_RESOURCE_BLOCKED
```

The exact command may use Python or an already-available JSON tool.

Do not install a new tool only for this check.

---

## 22.6 Existing Verifier Reuse

The following verifier paths are known from predecessor evidence or project convention:

```text
scripts/verify_vla_runtime.py
scripts/verify_robot_io_readiness.py
scripts/verify_training_resource_readiness.py
```

Do **not** automatically rerun them.

Before reuse, verify:

1. the verifier is non-mutating;
2. its exact invocation is known;
3. rerunning it will not alter the accepted predecessor evidence;
4. it does not execute physical motion/training/download/provisioning.

If any exact invocation is not already established:

```text
VERIFY EXACT COMMAND BEFORE EXECUTION
```

Do not guess an invocation.

P0-004R may validate the accepted evidence without rerunning predecessor environmental probes.

---

## 22.7 Optional P0-004R Verifier

If a dedicated P0-004R verifier is created, run its exact focused test command as defined by that implementation.

Until such a verifier exists:

```text
VERIFY EXACT COMMAND BEFORE EXECUTION
```

Do not invent a pytest path or test count in this Task specification.

---

## 22.8 Final Diff Validation

```bash
git diff --check
git status --short
```

If files are staged later during the commit phase:

```bash
git diff --cached --check
```

---

# 23. Exit Criteria

P0-004R is complete only when all of the following are satisfied.

### Evidence Integrity

* [ ] All four predecessor Evidence files exist.
* [ ] All four predecessor Evidence files parse successfully.
* [ ] Task IDs match expected predecessor tasks.
* [ ] Predecessor decision fields are extracted and verified.
* [ ] Available predecessor hash bindings are verified.
* [ ] Input evidence SHA-256 values are recorded.
* [ ] Original evidence files remain unchanged.

### Traceability

* [ ] Every original P0-004 blocker is mapped to a corrective Task.
* [ ] Every original P0-004 blocker has a Re-Gate result.
* [ ] Runtime, Device I/O, Camera, Teleoperation/Safety, and Training blockers are not conflated.
* [ ] P0-004 non-blocking PASS areas are explicitly carried forward or reclassified with evidence.
* [ ] Each Re-Gate check is exactly `PASS`, `FAIL`, or `DEFERRED`.

### Stage Readiness

* [ ] Runtime readiness is explicitly classified.
* [ ] W1-001 readiness is explicitly classified.
* [ ] W1-002/teleoperation readiness is explicitly classified.
* [ ] Dataset V1 readiness is explicitly classified.
* [ ] Fine-tuning readiness is explicitly classified.
* [ ] Physical-motion readiness is explicitly classified.

### Authorization

* [ ] `TASK-W1-001 authorized` is explicit Boolean.
* [ ] `TASK-W1-002 authorized` is explicit Boolean.
* [ ] `Dataset V1 authorized` is explicit Boolean.
* [ ] `SmolVLA fine-tuning authorized` is explicit Boolean.
* [ ] `Physical motion authorized` is explicit Boolean.
* [ ] Every `true` authorization is supported by PASS evidence.
* [ ] No `false` authorization is hidden by generic `GO` wording.

### Final Gate

* [ ] Exactly one final gate exists.
* [ ] Final gate is one of `GO`, `CONDITIONAL_GO`, `NO_GO`.
* [ ] `CONDITIONAL_GO` is used only if W1-001 is actually authorized.
* [ ] A W1-001 hard blocker forces `NO_GO`.
* [ ] Remaining blockers are explicitly listed.
* [ ] Resolved blockers are explicitly listed.
* [ ] Deferred checks identify their protected later stage.

### Outputs

* [ ] `docs/vla/vla_readiness_regate_v1.md` exists.
* [ ] `results/phase0/P0-004R_vla_readiness.json` exists.
* [ ] P0-004R JSON parses successfully.
* [ ] Report and JSON agree on authorization and final gate.
* [ ] No unsupported benchmark/performance claims exist.

### Scope Safety

* [ ] No new runtime was installed.
* [ ] No driver/CUDA/LeRobot upgrade occurred.
* [ ] No robot/camera adapter implementation occurred.
* [ ] No physical motion occurred.
* [ ] No teleoperation implementation occurred.
* [ ] No Dataset V1 collection occurred.
* [ ] No model loading/training requirement was added merely to force the gate.
* [ ] No fine-tuning occurred.
* [ ] No external paid compute was provisioned.
* [ ] No Week 1 Task was started.
* [ ] No new remediation Task was automatically created.
* [ ] No unrelated application source was modified.

### Repository Validation

* [ ] Required validation commands pass.
* [ ] `git diff --check` passes.
* [ ] Only task-related files changed.

---

# 24. Review Scope

This is a bounded Re-Gate review.

Reviewer should inspect only:

```text
tasks/TASK-P0-004R.md

git diff <merge-base>...HEAD

docs/vla/vla_readiness_regate_v1.md
results/phase0/P0-004R_vla_readiness.json

results/phase0/P0-004_vla_readiness.json
results/phase0/P0-005_vla_runtime.json
results/phase0/P0-006_robot_io_readiness.json
results/phase0/P0-007_training_resource_readiness.json

task-related validation output
```

Read an Architecture / ADR / Contract only when a specific Re-Gate claim cannot otherwise be verified.

Do not perform:

```text
project-wide review
full repository rediscovery
previous Task history review
portfolio review
Week 2+ planning review
```

### Review Categories

Use:

```text
BLOCKER
HIGH
MEDIUM
LOW
NOTE
```

Final review recommendation:

```text
ACCEPT
FIX REQUIRED
```

A correctly supported `NO_GO` is eligible for `ACCEPT`.

Review the **correctness of the gate**, not whether the gate produced the desired business outcome.

---

# 25. Fix / Re-Review Rule

If review returns findings:

1. fix only cited findings;
2. do not reopen full project discovery;
3. inspect only affected files;
4. rerun affected validation plus mandatory final checks.

Re-review only:

```text
previous findings
delta since reviewed revision
affected evidence
affected validation
```

Do not automatically perform another full Re-Gate review unless the fix changes:

* gate logic;
* authorization semantics;
* evidence source;
* architecture/contract boundary.

---

# 26. Context Expansion Rule

If additional context becomes necessary:

1. state the exact missing fact;
2. identify the exact file expected to contain it;
3. read that file only;
4. record why expansion was necessary.

Do not recursively search:

```text
context/
docs/
plans/
tasks/
```

Do not browse unrelated repository history to reconstruct project background.

If the missing fact cannot be resolved from a bounded source:

```text
classify the related check as NOT_VERIFIED / FAIL as appropriate
```

rather than expanding indefinitely.

---

# 27. Project State Update

Do **not** update project-state context as part of the initial Re-Gate implementation unless explicitly required by the Task outputs.

After P0-004R has:

```text
completed
→ passed review
→ been committed
→ been merged
```

update:

```text
context/current_project_state.md
context/session_handoff.md
```

Update:

```text
context/task_mapping.md
```

only when the final Re-Gate decision changes:

* authorization;
* dependency;
* next executable Task mapping.

Do not modify:

```text
context/project_management_context.md
```

unless a project-management rule itself changed.

---

# 28. Workbook Update Rule

Do not edit the Excel project-management workbook during P0-004R execution.

P0-004R is a Gate / Milestone synchronization point.

After P0-004R is:

```text
reviewed
committed
merged
```

perform a separate workbook reconciliation using:

```text
merged Git state
P0-004R Evidence
current_project_state.md
task_mapping.md
risk/dependency changes
```

The workbook update must reflect the actual final gate rather than a planned outcome.

---

# 29. Recommended Git Workflow

After this Task specification has been human-reviewed, create:

```text
branch:
task/p0-004r-vla-readiness-regate

worktree:
../factory_physical_ai_p0_004r
```

Recommended creation sequence:

```bash
cd ~/projects/factory_physical_ai

git switch master
git pull --ff-only origin master
git status

git worktree add \
  ../factory_physical_ai_p0_004r \
  -b task/p0-004r-vla-readiness-regate \
  master
```

Do not create the branch until the Task specification is approved for execution.

---

# 30. Recommended Commit Message

Choose a decision-specific commit message after the gate result is known.

### If GO

```text
chore(vla): record GO VLA readiness re-gate
```

### If CONDITIONAL_GO

```text
chore(vla): record conditional VLA readiness re-gate
```

### If NO_GO

```text
chore(vla): record no-go VLA readiness re-gate
```

Do not choose the commit message before the final evidence-based decision exists.

---

# 31. Codex Execution Prompt

```text
Execute TASK-P0-004R only.

First verify:
- pwd
- git branch --show-current
- git status

Read:
1. AGENTS.md
2. tasks/TASK-P0-004R.md
3. only the Required Context listed in the Task

Do not recursively rediscover project context.

This is an evidence-based readiness re-gate,
not a feature implementation task.

Do not remediate failed readiness checks.
Do not start Week 1 work.
Do not perform physical motion, dataset work, or training.
Do not commit.

Validate the predecessor evidence,
produce the required Re-Gate report and machine-readable evidence,
and run the exact Validation Commands defined by the Task.

Stop after reporting:
- evidence integrity
- Exit Criteria
- resolved blockers
- remaining blockers
- deferred checks
- authorization matrix
- final Gate decision
```

---

# 32. Stop Condition

After producing:

```text
docs/vla/vla_readiness_regate_v1.md
results/phase0/P0-004R_vla_readiness.json
```

and completing the required validation:

```text
STOP
```

Do not:

```text
fix blockers
create another P0 Task
start TASK-W1-001
start TASK-W1-002
collect Dataset V1
fine-tune SmolVLA
commit automatically
```

Wait for independent review and the next explicit instruction.
