# TASK-P0-006 — Robot / Camera / Device I/O Readiness

> Phase: Phase 0 — Readiness Blocker Resolution
> Type: Implementation Task Specification / Readiness Verification
> Status: READY_FOR_IMPLEMENTATION
> Predecessor: `TASK-P0-005` — ACCEPTED
> Downstream Gate: `TASK-P0-004R`
> Week 1 Authorization: NOT GRANTED BY THIS TASK

---

# 1. Purpose

Resolve the remaining **physical device and I/O readiness blockers** identified by the Phase 0 VLA readiness assessment without implementing Week 1 robot behavior.

This task shall establish reproducible evidence that the project has a usable and sufficiently understood physical I/O foundation for subsequent VLA/robot integration work.

The task answers:

> "Are the target robot/manipulator, camera, device interfaces, state paths, safety boundaries, and future teleoperation prerequisites sufficiently identified and accessible to allow the project to proceed to the final Phase 0 re-gate?"

This task does **not** answer:

> "Can the robot already execute VLA actions?"

and does **not** implement physical robot behavior.

---

# 2. Background

`TASK-P0-004` produced a VLA readiness decision of `NO_GO`.

`TASK-P0-005` resolved the software runtime portion and was independently accepted with:

```text
VLA Runtime = RUNTIME_READY
```

Remaining Phase 0 physical-readiness concerns include:

* manipulator / robot target identity;
* robot USB / serial / device I/O;
* camera identity and frame I/O;
* robot state-feedback path;
* gripper/control-path discovery;
* workspace and motion-limit definition;
* manual abort / emergency-stop readiness;
* supervised teleoperation prerequisites.

Training-resource and budget readiness are outside this task and shall be handled separately by `TASK-P0-007`.

---

# 3. Preconditions

Before implementation begins:

1. `TASK-P0-005` must be independently accepted.
2. The `TASK-P0-005` accepted runtime evidence must remain unchanged.
3. `TASK-W1-001` remains unauthorized.
4. No Week 1 task may be started as part of this task.
5. No physical robot motion is authorized by this task.
6. No model loading, VLA inference, training, dataset generation, or Agent integration is authorized.

If an expected physical device is unavailable, the verifier shall report that fact rather than substituting simulated or inferred evidence.

---

# 4. Primary Decision

The task shall produce exactly one top-level physical I/O readiness decision:

```text
DEVICE_IO_READY
```

or

```text
DEVICE_IO_BLOCKED
```

`DEVICE_IO_READY` means:

> The required physical devices and their relevant non-motion I/O paths have been identified, observed, and documented sufficiently for the final Phase 0 re-gate.

It does **not** mean:

* robot motion has been validated;
* teleoperation works;
* VLA inference works;
* VLA actions can control the robot;
* the camera-to-VLA pipeline works;
* dataset collection works;
* the system is production-safe.

Any unresolved mandatory physical-readiness requirement shall result in `DEVICE_IO_BLOCKED`.

---

# 5. Scope

## 5.1 In Scope

### A. Target Robot / Manipulator Identity

Establish and record the intended physical target for the project.

Record, where available:

* manufacturer;
* model;
* controller / compute unit;
* firmware or software version if observable;
* connection type;
* device identifiers;
* relevant official/project documentation references.

Do not silently substitute another robot or manipulator.

If final target selection remains unresolved, classify the task as blocked.

---

### B. Robot Device Discovery

Perform bounded, non-destructive discovery of robot-side interfaces.

Examples may include:

* USB enumeration;
* serial-device enumeration;
* `/dev/serial/by-id`;
* vendor/product IDs;
* device permissions;
* user/group access;
* controller network endpoint, when applicable;
* SDK/package availability;
* read-only device metadata.

The verifier must not send any command that can produce actuator motion.

---

### C. Robot State-Feedback Path

Identify whether a future implementation has a viable path for obtaining robot state.

Examples:

* joint positions;
* joint states;
* controller state;
* robot mode/status;
* gripper state, if exposed.

The task may:

