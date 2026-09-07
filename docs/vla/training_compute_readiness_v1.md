# VLA Training Compute Readiness v1

> Task: `TASK-P0-007`
>
> Canonical evidence: `results/phase0/P0-007_training_resource_readiness.json`
>
> Assessment date: 2026-09-05

## Executive decision

```text
Local training classification: TRAINING_NOT_VERIFIED
Training execution mode: UNRESOLVED
Primary compute path: UNRESOLVED
Storage readiness: STORAGE_NOT_VERIFIED
Budget policy: UNRESOLVED
Budget feasibility: NOT_VERIFIED
Fallback compute: NOT_VERIFIED
Training-resource outcome: TRAINING_RESOURCE_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

`TASK-P0-007` is a readiness assessment, not a training run. The local host is
usable for development, configuration, bounded metadata/runtime checks, and
artifact inspection. No evidence authorized by this task proves that SmolVLA
training fits in the local 6 GiB GPU, and no approved external resource or
budget policy has been supplied. The assessment therefore fails closed.

Task implementation completion and the resource outcome are separate. A
complete verifier/documentation implementation may truthfully retain
`TRAINING_RESOURCE_BLOCKED`.

## Provenance vocabulary

Only these values are accepted by the verifier:

| Value | Meaning |
|---|---|
| `MEASURED` | Directly observed by the bounded verifier. |
| `DECLARED_INPUT` | Explicit operator input, not independently verified. |
| `DERIVED` | Calculated or classified from evidenced inputs. |
| `DOCUMENTED` | Taken from the authoritative task or accepted project artifact. |
| `NOT_VERIFIED` | Evidence is absent or insufficient. |

No `DECLARED_INPUT`, `DERIVED`, or `DOCUMENTED` item is represented as
`MEASURED`.

## Accepted context

| Item | Result | Provenance |
|---|---|---|
| `TASK-P0-005` | `ACCEPTED`; evidence SHA-256 must equal `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae` | `DOCUMENTED` |
| P0-005 runtime | `RUNTIME_READY` | `DOCUMENTED` |
| `TASK-P0-006` | `ACCEPTED` per authoritative `TASK-P0-007` prerequisite contract | `DOCUMENTED` |
| P0-006 physical outcome | `DEVICE_IO_BLOCKED`; evidence SHA-256 must equal `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506` | `DOCUMENTED` |

P0-007 neither edits those evidence files nor remediates any P0-006 physical
blocker.

## Local host measurements

The canonical verifier performs bounded metadata/runtime probes. Values below
are from the implementation-time run; the JSON artifact is authoritative for
the final run.

| Fact | Observed value | Provenance | Interpretation |
|---|---:|---|---|
| GPU | `NVIDIA GeForce RTX 2060 with Max-Q Design` | `MEASURED` | Identity only |
| VRAM | `6144 MiB` total; `5955 MiB` free at query | `MEASURED` | Capacity snapshot only |
| Compute capability | `7.5` | `MEASURED` | Device property, not training proof |
| Host RAM | `16,615,329,792` bytes total | `MEASURED` | `/proc/meminfo` |
| Repository filesystem | `1,081,101,176,832` bytes total; approximately `978 GB` free | `MEASURED` | Free capacity changes over time |
| Accepted VLA environment | `/home/jinho/projects/factory_physical_ai_p0_005/.venv-vla` | `DOCUMENTED` | Location recorded by accepted P0-005 evidence |
| Environment footprint | `6,198,765,955` bytes | `MEASURED` | Packages only; excludes model/data/checkpoints |
| Intended HF cache | `/home/jinho/.cache/huggingface` | `DOCUMENTED` | Default path; not created by this task |

The PyTorch metadata probe in the accepted environment re-observed:

```text
Python       3.12.3
LeRobot      0.4.4 (accepted baseline; not upgraded)
PyTorch      2.10.0+cu130
torchvision  0.25.0+cu130
CUDA runtime 13.0
CUDA available true
```

The probe imports PyTorch/torchvision and reads CUDA properties. It does not
load SmolVLA weights, allocate a synthetic training tensor, instantiate an
optimizer, read training data, or execute an update.

## Local training limitation

```text
TRAINING_NOT_VERIFIED
```

The following observations are insufficient to upgrade this classification:

- CUDA is available;
- PyTorch and LeRobot import;
- free VRAM exists;
- a bounded or synthetic CUDA allocation could succeed;
- SmolVLA configuration code can import or instantiate.

Model-specific peak memory, optimizer state, activation memory, input shape,
batching, precision, and checkpoint behavior have not been established by an
authorized task. No training duration or feasible local configuration is
claimed.

## Training execution mode and primary resource

```text
Execution mode: UNRESOLVED
Primary resource: UNRESOLVED
Compatibility: NOT_VERIFIED
```

Local-only execution cannot be selected while local training remains
`TRAINING_NOT_VERIFIED`. `REMOTE_TRAINING` or `HYBRID_TRAINING` also cannot be
selected because there is no evidenced approved GPU resource, access/quota,
resource class, runtime compatibility, or budget. No cloud account or instance
was created or contacted.

For any future READY result, the verifier requires a non-placeholder resource
identity, provider/owner, resource class, positive VRAM value, availability and
compatibility evidence, allowed provenance, and source references. Local mode
additionally requires authorized model-specific evidence, a configuration
reference, and evidenced peak VRAM within the measured local capacity.

Execution roles are exact mode material: HYBRID requires local
development/configuration/validation-only and remote-primary-training roles;
REMOTE and LOCAL use their corresponding explicit role pair. Missing or
placeholder role/identity text fails closed.

A READY primary must be classified as `NVIDIA_CUDA_GPU`, identify the selected
workload/configuration, state its evidenced required VRAM and available VRAM,
and prove `available >= required`. A merely positive VRAM number is not a
compute-sufficiency result.

The intended division, once explicitly approved, is likely to keep local work
bounded to development/configuration/validation and execute fine-tuning on a
separately evidenced resource. That is a planning direction, not a selected
resource.

## Storage strategy and readiness

Planned locations are documented but not created:

| Artifact | Planned path | Size evidence |
|---|---|---|
| Hugging Face/model cache | `/home/jinho/.cache/huggingface` | `NOT_VERIFIED` |
| Future VLA datasets | `data/vla/` | `NOT_VERIFIED`; Dataset V1 does not exist |
| Future checkpoints | `results/vla/checkpoints/` | `NOT_VERIFIED` |

The relevant filesystem has substantial measured free capacity, but future
dataset, model-cache, checkpoint, and temporary-artifact sizes are undefined.
Free bytes alone cannot prove fit. Therefore:

```text
Storage readiness: STORAGE_NOT_VERIFIED
```

A later authorized task must calculate required bytes from actual model,
dataset, checkpoint-retention, and temporary-space inputs before writing large
artifacts. It must stop before execution if available capacity is below that
derived requirement.

For READY, the verifier recomputes exactly:

```text
required_capacity_bytes = dataset_size_bytes + checkpoint_size_bytes
                        + model_cache_size_bytes + temporary_space_bytes
