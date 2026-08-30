# VLA Readiness Report v1

> Task: `TASK-P0-004`
>
> Verification date: 2026-08-30
>
> Evidence: `results/phase0/P0-004_vla_readiness.json`
>
> Final gate: **NO_GO**

## Decision

The current repository and measured WSL development environment are **not ready** to start `TASK-W1-001` or any real VLA implementation. Python and the design-only dataset/service boundaries are usable, but the required CUDA execution path, LeRobot runtime, SmolVLA prerequisites, selected physical device path, safe teleoperation path, and approved training budget are unresolved.

`TASK-W1-001` is **not authorized**. Dataset V1 collection, SmolVLA fine-tuning, VLA Skill Server implementation, and physical motion remain prohibited. This decision does not block or change the independent Agent/MVP lane.

## Evidence language

| Label | Meaning in this report |
|---|---|
| `MEASURED` | Produced by the non-destructive verifier on this host. |
| `INFERRED` | Design conclusion derived from accepted architecture or an explicit calculation; not runtime proof. |
| `DEFERRED` | Cannot be checked until the named environment/device and safety trigger exist. |
| `NOT AVAILABLE` | Required evidence or approval was not found. |

No benchmark, training, dataset episode, model-performance, or production-readiness claim is made.

## Environment

Measured by `python3 scripts/verify_vla_readiness.py`:

| Fact | Measured value |
|---|---|
| Host | Ubuntu 24.04.4 LTS under WSL2, x86_64 |
| Kernel | `6.18.33.2-microsoft-standard-WSL2` |
| CPUs | 8 logical CPUs |
| Memory | 16,615,333,888 bytes total; 14,172,033,024 bytes available at verification time |
| Swap | 4,294,967,296 bytes total/free |
| Repository filesystem | 1,081,101,176,832 bytes total; 983,736,274,944 bytes free at verification time |
| Python | CPython 3.12.3 at `/usr/bin/python3` |
| Virtual environment | None active (`VIRTUAL_ENV` and `CONDA_PREFIX` unset) |
| Package tools | system `pip 24.0` available; `uv` not found |
| Environment variables | `CUDA_VISIBLE_DEVICES`, `ROS_DISTRO`, `ROS_DOMAIN_ID`, `VLA_DATASET_ROOT`, `HF_HOME`, and Hugging Face token variables unset |

The frozen strategy remains a project-local Python environment managed with `uv`; the system interpreter must not be mutated. The following is a **proposed, unexecuted** reproduction command based on the accepted LeRobot v0.4.4 documentation baseline:

```bash
uv venv --python 3.12 .venv-vla
uv pip install --python .venv-vla/bin/python 'lerobot[smolvla]==0.4.4'
```

Before executing it, the selected CUDA host must have `uv`, and the version pin plus Python/CUDA compatibility must be reviewed. This task did not install anything.

## GPU / CUDA

Status: **FAIL — blocking** (`MEASURED`).

- `nvidia-smi` exists at `/usr/lib/wsl/lib/nvidia-smi` but returned code 255: NVML reported that GPU access is blocked by the operating system.
- `torch` is not importable in `/usr/bin/python3`.
- PyTorch CUDA availability is therefore false, device count is 0, CUDA runtime version is unavailable, and a basic GPU tensor allocation could not run.
- GPU model, driver version, VRAM total/free, and usable CUDA runtime remain unknown.

This result characterizes only this WSL environment. A separately approved CUDA host may satisfy the gate, but it must be measured with the same checks.

CPU-only work in this task was limited to repository inspection, import checks, schema/design documentation, and evidence generation. Model loading, inference, fine-tuning, and capacity checks still require the approved CUDA path.

## LeRobot

Status: **FAIL — blocking** (`MEASURED`).

- Distribution version/source revision: not available.
- `import lerobot`: failed because the package is absent.
- `lerobot.datasets.lerobot_dataset`: failed because the package is absent.
- `lerobot.policies.smolvla.modeling_smolvla`: failed because the package is absent.
- No dependency conflict was observed because dependency resolution was not started.

