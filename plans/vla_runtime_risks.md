# VLA Runtime Risks after TASK-P0-005

> Verification date: 2026-09-02
>
> Runtime decision: **RUNTIME_READY**
>
> Source evidence: `results/phase0/P0-005_vla_runtime.json`
>
> `TASK-W1-001` remains unauthorized; `TASK-P0-004R` remains required.

| ID | Risk | Impact | Current evidence | Mitigation | Trigger / exit signal | Owner | Blocking for P0-005 runtime decision? | Blocking for later P0-004R readiness? |
|---|---|---|---|---|---|---|---|---|
| VLA-RT-R01 | SmolVLA model/training capacity in 6 GB is unknown | Model load, inference, or fine-tuning may exceed local VRAM | CUDA tensor and code/config discovery PASS; weights/inference/training not attempted; training fit `NOT_VERIFIED` | Run only a separately authorized, configuration-specific capacity task; retain remote CUDA-host option | Measured model/training peak memory and outcome for an approved config | VLA owner / compute owner | No | Yes |
| VLA-RT-R02 | LeRobot 0.4.4 is older than upstream 0.6.1 | Later hardware/data APIs may differ from current upstream guidance | 0.4.4 was explicitly retained and fully imports; 0.6.1 was considered but not adopted | Review version at P0-004R/ADR-004; migrate only with explicit API/dependency evidence | ADR-004 records retained version or an approved migration with regression evidence | Lead Engineer / VLA owner | No | Yes |
| VLA-RT-R03 | Restricted sandboxes can hide WSL NVML/GPU access | A valid host may produce a false blocked result inside a restricted runner | Sandboxed `nvidia-smi` failed; authorized host probe and PyTorch CUDA tensor both PASS | State the execution boundary and require host GPU access for runtime evidence | Verifier and tensor check pass in the intended execution boundary | Lead Engineer / compute owner | No | Yes, at re-gate execution time |
| VLA-RT-R04 | Compatible transitive dependencies can drift on a future resolver run | Recreated environment may differ despite direct pins | Three direct pins plus complete 115-package snapshot recorded; `uv pip check` PASS | Compare recreated snapshot; add a reviewed lock/constraints artifact before long-lived training if required | Recreated direct and relevant transitive versions match or differences are explicitly reviewed | VLA owner | No | No, unless recreation differs |
| VLA-RT-R05 | System CUDA Toolkit is absent | Source builds/custom CUDA extensions would not have `nvcc` | `nvcc` is `NOT_AVAILABLE`; selected official PyTorch wheel executes CUDA successfully | Do not install a Toolkit without a scoped need; gate any custom extension separately | A later task either needs no Toolkit or records an approved Toolkit/version check | Compute owner | No | No for current pinned wheel path |
| VLA-RT-R06 | Physical manipulator/device and camera paths remain unverified | Real demonstrations cannot be captured safely | P0-005 performed no device or camera I/O | Complete native identity/connectivity and no-motion safety checks | `TASK-P0-006` evidence passes | Hardware owner / perception owner | No | Yes |
| VLA-RT-R07 | Teleoperation and recording path remains unverified | State/action/image data may be unsafe or unusable | No motion, capture, calibration, alignment, or recording occurred | Run only the supervised, bounded smoke task after P0-006 prerequisites | `TASK-P0-007` evidence passes | Safety operator / VLA data owner | No | Yes |
| VLA-RT-R08 | Training budget/host approval is absent | Fine-tuning could be infeasible or create uncontrolled cost | No provider, time/cost limit, approver, or stop condition was added | Record explicit owner, host/provider, cap, and stop rule in the designated later task | Approved budget record exists | Project owner / compute owner | No | Yes |
| VLA-RT-R09 | Runtime readiness could be misread as VLA implementation authorization | Dataset/training/integration could start before safety and hardware gates | Evidence fixes `task_w1_001_authorized=false` and `p0_004r_regate_required=true` | Preserve the authorization invariant in every downstream task | P0-004R explicitly reviews all blocker evidence and alone changes authorization | Lead Engineer / reviewer | No | Yes |

## Resolved P0-005 runtime blockers

| Former P0-004 blocker | P0-005 evidence |
|---|---|
| CUDA execution path unavailable | PyTorch `2.10.0+cu130` synchronized CUDA tensor PASS on RTX 2060 Max-Q |
| No reproducible LeRobot environment | `.venv-vla`, `uv 0.12.9`, LeRobot `0.4.4`, direct pins and package snapshot recorded |
| SmolVLA installed modules/config unavailable | policy/model/config/processor imports and `SmolVLAConfig(device="cuda")` PASS |

## Stop rule

Do not convert `RUNTIME_READY` into a claim that SmolVLA weights load, infer, or fine-tune in 6 GB. Do not start device I/O, camera work, teleoperation, Dataset V1, model loading, inference, training, evaluation, VLA Skill Server, ROS/Agent integration, or `TASK-W1-001` from this result. Only P0-004R may issue the later full VLA readiness authorization after P0-006/P0-007 evidence exists.