* inspect interfaces;
* inspect SDK APIs;
* inspect message/protocol definitions;
* perform read-only state queries when explicitly non-motion.

The task shall not command joints or actuators.

---

### D. Gripper / Actuator Command-Path Discovery

Identify the intended future command path to the robot/manipulator and gripper.

Evidence may include:

* SDK/API discovery;
* protocol/interface documentation;
* callable interface inspection;
* configuration;
* existing adapter/driver interfaces.

The task shall prove only that the expected command path is known and addressable at the interface level.

No physical motion command shall be sent.

---

### E. Camera Identity and I/O

Identify the camera intended for the project and verify bounded frame acquisition when hardware is available.

Record:

* camera identity;
* USB/device identity where applicable;
* device path;
* supported/selected resolution;
* selected pixel format when observable;
* frame width and height;
* acquisition success;
* bounded frame count;
* acquisition timing/FPS observation where meaningful.

A camera test must terminate automatically.

It shall not launch indefinite streaming processes.

---

### F. Workspace and Motion-Safety Boundary Definition

Document the constraints that later motion-producing tasks must obey.

At minimum identify:

* intended workspace;
* joint or Cartesian limits available from authoritative project/vendor data;
* prohibited zones where known;
* initial pose assumptions;
* gripper constraints where applicable;
* operator supervision requirement.

This task documents these limits but shall not physically exercise them.

---

### G. Manual Abort / Emergency-Stop Readiness

Identify and document how future physical-motion tests will be stopped.

Record:

* hardware emergency-stop availability, if present;
* controller power-off / disable method;
* software stop or abort interface, if known;
* manual operator action;
* expected operator location during future supervised tests.

The task shall not claim that an E-stop is functionally validated under motion unless a later explicitly authorized safety task performs such validation.

Physical-motion testing is outside P0-006.

---

### H. Supervised Teleoperation Prerequisites

Determine whether sufficient prerequisites exist for `TASK-W1-002` to implement supervised teleoperation later.

Verify only prerequisites such as:

* target command interface identified;
* state-feedback interface identified;
* gripper interface identified where required;
* camera path identified where required;
* workspace limits documented;
* abort mechanism documented;
* operator supervision requirement documented.

Do not implement or execute teleoperation.

---

### I. Reproducible Evidence

Produce machine-readable evidence and human-readable reproduction guidance.

---

# 6. Explicitly Out of Scope

The following are prohibited in `TASK-P0-006`.

## Physical Behavior

* actuator motion;
* robot joint motion;
* gripper open/close execution;
* Cartesian motion;
* trajectory execution;
* autonomous motion;
* physical teleoperation.

## VLA / AI

* SmolVLA model loading;
* SmolVLA inference;
* VLA action generation;
* VLA-to-robot command mapping;
* training;
* fine-tuning;
* benchmark claims.

## Dataset

* Dataset V1 implementation;
* demonstration recording;
* training-data collection;
* episode generation;
* Hugging Face dataset publication.

## Integration

* ROS/VLA integration;
* Agent integration;
* Factory Agent behavior;
* AMR integration;
* Week 1 implementation;
* `TASK-W1-001`;
* `TASK-W1-002`;
* `TASK-W1-003`;
* `TASK-W1-004`.

## Other Phase 0 Work

* training-host procurement;
* cloud-GPU selection;
* training-budget decisions;
* `TASK-P0-007`;
* final `TASK-P0-004R` decision;
* baseline promotion.

Do not modify `TASK-P0-005` implementation or its accepted evidence.

---

# 7. Safety Constraints

This is a **non-motion readiness task**.

The implementation must obey all of the following:

1. No physical actuator command.
2. No gripper-motion command.
3. No trajectory command.
4. No teleoperation command.
5. No test requiring an unattended physical robot.
6. All hardware queries must use bounded timeouts.
7. Camera acquisition must use bounded frame counts or explicit timeouts.
8. Any potentially destructive or state-changing vendor command must be excluded.
9. Unknown interfaces shall be classified as unresolved rather than experimentally exercised.
10. If safety of an operation is uncertain, do not execute it.