An isolated install/import check on the approved host is required. Installation is deliberately not part of this safe gate run.

## SmolVLA

Status: **FAIL — blocking** (`MEASURED` prerequisites plus `INFERRED` constraints).

- Planned identifier: `lerobot/smolvla_base`, retained from ADR-004.
- SmolVLA policy/config module discovery: not available because LeRobot is absent.
- Model download/load, inference, training, and benchmark: not attempted.
- Required compute/memory: `TBD`; measure the actual peak allocation on the selected host and pinned training configuration.
- An approved CUDA training budget/provider/limit is `NOT AVAILABLE`.

The model choice remains proposed. It is not accepted merely because an identifier and install extra are documented.

## Manipulator

Status: **DEFERRED — blocking** (`MEASURED` enumeration plus deferred native validation).

- No `/dev/ttyUSB*` or `/dev/ttyACM*` device is exposed in this WSL environment.
- Interpretation: **NOT EXPOSED IN CURRENT ENVIRONMENT**, not “hardware unsupported.”
- Target: `TBD` after physical inventory; a LeRobot-supported SO-101/SO-100-class leader/follower pair or documented adapter remains preferred by ADR-001.
- Connection: `TBD`, likely USB/serial through the selected LeRobot adapter.
- Expected command path: leader input → LeRobot teleoperator → validated follower adapter.
- Expected state feedback: follower joint/gripper state → timestamped recorder.
- Expected gripper path: supported leader/follower gripper channel; unverified.

No serial port was opened and no command was sent. The native robot-PC gate must record device identity, SDK/adapter version, mechanical/workspace limits, operator-controlled start, manual abort/E-stop, state feedback, and gripper behavior before motion.

## Camera

Status: **DEFERRED — blocking** (`MEASURED`).

- No `/dev/video*` device is exposed; a frame capture was therefore not attempted.
- Camera model, USB identity, native color format, clock source, and mount are `TBD`.
- One fixed external RGB camera at 640×480 and 30 FPS remains a hypothesis, not a measured requirement.
- Expected fields: `observation.images.camera`, `observation.state`, `timestamp`, and `calibration_revision`.

Trigger: attach the selected camera to the native robot PC, enumerate its identity/formats, then perform exactly one non-persisted frame capture. Sustained capture, calibration, timestamp alignment, and storage measurement belong to the later authorized smoke slice.

## Teleoperation

Status: **DEFERRED — blocking**.

Intended command path:

```text
Human leader input
  -> LeRobot teleoperation interface
  -> validated follower command adapter
  -> manipulator
```

Intended recording path:

```text
Robot state + camera frame
  -> timestamped observation/action capture
  -> LeRobot dataset recorder
```

The target command rate is `TBD` and must be derived from and measured on the selected adapter. State feedback, gripper control, workspace limits, operator start, and emergency/manual abort are unverified. Sustained teleoperation was not attempted.

## Dataset Pipeline

Status: **PASS for design readiness only** (`INFERRED`); Dataset V1 does not exist.

- Root: `data/vla` by default, overridable with `VLA_DATASET_ROOT`.
- Unit: immutable, LeRobot-compatible episodes.
- Observations: `observation.images.camera`, `observation.state`.
- Actions: `action` using the selected adapter's bounded representation.
- Alignment: `timestamp`, `frame_index`, and `episode_index` with monotonicity and observation/action synchronization checks.
- Annotation: natural-language manipulation instruction per episode.
- Versioning: immutable dataset version and manifest linked to collection configuration and Git commit.
- Validation: required fields/schema, monotonic timestamps, observation/action alignment, episode completeness/frame count, camera/calibration revision, and manual spot review.

Storage estimate (`INFERRED`, raw upper-bound calculation): one uncompressed RGB 640×480 stream at 30 FPS is 27,648,000 bytes/second or 1,658,880,000 bytes/minute. This excludes robot-state overhead and does not predict encoded LeRobot dataset size. Actual bandwidth and storage must be measured during an authorized smoke recording.

