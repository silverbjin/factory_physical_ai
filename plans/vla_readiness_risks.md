# VLA Readiness Risks after TASK-P0-004

> Gate date: 2026-08-30
>
> Current decision: **NO_GO**
>
> Source evidence: `results/phase0/P0-004_vla_readiness.json`

| ID | Risk | Impact | Current evidence | Mitigation | Trigger / exit signal | Owner | Blocking? |
|---|---|---|---|---|---|---|---|
| VLA-R01 | CUDA execution path unavailable | Model/config capacity checks, inference, and fine-tuning cannot be evidenced | `nvidia-smi` returns NVML access blocked; Torch absent; device count 0; allocation unavailable | Select an approved CUDA host; record GPU, driver, VRAM total/free, Torch/CUDA versions, and scalar allocation | All GPU checks report `MEASURED/PASS` on the intended host | Lead Engineer / compute owner | Yes |
| VLA-R02 | LeRobot environment is not reproducible yet | Dataset recorder and SmolVLA workflow cannot start | `lerobot` distribution and required imports absent; `uv` absent; no project VLA environment | Approve a version pin and isolated environment, install on the selected host, then rerun required imports | Package version/source revision and all required imports report `PASS` | Lead Engineer | Yes |
| VLA-R03 | SmolVLA capacity is unknown | Chosen model may exceed the approved host or budget | Config module unavailable; no model load; memory requirement `TBD` | Perform a non-training config/capacity smoke check on the approved host; record measured peak memory before training approval | Model/config discovery and capacity facts are recorded without fabricated benchmark claims | VLA owner / compute owner | Yes |
| VLA-R04 | Physical manipulator path is unselected and unverified | Teleoperation and demonstrations cannot be acquired safely | No serial devices exposed in WSL; identity, adapter, feedback, gripper, and bounds unknown | Inventory a supported leader/follower or documented adapter on the native robot PC without motion | Device identity, versions, state/gripper paths, bounds, operator start, and stop path are recorded | Hardware owner / safety operator | Yes |
| VLA-R05 | Camera path and timing are unverified | Observations may be missing, incompatible, or misaligned | No `/dev/video*`; model, format, clock, mount, capture, and calibration unknown | Enumerate the chosen camera and read one frame; later measure FPS/alignment/calibration during authorized smoke recording | Identity/formats and one-frame capture pass; later alignment gate is scheduled | Perception owner | Yes |
| VLA-R06 | Teleoperation safety and feedback are unverified | Motion could be unsafe and recorded actions unusable | No command rate, state feedback, gripper, workspace limit, operator start, or E-stop evidence | Define physical checklist and require supervised native-PC validation; do not move hardware in this gate | Approved checklist and all pre-motion safety facts exist | Safety operator / hardware owner | Yes |
| VLA-R07 | CUDA training budget is not approved | Work may stop after data collection or create uncontrolled cost | No provider, host, limit, approver, or stop condition documented | Approve host/provider plus cost/time cap and stop condition before the next gate decision | Approval record identifies owner, limit, and selected host | Project owner | Yes |
| VLA-R08 | WSL non-enumeration may be misreported as unsupported hardware | Incorrect procurement or architecture decision | Only this WSL host was measured | Keep the exact phrase `NOT EXPOSED IN CURRENT ENVIRONMENT`; validate the native robot PC separately | Native inventory evidence replaces the deferred fact | Lead Engineer | No |
| VLA-R09 | Dataset size/alignment assumptions may be wrong | Storage exhaustion or unusable episodes during collection | Only a raw 640×480×RGB×30 FPS upper-bound calculation exists | Measure actual encoding, bandwidth, timestamp monotonicity, and action/image alignment in the authorized smoke slice | Machine-readable smoke report records measured size/rate/alignment | VLA data owner | No for design; Yes before Dataset V1 |
| VLA-R10 | Future service implementation may drift across safety boundaries | VLA or Agent could bypass deterministic/ROS authority | Boundary is documented but not executable | Preserve contract review and add contract tests in the later service task | Typed contract tests prove runtime/VLA/MoveIt/`ros2_control` ownership | Integration owner | No for current gate |

## Stop rule

Do not substitute synthetic data, CPU-only training claims, a mocked policy, or an uninspected remote host for any blocking item. `TASK-W1-001` remains unauthorized until a rerun produces an explicitly reviewed gate that permits it.