---

# 8. Required Artifacts

The implementation shall produce at least the following.

## 8.1 Canonical Verifier

```text
scripts/verify_robot_io_readiness.py
```

Purpose:

* run bounded physical-readiness checks;
* avoid physical motion;
* produce deterministic structured output where practical;
* write result atomically;
* return non-zero when mandatory readiness blockers exist.

---

## 8.2 Machine-Readable Evidence

```text
results/phase0/P0-006_robot_io_readiness.json
```

The evidence must contain:

* task identity;
* timestamp;
* host/environment facts;
* target hardware identity;
* robot/device discovery;
* camera discovery;
* camera acquisition result;
* state-path classification;
* command-path classification;
* workspace/safety-boundary classification;
* abort/E-stop classification;
* teleoperation-prerequisite classification;
* unresolved blockers;
* deferred non-blockers;
* overall decision;
* verifier version/hash if practical.

---

## 8.3 Environment / Reproduction Document

```text
docs/hardware/robot_camera_io_readiness_v1.md
```

Include:

* target hardware decision;
* connection topology;
* device paths;
* permissions;
* camera configuration;
* state-feedback path;
* intended future control path;
* workspace assumptions;
* safety/abort method;
* reproduction commands;
* known limitations;
* what was explicitly not tested.

---

## 8.4 Risk Register

```text
plans/robot_camera_io_risks.md
```

Classify each item as:

```text
RESOLVED
DEFERRED
BLOCKING
OUT_OF_SCOPE
```

For each risk record:

* ID;
* description;
* evidence;
* impact;
* disposition;
* owner/future task where applicable.

---

## 8.5 Task History

Create/update:

```text
docs/task_history/TASK-P0-006/01_implementation.md
docs/task_history/TASK-P0-006/README.md
docs/task_history/README.md
```

Independent review history is created only during the subsequent review step.

---

# 9. Evidence Provenance

Avoid the ambiguous provenance taxonomy identified during `TASK-P0-005` review.

Every important evidence item should distinguish its source using fields such as:

```text
MEASURED
DECLARED_INPUT
DERIVED
DOCUMENTED
NOT_VERIFIED
```

Definitions:

* `MEASURED` — observed directly by the verifier on the host/device.
* `DECLARED_INPUT` — supplied explicitly by the operator/user and not independently measured.
* `DERIVED` — calculated from measured/documented inputs.
* `DOCUMENTED` — obtained from an accepted project/vendor definition and not directly measured.
* `NOT_VERIFIED` — no sufficient evidence exists.

A `DECLARED_INPUT`, `DERIVED`, or `DOCUMENTED` fact must not be represented as `MEASURED`.

---

# 10. Verifier Behavior

The canonical verifier must be:

* bounded;
* non-destructive;
* repeatable;
* non-motion;
* explicit about unsupported checks;
* explicit about missing hardware;
* atomic when writing JSON.

Recommended exit behavior:

```text
0 = DEVICE_IO_READY
2 = DEVICE_IO_BLOCKED
3 = VERIFIER_ERROR
```

The verifier shall never convert an internal diagnostic failure into a successful aggregate readiness result merely because unrelated checks passed.

Mandatory sub-check failures must propagate to the relevant aggregate status.

---

# 11. Minimum Verification Dimensions

The canonical evidence must contain explicit PASS/BLOCKED/NOT_VERIFIED-style results for the following dimensions.

```text
C01 Target hardware selected
C02 Robot/controller physically discoverable
C03 Stable device identity available
C04 Required host permission/access available
C05 Robot state-feedback path identified
C06 Robot state path observable without motion, where supported
C07 Future actuator command path identified
C08 Future gripper path identified or explicitly not applicable
C09 Camera selected
C10 Camera physically discoverable
C11 Bounded camera frame acquisition succeeds
C12 Camera configuration recorded
C13 Workspace/motion constraints documented
C14 Manual abort/E-stop path documented
C15 Supervised teleoperation prerequisites classified
C16 No physical motion occurred
C17 No Week 1 / dataset / model work occurred
C18 Evidence and documentation are internally consistent
```