No dataset directory, episode, frame, or annotation was created by this task.

## Service Boundary

Status: **PASS for architecture readiness only** (`INFERRED` from the accepted architecture). No server was implemented.

The future typed surface may expose `/health`, `/version`, and `/execute` (or equivalent interfaces). The execution request/result must carry at least:

```text
schema_version, mission_id, request_id, action_id,
skill, instruction, observation_refs,
deadline_at, timeout_ms, status, error, component_version
```

The deterministic runtime retains authorization, deadlines/timeouts, retry budget, idempotency, reconciliation, and business recovery. VLA provides only a bounded approved manipulation policy. MoveIt and `ros2_control` retain validated motion and hardware/controller authority where they apply. The Agent cannot emit raw motor, trajectory, arbitrary ROS, shell, or actuator commands and cannot decide an ambiguous physical outcome.

## Readiness Matrix

| Area | Status | Evidence | Blocking? | Next action |
|---|---|---|---|---|
| Python | PASS | CPython 3.12.3; system pip 24.0 | No | Create the pinned project-local environment only after host approval. |
| GPU | FAIL | NVML blocked; Torch absent; CUDA device count 0; allocation unavailable | Yes | Select/approve a CUDA host and rerun GPU facts plus scalar allocation. |
| LeRobot | FAIL | Package and three required imports unavailable | Yes | Pin/install in an isolated approved environment and rerun imports. |
| SmolVLA | FAIL | Policy/config discovery unavailable; compute/memory unknown | Yes | Validate config discovery and capacity without training/download unless separately approved. |
| Robot I/O | DEFERRED | No serial devices exposed in WSL | Yes | Inventory the selected device on the native robot PC without motion. |
| Camera | DEFERRED | No video device exposed; capture not attempted | Yes | Enumerate and read one non-persisted frame on the native robot PC. |
| Teleoperation | DEFERRED | Command/state/gripper/stop paths unverified | Yes | Establish safety prerequisites, then schedule supervised smoke validation. |
| Dataset Pipeline | PASS | Fields, alignment, versioning, validation, and storage formula documented | No | Implement only after the gate authorizes the next task. |
| Service Boundary | PASS | Typed future surface and ownership conform to frozen architecture | No | Preserve in the later service task; do not implement now. |
| Training Budget | FAIL | No approved provider, limit, or owner authorization found | Yes | Record an approved host/cost/time limit and owner. |

## Blockers

1. No verified CUDA device, driver/VRAM facts, Torch CUDA runtime, or scalar tensor allocation.
2. LeRobot and required dataset/SmolVLA imports are unavailable.
3. SmolVLA config/capacity prerequisites are unverified.
4. Manipulator identity, adapter, state/gripper paths, bounds, and stop path are unverified.
5. Camera identity, format, timestamp source, and one-frame capture are unverified.
6. Physical teleoperation feasibility and safety path are unverified.
7. No approved CUDA training budget/provider/limit is documented.

## Deferred Checks

- **Native robot PC:** no-motion manipulator enumeration and exact adapter/version inventory.
- **Camera host:** device identity, format enumeration, one-frame capture, and timestamp-source identification.
- **Safety/operator:** mechanical/workspace bounds, operator-controlled start, manual abort/E-stop, and supervised authorization.
- **Approved CUDA host:** GPU/driver/VRAM, Torch/CUDA versions, scalar allocation, pinned LeRobot imports, SmolVLA config discovery, and measured capacity.
- **Budget approval:** provider/host, monetary or time limit, approver, and stop condition.
- **Later smoke slice only after a new gate decision:** command rate, state/action/image alignment, sustained teleoperation, calibration, and actual storage bandwidth.

## Final Gate

```text
VLA Readiness Gate = NO_GO
TASK-W1-001 authorized = false
```

Meaningful real VLA work cannot begin reproducibly or safely with the current evidence. Resolve the blocking facts and rerun `python3 scripts/verify_vla_readiness.py`; a subsequent reviewed gate decision must explicitly change `next_task_authorized` before `TASK-W1-001` starts.
