# VLA Runtime Environment v1

> Task: `TASK-P0-005`
>
> Verification date: 2026-09-02
>
> Evidence: `results/phase0/P0-005_vla_runtime.json`
>
> Runtime decision: **RUNTIME_READY**

## Decision

The project-local VLA software runtime is ready for later gated work. The measured host can execute a real PyTorch CUDA operation, the explicitly pinned LeRobot baseline imports successfully, and the installed SmolVLA code/configuration surface can be discovered without downloading model weights.

This decision is narrow:

```text
P0-005 software runtime: ready
TASK-W1-001 authorized: false
TASK-P0-004R re-gate required: true
```

It does not establish physical-device readiness, camera readiness, teleoperation safety, Dataset V1 readiness, training-budget approval, SmolVLA model loading/inference, or local fine-tuning capacity.

## Evidence language

| Label | Meaning |
|---|---|
| `MEASURED` | Produced by `scripts/verify_vla_runtime.py` or the recorded isolated installation on this host. |
| `INFERRED` | A bounded conclusion from measured facts or authoritative package metadata; not direct model execution proof. |
| `DEFERRED` | Intentionally assigned to a later readiness task. |
| `NOT_AVAILABLE` | The inspected item is absent or could not be measured. |

## Input Observations vs Re-measured Evidence

The supplied observations were treated as inputs only and were independently re-measured.

| Fact | Input observation | P0-005 measurement | Result |
|---|---|---|---|
| Host | WSL2 / Ubuntu 24.04 | Ubuntu 24.04.4 LTS, kernel `6.18.33.2-microsoft-standard-WSL2` | Match |
| WSL GPU bridge | `/dev/dxg` exists | `/dev/dxg` exists | Match |
| NVIDIA-SMI | `580.102.01` | `580.102.01` | Match |
| Driver | `581.57` | `581.57` | Match |
| Driver-reported CUDA | `13.0` | `13.0` | Match; driver capability only |
| GPU | RTX 2060-class | `NVIDIA GeForce RTX 2060 with Max-Q Design` | Exact model measured |
| VRAM | 6144 MiB | 6144 MiB total; 5955 MiB free at NVIDIA query | Match |
| Compute capability | Not supplied | `7.5` from NVIDIA-SMI and `(7, 5)` from PyTorch | Measured |
| Compute processes | None | 0 compute processes | Match at verification time |

The official evidence run required host GPU access. A restricted sandbox can block NVML even when the WSL host is correctly configured; this is why the evidence records the command return codes and actual tensor result rather than assuming visibility.

## Environment Strategy

The VLA packages are isolated at:

```text
/home/jinho/projects/factory_physical_ai_p0_005/.venv-vla
```

The environment was created by `uv` from `/usr/bin/python3.12`. Package installation targeted `.venv-vla/bin/python` explicitly. `/usr/bin/python3` still reports neither `torch` nor `lerobot`, providing an after-install check that the system interpreter was not used as the package target.

The interactive shell contains ROS workspace paths in `PYTHONPATH`. The official P0-005 evidence run clears `PYTHONPATH` for that process so imports and the package snapshot come only from the standard library and `.venv-vla`; it does not alter the user's shell configuration. The verifier fails the isolation check if a non-empty ambient `PYTHONPATH` is supplied.

`.venv-vla/` is excluded by `.gitignore`. No environment, cache, CUDA library, model weight, dataset, token, or credential is committed.

## Python Version Decision

Selected: **CPython 3.12.3**.

| Candidate | Decision | Reason |
|---|---|---|
| Python 3.12 | Selected | Already provided by Ubuntu 24.04; satisfies LeRobot 0.4.4's Python `>=3.10` metadata and the selected PyTorch wheel. |
| Python 3.10 / 3.11 | Rejected as unnecessary | Compatible with the retained LeRobot release but would add an unnecessary managed interpreter. |
| Python 3.13 | Rejected as unnecessary | Not installed and provides no compatibility advantage for the retained baseline. |

Using the distribution interpreter as the base for an isolated virtual environment does not authorize installing packages into system Python. `sudo pip`, `uv pip --system`, `--break-system-packages`, OS Python replacement, and system site-package mutation remain prohibited.

## uv Setup

Selected: `uv 0.12.9 (x86_64-unknown-linux-gnu)` at `/home/jinho/.local/bin/uv`.

It was installed from the pinned official standalone installer with `UV_UNMANAGED_INSTALL`, so no shell profile or system Python was modified.

```text
installer: https://astral.sh/uv/0.12.9/install.sh
installer SHA-256: 222e006c0fe4a0d793031833e469b21df72311f4e3526ffecca0e19e6dfabc32
scope: user-scoped unmanaged binary
```

## NVIDIA Driver vs Toolkit vs PyTorch CUDA