---

# 12. Exit Criteria

## EC-01 — Correct Context

The implementation explicitly recognizes:

* P0-005 is accepted;
* P0-004R remains required;
* W1 is unauthorized;
* P0-006 does not itself authorize W1.

PASS only if these boundaries are preserved.

---

## EC-02 — Target Hardware Decision

The intended robot/manipulator target is unambiguously recorded.

If selection remains materially unresolved:

```text
DEVICE_IO_BLOCKED
```

---

## EC-03 — Robot Device Discovery

The host can identify the relevant robot/controller device or endpoint using measured evidence.

Device identity must be sufficiently stable for later reproducible use.

---

## EC-04 — Host Access

Required permissions and access to the discovered device are verified without changing system-wide security policy unnecessarily.

---

## EC-05 — State Interface Identified

A concrete future state-feedback path is documented.

The evidence distinguishes:

* directly measured state availability;
* interface-only discovery;
* unverified assumptions.

---

## EC-06 — Non-Motion State Observation

Where the target hardware safely permits it, at least one bounded read-only state/status observation succeeds.

If this cannot safely be performed, document why and classify the resulting readiness impact explicitly.

---

## EC-07 — Control Interface Identified

The future robot/manipulator command interface is identified without sending a motion command.

---

## EC-08 — Gripper Interface

The future gripper interface is identified if a gripper is part of the selected target.

No gripper actuation is performed.

---

## EC-09 — Camera Identity

The project camera is identified using measured device evidence.

---

## EC-10 — Camera Frame Acquisition

At least one bounded camera acquisition test succeeds when the camera is required and physically available.

No indefinite streaming process remains running.

---

## EC-11 — Camera Configuration

Relevant camera configuration used during verification is recorded.

At minimum:

* device;
* width;
* height;
* pixel format when available;
* observed frame/acquisition result.

---

## EC-12 — Workspace Constraints

Workspace/motion constraints needed by future supervised physical tasks are recorded using authoritative project/vendor sources or clearly identified project assumptions.

---

## EC-13 — Abort / E-Stop Path

A manual abort / emergency-stop strategy for later physical-motion tasks is explicitly documented.

Documentation must distinguish:

```text
AVAILABLE
DOCUMENTED_ONLY
NOT_VERIFIED
UNAVAILABLE
```

No claim of motion-tested emergency-stop effectiveness is permitted.

---

## EC-14 — Teleoperation Prerequisites

Prerequisites for future `TASK-W1-002` supervised teleoperation are explicitly classified.

This criterion does not require teleoperation implementation.

---

## EC-15 — No Motion

Evidence and repository changes demonstrate that no physical actuator/gripper/trajectory motion was commanded.

---

## EC-16 — Scope Preservation

No Dataset V1, VLA inference, training, ROS/Agent integration, or Week 1 implementation is introduced.

---

## EC-17 — Regression Safety

Focused tests for P0-006 and the existing full regression suite pass.

Existing accepted P0-005 evidence remains unchanged.

---

## EC-18 — Evidence Integrity

Machine-readable evidence, documentation, verifier output, and task history agree on all material measured facts and decisions.

---

## EC-19 — Repeatability

A safe verifier rerun produces a semantically consistent readiness decision.

Dynamic fields such as timestamps may differ.

---

## EC-20 — Final Decision

The task concludes with exactly one of:

```text
DEVICE_IO_READY
DEVICE_IO_BLOCKED
```

The final report explicitly states:

