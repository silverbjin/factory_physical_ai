# Robot / Camera / Device I/O Readiness v1

> Task: `TASK-P0-006`
>
> Verification date: 2026-09-03
>
> Evidence: `results/phase0/P0-006_robot_io_readiness.json`
>
> Device I/O decision: **DEVICE_IO_BLOCKED**

## Decision boundary

`TASK-P0-006` implements a bounded, non-motion readiness verifier. The verifier
completed correctly, but the measured host and available declarations do not
resolve the mandatory physical-device prerequisites. Implementation completion
therefore does not change the physical readiness outcome:

```text
TASK-P0-006 implementation: complete after required validation/history
Physical readiness: DEVICE_IO_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

No robot, joint, gripper, trajectory, teleoperation, model, dataset, ROS, or
Agent command was executed.

## Evidence provenance

| Label | Meaning |
|---|---|
| `MEASURED` | Directly observed by the verifier on this host. |
| `DECLARED_INPUT` | Supplied by an operator and not independently measured. |
| `DERIVED` | Calculated from measured or documented inputs. |
| `DOCUMENTED` | Taken from an accepted project/vendor definition, not measured. |
| `NOT_VERIFIED` | No sufficient evidence exists. |

Declared, derived, and documented facts are not promoted to `MEASURED`.

## Target hardware decision

The final robot/manipulator target is `NOT_VERIFIED` and remains unresolved.
`ADR-001` records only a preferred LeRobot-supported SO-101/SO-100-class
leader/follower direction; it explicitly defers selection until physical
enumeration and safety/port/camera evidence exist. That preference is not a
selected device and was not used as measured evidence.

| Field | Result | Provenance |
|---|---|---|
| Manufacturer/model/controller | Unresolved | `NOT_VERIFIED` |
| Firmware/software version | Unresolved | `NOT_VERIFIED` |
| Connection type | Unresolved | `NOT_VERIFIED` |
| Stable robot identity | Unresolved | `NOT_VERIFIED` |
| Gripper applicability | Unresolved | `NOT_VERIFIED` |

## Connection topology and device access

The canonical run executed on Ubuntu 24.04.4 LTS under WSL2. It enumerated only
the fixed patterns `/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/serial/by-id/*`,
`/dev/video*`, and `/dev/v4l/by-id/*` in a child process with a five-second
timeout. It found no robot, stable serial, camera, or stable video candidates.

Because no target was declared, the verifier did not open a serial or controller
device and did not infer that any enumerated path belonged to the project.
Robot read/write permission and controller endpoint access remain
`NOT_VERIFIED`; no permission or security-policy change was made.

## Robot state and future control paths

| Path | Result | Provenance |
|---|---|---|
| State-feedback interface | Not identified | `NOT_VERIFIED` |
| Bounded non-motion state observation | Not attempted; no explicitly safe read-only snapshot was declared | `NOT_VERIFIED` |
| Future actuator command interface | Not identified or invoked | `NOT_VERIFIED` |
| Future gripper interface | Applicability/path unresolved; not invoked | `NOT_VERIFIED` |

The verifier permits only an explicitly declared `regular_file_snapshot` marked
`safe_read_only=true`, limits the read to 4096 bytes, and enforces a state-query
timeout. Unknown SDK, vendor, serial, network, and controller operations are not
executed.

## Camera identity and I/O

The project camera is unresolved. No `/dev/video*` or `/dev/v4l/by-id/*`
candidate was measured on the canonical host, and no declared camera path was
available. Consequently:

| Field | Result | Provenance |
|---|---|---|
| Camera manufacturer/model | Unresolved | `NOT_VERIFIED` |
| Device/stable identity | No candidates enumerated; no selected identity | `MEASURED` / `NOT_VERIFIED` |
| Width/height/pixel format | Unresolved | `NOT_VERIFIED` |
| Frame acquisition | Not attempted | `NOT_VERIFIED` |
| Frames persisted | 0 | `DERIVED` from verifier behavior |

When a valid operator declaration is supplied, acquisition is limited to at
most five frames and at most 30 seconds. The canonical run requested one-frame
bounds but correctly skipped acquisition because no selected readable camera
was present. No stream or capture process was left running.

## Workspace and motion-safety boundary

The intended workspace, authoritative joint/Cartesian limits, prohibited zones,
initial pose assumptions, and gripper constraints are `NOT_VERIFIED`. Operator
supervision is mandatory for every later physical task, but this general rule is
not a substitute for target-specific limits.

No limit was physically exercised. A future declaration must identify each
constraint and declare its source as either `DOCUMENTED` or `DECLARED_INPUT`.
The verifier preserves that claim as `declared_source_kind` while keeping the
declaration itself at provenance `DECLARED_INPUT`; only a separate review of an
accepted project/vendor source may establish `DOCUMENTED` evidence.

## Manual abort / emergency stop

The target-specific abort classification is `NOT_VERIFIED`. Hardware E-stop
availability, controller disable/power-off procedure, software abort interface,
manual operator action, and required operator location remain unresolved.

The verifier requires any declaration to state `motion_tested=false` for this
task. Nothing in this report claims that an E-stop or abort path was functionally
tested under motion.

## Supervised teleoperation prerequisites

The prerequisite classification is `BLOCKED`. Target identity, stable device
access, state feedback, command/gripper paths, camera I/O, workspace limits, and
abort readiness are unresolved. Physical teleoperation was neither implemented
nor executed, and `TASK-W1-002` is not authorized by this result.

## Safe reproduction

Reproduce the current no-declaration, discovery-only result from the repository
root:

```bash
python3 scripts/verify_robot_io_readiness.py \
  --device-discovery-timeout-seconds 5 \
  --camera-timeout-seconds 5 \
  --state-timeout-seconds 2 \
  --camera-frame-count 1
```

Expected exit codes:

```text
0 = DEVICE_IO_READY
2 = DEVICE_IO_BLOCKED
3 = VERIFIER_ERROR
```

Exit code `2` is the expected canonical result until the mandatory blockers are
resolved. A later operator may use `--declarations /absolute/path/to/input.json`
only after confirming every referenced interface is non-motion and safe to
query. Declared robot and camera paths must remain under the selected
`--dev-root`, with stable identities under `serial/by-id` and `v4l/by-id`.
If a vendor/device command has uncertain side effects, omit it and retain
`NOT_VERIFIED`.

Safe verification commands that do not contact a robot controller are:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 -m unittest tests.test_verify_robot_io_readiness -v
python3 -m json.tool results/phase0/P0-006_robot_io_readiness.json >/dev/null
git diff --check
```

## Known limitations and explicitly untested items

- No target robot/manipulator or camera was selected.
- No robot/controller endpoint was opened or queried.
- No robot state was observed.
- No command or gripper interface was invoked.
- No camera frame was acquired.
- No workspace limit, abort path, or E-stop was functionally exercised.
- No calibration, synchronization, teleoperation, recording, Dataset V1,
  SmolVLA model loading/inference, training/fine-tuning, ROS/VLA integration, or
  Agent integration was performed.
- Training host/budget readiness belongs to `TASK-P0-007`.
- Final Phase 0 authorization belongs to `TASK-P0-004R`.