```

Each component requires its own source/provenance. A reported aggregate smaller
than its components, or an aggregate larger than available capacity, fails C11.

## Budget policy and feasibility

```text
Budget policy: UNRESOLVED
Budget feasibility: NOT_VERIFIED
Cost calculation performed: false
```

No currency, unit price, expected training duration, estimated dataset size,
approved numeric ceiling, prepaid resource, or GPU quota was supplied. None is
invented. Consequently no compute-cost estimate can be calculated.

For a future numeric policy, the verifier accepts only finite non-negative
inputs with source references and independently recomputes, without implicit
rounding:

```text
estimated_compute_cost = unit_price * estimated_training_hours
```

For a prepaid policy, a concrete resource reference and positive evidenced
remaining quota are mandatory. Neither policy can pass through a boolean-only
availability assertion. Numeric and prepaid policies must identify the same
primary resource to which the cost/quota evidence applies.
Prepaid feasibility additionally requires an evidenced required usage in the
same unit and verifies `remaining_quota >= required_quota`; positive-but-
insufficient quota cannot be `WITHIN_POLICY`.
Because this task performs no training, an estimated training duration cannot
use `MEASURED`; it must remain `DECLARED_INPUT` or `DOCUMENTED`, and the
computed cost alone uses `DERIVED`.

## Fallback strategy

There is no evidenced fallback compute resource. The mandatory fallback check
therefore remains blocked.

The fail-closed operational rule is:

```text
If the primary path is absent, unavailable, incompatible, over budget, or out
of storage, do not train. Obtain explicit resource and budget approval, record
the associated provenance, and rerun P0-007 before downstream authorization.
```

This stop/escalation policy does not count as an available fallback GPU.
No TASK-defined redundancy rule currently proves a separate fallback
unnecessary, so every READY result requires a concrete, compatible, evidenced
fallback resource.
The fallback resource identity must differ from the primary resource identity;
renaming the primary as its own fallback does not establish recovery capacity.
The fallback must independently satisfy CUDA GPU kind, workload VRAM capacity,
runtime compatibility, storage-movement, and a policy-specific budget predicate
applied to the fallback resource.

## Reproduction strategy

The future authorized environment must retain the accepted P0-005 direct
baseline unless an explicit dependency-migration task changes it:

```text
Python       3.12.3
LeRobot      0.4.4
PyTorch      2.10.0+cu130
torchvision  0.25.0+cu130
isolation    uv virtual environment
```

Reconstruction must use the accepted P0-005 command/pins, compare the resolved
package snapshot, clear ambient `PYTHONPATH` for evidence runs, and record the
Git revision, dataset manifest/version, training configuration, model version,
environment snapshot, and artifact hashes. A remote candidate must demonstrate
compatible NVIDIA/CUDA/PyTorch execution before it becomes the primary path.

## Mandatory readiness blockers

The canonical result retains these failed mandatory dimensions:

- `C08` training execution mode selected;
- `C09` primary training resource identified;
- `C10` software/runtime compatibility documented for that primary resource;
- `C11` storage requirements and artifact-movement strategy sufficiently verified;
- `C12` budget policy defined;
- `C14` primary-path budget feasibility classified;
- `C15` fallback compute strategy defined.

The verifier independently derives this list from the underlying mode,
resource, storage, budget, cost, and fallback fields. It rejects any artifact
whose blocker list differs, whose mandatory flag is demoted, whose material
fields use insufficient provenance, or whose aggregate decision is manipulated
to `TRAINING_RESOURCE_READY`, even when the manipulated payload is rehashed.
Every PASS check must itself carry sufficient provenance; `NOT_VERIFIED` cannot
be paired with PASS.
No-training fields are explicit: missing runtime/generation training,
optimizer-update, or hyperparameter-search fields fail C18 rather than defaulting
to false. JSON reads, content hashes, executable discovery, path metadata,
resource metadata, and subprocess probes all run behind explicit timeouts.

## Explicitly unverified and deferred

- local SmolVLA training fit, peak memory, duration, and performance;
- external compute availability, quota, resource class, compatibility, and price;
- approved budget ceiling or prepaid resource;
- Dataset V1/model/checkpoint sizes;
- physical robot/camera readiness, still `DEVICE_IO_BLOCKED`;
- all training, evaluation, Dataset V1, teleoperation, integration, P0-006R,
  P0-004R, and Week 1 execution.
