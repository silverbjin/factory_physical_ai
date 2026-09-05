# VLA Training Resource Risks after TASK-P0-007

> Assessment date: 2026-09-05
>
> Resource outcome: `TRAINING_RESOURCE_BLOCKED`
>
> Evidence: `results/phase0/P0-007_training_resource_readiness.json`

Allowed dispositions are `RESOLVED`, `DEFERRED`, `BLOCKING`, and
`OUT_OF_SCOPE`.

| ID | Description | Evidence / provenance | Impact | Disposition | Future owner / task |
|---|---|---|---|---|---|
| `VLA-TR-R01` | Local SmolVLA training fit in 6 GiB is unknown. | CUDA/runtime metadata is `MEASURED`; model-specific training evidence is `NOT_VERIFIED`. | Local-only training cannot be selected. | `BLOCKING` | compute owner / later explicitly authorized capacity or training task |
| `VLA-TR-R02` | No external primary compute resource, access, or quota is evidenced. | No declared or measured external resource exists (`NOT_VERIFIED`). | `REMOTE_TRAINING` and `HYBRID_TRAINING` cannot be selected. | `BLOCKING` | project/compute owner |
| `VLA-TR-R03` | Budget policy and ceiling/prepaid status are absent. | Policy `UNRESOLVED`; no numeric inputs (`NOT_VERIFIED`). | Cost feasibility cannot be established. | `BLOCKING` | project owner |
| `VLA-TR-R04` | No available fallback compute resource is evidenced. | Stop/escalation policy is `DOCUMENTED`, fallback availability is `NOT_VERIFIED`. | Primary failure cannot transfer to another approved resource. | `BLOCKING` | project/compute owner |
| `VLA-TR-R05` | Dataset/model/checkpoint/temp storage requirements are unknown. | Filesystem capacity is `MEASURED`; all future artifact sizes are `NOT_VERIFIED`. | Free disk cannot be interpreted as proof of storage fit. | `BLOCKING` | later authorized VLA data/training task |
| `VLA-TR-R06` | Accepted environment lives under the P0-005 worktree path. | Path and 6,198,765,955-byte footprint are `MEASURED`; baseline is `DOCUMENTED`. | Reproduction on another worktree/host must be explicit and snapshot-checked. | `DEFERRED` | selected compute-path owner |
| `VLA-TR-R07` | Compatible transitive packages may drift on reconstruction. | P0-005 direct pins/snapshot are `DOCUMENTED`; no upgrade occurred. | Remote/local recreation could differ. | `DEFERRED` | later environment owner |
| `VLA-TR-R08` | P0-006 physical I/O remains blocked. | `DEVICE_IO_BLOCKED`, accepted artifact hash bound by P0-007 (`DOCUMENTED`). | Physical data collection/teleoperation remains unavailable. | `OUT_OF_SCOPE` | `TASK-P0-006R` |
| `VLA-TR-R09` | A readiness implementation could be confused with authorization to train. | `task_w1_001_authorized=false`, `p0_004r_required=true`; no training/procurement flags are false. | Premature Dataset/training work could bypass Phase 0. | `RESOLVED` | verifier invariant / `TASK-P0-004R` |
| `VLA-TR-R10` | Evidence could be manipulated by coordinated edits to material fields, checks, blockers, decision, and payload hash. | Verifier v1.3 additionally recomputes workload VRAM fit, storage component totals, prepaid required usage, fallback compute/storage/budget material, requires explicit no-training fields, and bounds JSON/hash/executable discovery; rehashed regressions pass. | False `TRAINING_RESOURCE_READY` could be emitted. | `RESOLVED` | P0-007 verifier/tests; retain as regression invariant |

## Exit signals for blocking risks

- `R01`: authorized model-specific evidence supports a local classification,
  or an evidenced external primary path makes local fit unnecessary.
- `R02`: a concrete resource, access/quota, resource facts, and runtime
  compatibility have allowed provenance.
- `R03`: one allowed non-`UNRESOLVED` budget policy is approved and primary
  feasibility is `WITHIN_POLICY`.
- `R04`: an available, compatible, policy-compliant fallback compute path is
  evidenced.
- `R05`: requirements are derived from actual selected model/data/checkpoint
  inputs and fit within measured free capacity.

All exit signals require a verifier rerun. They do not themselves authorize
training; `TASK-P0-004R` remains required.
