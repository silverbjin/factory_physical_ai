# VLA Training Compute / Budget Plan

> Task: `TASK-P0-007`
>
> Status: readiness plan complete; resource outcome `TRAINING_RESOURCE_BLOCKED`
>
> Evidence: `results/phase0/P0-007_training_resource_readiness.json`

## Decision summary

| Decision | Value | Provenance |
|---|---|---|
| Local training classification | `TRAINING_NOT_VERIFIED` | `DERIVED` |
| Execution mode | `UNRESOLVED` | `NOT_VERIFIED` |
| Primary resource | `UNRESOLVED` | `NOT_VERIFIED` |
| Storage readiness | `STORAGE_NOT_VERIFIED` | `DOCUMENTED` + measured filesystem capacity |
| Budget policy | `UNRESOLVED` | `NOT_VERIFIED` |
| Budget feasibility | `NOT_VERIFIED` | `NOT_VERIFIED` |
| Fallback compute | `NOT_VERIFIED` | `NOT_VERIFIED` |
| Overall outcome | `TRAINING_RESOURCE_BLOCKED` | `DERIVED` |

No training or procurement is authorized by this plan.

## Primary compute resource

No primary training resource is selected.

The local RTX 2060 Max-Q 6 GiB host remains a development/configuration and
bounded validation resource only. CUDA/runtime visibility is measured, but
SmolVLA training fit is `TRAINING_NOT_VERIFIED`. No external GPU resource,
account access, quota, or availability has been evidenced.

Before selecting `REMOTE_TRAINING` or `HYBRID_TRAINING`, the compute owner must
provide all of the following with allowed provenance:

1. concrete resource/provider or organizational host identity;
2. availability/access and quota evidence;
3. GPU/resource class and usable VRAM;
   required VRAM for the selected workload/configuration, with
   `available_vram_bytes >= required_vram_bytes`;
4. compatibility with the accepted Python/LeRobot/PyTorch strategy;
5. data/model/checkpoint transfer method;
6. environment reconstruction and source revision method;
7. approved budget policy and feasibility classification.

The task does not prescribe or invent a GPU class or VRAM requirement because
the model-specific training configuration has not been established.

## Runtime requirements

The selected path must retain or explicitly migrate, through a separately
authorized decision, this accepted baseline:

```text
Python       3.12.3
LeRobot      0.4.4
PyTorch      2.10.0+cu130
torchvision  0.25.0+cu130
```

The baseline is reconstructed in an isolated `uv` environment. The later
training run must record the resolver/package snapshot, source Git revision,
training config, dataset version, model/checkpoint hashes, and relevant cache
locations. P0-007 performs no dependency installation or upgrade.

## Storage plan

| Purpose | Planned location | Current status | Required future check |
|---|---|---|---|
| VLA environment | `/home/jinho/projects/factory_physical_ai_p0_005/.venv-vla` | `MEASURED`; about 6.20 GB package footprint | Recreate or relocate explicitly for the selected compute host |
| Model/HF cache | `/home/jinho/.cache/huggingface` | `DOCUMENTED`; not created by P0-007 | Derive cache requirement from selected model artifacts |
| Dataset | `data/vla/` | planned only | Measure Dataset V1 after its separately authorized creation |
| Checkpoints | `results/vla/checkpoints/` | planned only | Define checkpoint count/retention and temporary-space factor |

The repository filesystem capacity is measured by each verifier run. Storage
cannot move beyond `STORAGE_NOT_VERIFIED` until model, dataset, checkpoint, and
temporary-space requirements are evidenced. Planned paths do not imply that
Dataset V1 or checkpoints exist.

READY storage uses the exact, independently recomputed relationship:

```text
required = dataset + checkpoints + model cache + temporary space
available >= required
```

All components retain distinct provenance; no dataset size is inferred by this
task.

## Budget policy

```text
UNRESOLVED
```

None of these required policy inputs is available:

- approved numeric ceiling and currency;
- verified zero-incremental-cost local training feasibility;
- identified existing prepaid resource;
- approved resource unit price;
- authorized training-duration assumption;
- contingency policy.

Accordingly:

```text
Cost calculation performed: false
Estimated cost: NOT_VERIFIED
Budget feasibility: NOT_VERIFIED
```

No cloud price, duration, dataset size, ceiling, quota, or availability is
assumed. If a later owner chooses `APPROVED_NUMERIC_BUDGET_CEILING`, every
numeric input must carry provenance, and `estimated_compute_cost` must be
independently recomputed as `unit_price * estimated_training_hours` using exact
decimal arithmetic with no implicit rounding. NaN, infinity, negative,
malformed, missing, or arithmetically inconsistent values fail closed. A result
exactly at the approved ceiling is `WITHIN_POLICY`; a result above it is
`OUTSIDE_POLICY` and stops execution.

`EXISTING_PREPAID_RESOURCE` additionally requires a concrete prepaid resource
identifier/reference plus positive remaining quota, unit, provenance, and
source. `LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET` is valid only for an independently
verified `LOCAL_TRAINING` path. A policy name or availability boolean alone is
never sufficient. Numeric or prepaid evidence must name the selected primary
resource through `applies_to_resource_id`; an entitlement or price for a
different resource cannot establish primary-path feasibility.
Prepaid feasibility requires both remaining and required usage with the same
unit and independently checks `remaining_quota >= required_quota`. It cannot
carry contradictory numeric-cost fields while claiming no cost calculation.
P0-007 cannot produce a measured training-duration input because it executes no
training. Such an estimate must be `DECLARED_INPUT` or `DOCUMENTED`; only the
formula result is `DERIVED`.

## Fallback and stop conditions

No fallback compute resource is currently available or verified. The fallback
check is therefore `BLOCKED`, even though the stop/escalation rule is defined.

Training must not start when any of these conditions holds:

- execution mode or primary resource is unresolved;
- resource availability/quota is not verified;
- runtime compatibility is not verified;
- local training fit would rely on CUDA/import/free-VRAM/config evidence alone;
- storage required bytes are not derived or exceed free capacity;
- budget policy is unresolved;
- estimated cost is missing, malformed, or outside policy;
- fallback is required but unavailable;
- P0-004R has not authorized the downstream task.

On any stop condition, the owner must obtain explicit approval/evidence and
rerun the readiness verifier. The plan may never switch provider, resource, or
budget silently.

A fallback must identify its strategy, resource, provider/owner,
resource class, availability, runtime compatibility, provenance, and sources.
This TASK defines no independently demonstrable redundancy exemption, so an
empty fallback or a `fallback.required=false` assertion fails READY.
The fallback resource ID must also be distinct from the primary resource ID.
It must identify an NVIDIA CUDA GPU, prove available VRAM against the same
workload requirement, reference the storage/artifact movement strategy, and
pass a numeric or prepaid budget predicate applied to that fallback resource.

## Approval dependencies and future ownership

| Item | Current state | Owner / future task |
|---|---|---|
| External resource and quota | `NOT_VERIFIED` | project/compute owner |
| Budget policy/ceiling | `UNRESOLVED` | project owner |
| Dataset/model/checkpoint byte requirements | `NOT_VERIFIED` | later authorized VLA data/training task |
| Physical device blockers | `DEVICE_IO_BLOCKED` | `TASK-P0-006R` |
| Consolidated Phase 0 gate | required, not started | `TASK-P0-004R` |
| Week 1 authorization | `false` | `TASK-P0-004R` only |

This task does not authorize purchasing, provisioning, activating, or testing
paid resources.