```text
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

---

# 13. Decision Rules

Return:

```text
DEVICE_IO_READY
```

only if all mandatory physical-readiness blockers for this task are resolved.

Examples of mandatory blockers include:

* no selected target robot/manipulator;
* required robot/controller cannot be discovered;
* device access is unavailable;
* required camera cannot be discovered/acquired;
* no credible future state path;
* no credible future control path;
* no safety/abort strategy for later physical operation;
* required workspace boundaries are unknown.

Return:

```text
DEVICE_IO_BLOCKED
```

if any mandatory blocker remains.

Do not downgrade a true mandatory blocker to a deferred issue merely to obtain a READY result.

---

# 14. Deferred Work

The following may be deferred without violating this task when explicitly recorded:

* actual teleoperation implementation → `TASK-W1-002`;
* Dataset V1 → `TASK-W1-003`;
* fine-tuning → `TASK-W1-004`;
* model inference and behavior validation → downstream authorized tasks;
* training compute/budget resolution → `TASK-P0-007`;
* final Phase 0 authorization → `TASK-P0-004R`.

Deferred work must not be described as verified.

---

# 15. Test Requirements

At minimum run:

## Focused Tests

* normal device-discovery path;
* missing robot-device path;
* permission/access failure path;
* missing camera path;
* bounded camera-acquisition failure;
* invalid/partial diagnostic parsing;
* evidence-output validation;
* timeout behavior;
* aggregate decision propagation.

A mandatory sub-check failure must cause the appropriate aggregate readiness failure.

---

## Safe Rerun

Run the canonical verifier at least twice when safe.

Verify:

* no physical motion;
* no leaked processes;
* no persistent undesired device changes;
* semantically stable result.

---

## Full Regression

Run the existing repository regression suite.

A P0-006 change must not break previously accepted Phase 0 behavior.

---

## Repository Validation

Run:

```bash
git diff --check
```

and relevant compile/syntax/JSON validation.

---

# 16. Required Implementation Report

At completion Codex shall report:

```markdown
# Implementation Result — TASK-P0-006

## Scope

## Files Changed

## Hardware Target

## Robot / Device I/O

## Camera I/O

## State / Control Path

## Safety / Abort Readiness

## Teleoperation Prerequisites

## Tests Run

## Exit Criteria

## Evidence

## Deferred Items

## Runtime / Device Blockers

## TASK History

## Repository Check

## Recommended Commit Message

## Final Status
```

The final status shall contain:

```text
DEVICE_IO_READY
```

or:

```text
DEVICE_IO_BLOCKED
```

and explicitly:

```text
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

---

# 17. Independent Review Policy

Implementation completion does not imply task acceptance.

After implementation, run a separate read-only Independent Review.

The reviewer shall verify:

* requirement traceability;
* scope compliance;
* safety boundaries;
* test adequacy;
* negative/failure paths;
* evidence integrity;
* claim accuracy;
* regression safety;
* final readiness decision.

Findings shall be classified:

```text
BLOCKER
HIGH
MEDIUM
LOW
```

Acceptance policy:

* BLOCKER → REJECT
* HIGH → normally REJECT
* MEDIUM → may be deferred only with explicit downstream blocking condition
* LOW → may be backlog

Only accepted evidence may be consumed by `TASK-P0-004R`.

---

# 18. TASK Completion Definition

`TASK-P0-006` implementation is complete when:

1. all required artifacts exist;
2. focused verification is complete;
3. full regression passes;
4. evidence integrity passes;
5. all exit criteria have explicit results;
6. final decision is recorded;
7. task history is recorded;
8. no downstream implementation was started.

The task becomes:

```text
ACCEPTED
```

only after the separate Independent Review accepts it.

Even an accepted `TASK-P0-006` does not authorize `TASK-W1-001`.

---

# 19. Expected Phase 0 Flow

```text
TASK-P0-005
ACCEPTED
    │
    ▼
TASK-P0-006
Robot / Camera / Device I/O Readiness
    │
    ├── DEVICE_IO_BLOCKED
    │        │
    │        └── resolve blocking physical readiness
    │
    └── DEVICE_IO_READY
             │
             ▼
        TASK-P0-007
        Training Resource /
        Budget Readiness
             │
             ▼
     outstanding finding remediation
             │
             ▼
        TASK-P0-004R
        Final VLA Re-Gate
             │
        ┌────┴────┐
        │         │
      NO_GO      GO /
             CONDITIONAL_GO
                  │
                  ▼
            W1 authorization
```

No part of this task may bypass `TASK-P0-004R`.