These are independent facts:

| Layer | Measured result | Interpretation |
|---|---|---|
| NVIDIA driver | `581.57`; NVIDIA-SMI reports CUDA `13.0` | The driver reports its CUDA compatibility level. |
| System CUDA Toolkit | `nvcc` not found | CUDA Toolkit 13.0 is not proven installed. |
| PyTorch package | `2.10.0+cu130` | The installed wheel was built for its packaged CUDA 13.0 runtime. |
| PyTorch runtime | `torch.version.cuda == "13.0"` | Runtime fact reported by the installed PyTorch build. |
| CUDA execution | PASS | A synchronized tensor operation ran on `cuda:0` and returned the expected result. |
| LeRobot | `0.4.4` imports PASS | Compatibility is measured for the pinned environment, not inferred from NVIDIA-SMI. |
| SmolVLA training in 6 GB | `NOT_VERIFIED` | No model load, inference, or training was authorized or run. |

Therefore, `nvidia-smi` reporting `CUDA Version: 13.0` does **not** by itself prove:

- CUDA Toolkit 13.0 is installed;
- PyTorch is using CUDA 13.0;
- PyTorch CUDA works;
- LeRobot is compatible; or
- SmolVLA training fits in 6 GB VRAM.

P0-005 establishes the PyTorch and LeRobot facts through separate runtime checks. It deliberately leaves the SmolVLA training-fit claim unverified.

## PyTorch CUDA Verification

| Check | Measured value |
|---|---|
| PyTorch | `2.10.0+cu130` |
| torchvision | `0.25.0+cu130` |
| `torch.version.cuda` | `13.0` |
| `torch.cuda.is_available()` | `true` |
| Device count | 1 |
| Device | `NVIDIA GeForce RTX 2060 with Max-Q Design` |
| Compute capability | `(7, 5)` |
| Runtime-visible memory | 6,442,123,264 bytes total |
| Free memory at check | 5,352,980,480 bytes |
| cuDNN | available; version `91501` |

The official PyTorch wheel includes `sm_75` in its measured build configuration, matching the device capability.

## CUDA Tensor Execution

The verifier performed a bounded 2×2 `float32` matrix multiplication on `cuda:0`:

```text
[[1, 2],       [[5, 6],       [[19, 22],
 [3, 4]]   @    [7, 8]]   =    [43, 50]]
```

It synchronized the CUDA device, copied the result to CPU, and asserted exact equality.

| Fact | Measured value |
|---|---:|
| Status | PASS |
| Numerical assertion | `true` |
| Allocated before | 0 bytes |
| Reserved before | 0 bytes |
| Allocated after | 8,521,216 bytes |
| Reserved after | 23,068,672 bytes |
| Peak allocated | 8,521,216 bytes |

The recorded elapsed time is diagnostic-only. It is not a model, inference-latency, or performance benchmark.

## LeRobot Version Decision

The repository baseline **LeRobot 0.4.4** was retained explicitly. Current upstream **0.6.1** was considered but not adopted because that would introduce an API/dependency migration unrelated to proving the ADR-004 baseline and would require separate architecture/dependency review.

Selected direct pins:

```text
torch==2.10.0       (resolved: 2.10.0+cu130)
torchvision==0.25.0 (resolved: 0.25.0+cu130)
lerobot[smolvla]==0.4.4
```

LeRobot 0.4.4 official metadata declares:

```text
Python >=3.10
torch >=2.2.1,<2.11.0
torchvision >=0.21.0,<0.26.0
```

Its `smolvla` extra declares compatible ranges for Transformers, num2words, Accelerate, and safetensors. The resolved 115-package environment passes `uv pip check`; the complete package snapshot is in the machine-readable evidence.

Authoritative sources:

- [LeRobot 0.4.4 package metadata](https://pypi.org/project/lerobot/0.4.4/)
- [LeRobot 0.4.4 source revision](https://github.com/huggingface/lerobot/tree/8fff0fde7c79f23a93d845d1a50e985de01f8b8a)
- [PyTorch previous-version wheel matrix](https://pytorch.org/get-started/previous-versions/)

ADR-004 remains proposed. P0-004R, not P0-005, owns the later full-stack readiness/ADR review.

## LeRobot Import Validation

All imports were checked independently:

| Module | Status |
|---|---|
| `lerobot` | PASS |
| `lerobot.datasets.lerobot_dataset` | PASS |
| `lerobot.policies.smolvla` | PASS |
| `lerobot.policies.smolvla.modeling_smolvla` | PASS |
| `lerobot.policies.smolvla.configuration_smolvla` | PASS |
| `lerobot.policies.smolvla.processor_smolvla` | PASS |

Import success is not model-load, inference, or training evidence.

## SmolVLA Module/Config Discovery

The verifier imported the policy, modeling, configuration, and processor modules, then instantiated `SmolVLAConfig(device="cuda")` without using `from_pretrained` or accessing the model hub.

Selected discovered configuration values:

| Field | Value |
|---|---|
| `type` | `smolvla` |
| `device` | `cuda` |
| `chunk_size` | 50 |
| `n_action_steps` | 50 |
| `resize_imgs_with_padding` | `[512, 512]` |
| `tokenizer_max_length` | 48 |
| `vlm_model_name` | `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` |
| `freeze_vision_encoder` | `true` |
| `train_expert_only` | `true` |
| `load_vlm_weights` | `false` |

Planned model identifier remains `lerobot/smolvla_base`. It was recorded as a plan, not downloaded or loaded.

## RTX 2060 6 GB Capability Classification

```text
CUDA_RUNTIME_AND_SMOLVLA_CODE_READY_TRAINING_UNVERIFIED
```

Measured and supported claims:

- the WSL host exposes the RTX 2060 Max-Q and 6144 MiB VRAM;
- the pinned PyTorch build executes a real CUDA tensor on that GPU;
- the pinned LeRobot and SmolVLA modules/configuration import and instantiate.

Claims not supported by this task:

| Capability | Status |
|---|---|
| SmolVLA model loading | Not tested |
| Local SmolVLA inference | Not tested |
| Local SmolVLA fine-tuning | Not tested |
| SmolVLA training fit in 6 GB | `NOT_VERIFIED` |

Reduced batch size, mixed precision, gradient accumulation/checkpointing, parameter-efficient tuning, or a remote CUDA host are candidate mitigations only. They are `INFERRED`, not measured feasibility.

## Limitations

1. P0-005 does not prove that the 450M SmolVLA weights load or infer within 6 GB.
2. No fine-tuning configuration or peak model/training memory was measured.
3. Direct dependencies are pinned and the full resolved snapshot is recorded, but a future resolver run may select newer compatible transitive packages unless a lock artifact is introduced by an authorized dependency-management task.
4. WSL GPU access may be unavailable inside restricted execution sandboxes even when host execution works; future evidence runs must state their execution boundary.
5. LeRobot 0.6.1 exists upstream but was not evaluated or adopted in this task.
6. No physical device, camera, teleoperation, dataset, model service, ROS, or Agent boundary was exercised.

## Reproduction Commands

The following records the actual bounded setup pattern. Review a downloaded installer before execution and verify its SHA-256.

```bash
curl -LsSf https://astral.sh/uv/0.12.9/install.sh -o /tmp/p0-005-uv-install.sh
sha256sum /tmp/p0-005-uv-install.sh
env UV_UNMANAGED_INSTALL=/home/jinho/.local/bin sh /tmp/p0-005-uv-install.sh

env UV_CACHE_DIR=/tmp/p0-005-uv-cache /home/jinho/.local/bin/uv \
  venv --python /usr/bin/python3.12 .venv-vla

env UV_CACHE_DIR=/tmp/p0-005-uv-cache /home/jinho/.local/bin/uv pip install \
  --python .venv-vla/bin/python \
  --torch-backend cu130 \
  --strict \
  'torch==2.10.0' \
  'torchvision==0.25.0' \
  'lerobot[smolvla]==0.4.4'

env PATH=/home/jinho/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  PYTHONPATH= \
  UV_CACHE_DIR=/tmp/p0-005-uv-cache \
  .venv-vla/bin/python scripts/verify_vla_runtime.py
```

The final command needs access to the host GPU. It does not install packages or access models/devices other than the NVIDIA runtime.

Rollback is environment-local: rename `.venv-vla` to a uniquely named disabled directory for inspection, or remove only that exact environment after confirming no process uses it, then recreate it from the pinned commands. The user-scoped `uv` binary is shared tooling and should not be removed as part of a VLA-environment rollback.

## Deferred Readiness Blockers

| Deferred area | Owner task | P0-005 disposition |
|---|---|---|
| Manipulator/device identity, connectivity, and no-motion safety prerequisites | `TASK-P0-006` | DEFERRED |
| Camera identity/connectivity and no-motion readiness | `TASK-P0-006` | DEFERRED |
| Supervised teleoperation/recording smoke readiness | `TASK-P0-007` | DEFERRED |
| Training host/provider/time/cost approval | `TASK-P0-007` | DEFERRED |
| Complete VLA readiness re-gate and ADR-004 review | `TASK-P0-004R` | DEFERRED |
| `TASK-W1-001` authorization | `TASK-P0-004R` only | false |

P0-005 resolves the software/runtime blockers only. `TASK-W1-001` remains unauthorized until the later P0-004R evidence explicitly changes that gate.
