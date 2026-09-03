# Robot / Camera / Device I/O Risks after TASK-P0-006

> Verification date: 2026-09-03
>
> Device I/O decision: **DEVICE_IO_BLOCKED**
>
> Source evidence: `results/phase0/P0-006_robot_io_readiness.json`
>
> `TASK-W1-001 authorized: false`; `TASK-P0-004R required: true`.

| ID | Description | Evidence | Impact | Disposition | Owner / future task |
|---|---|---|---|---|---|
| DEV-IO-R01 | Final robot/manipulator target is not selected. | C01 `BLOCKED`; target `NOT_VERIFIED` | Stable device, interface, and safety claims cannot be tied to a physical target. | `BLOCKING` | Hardware owner; resolve before `TASK-P0-004R` |
| DEV-IO-R02 | Robot/controller discovery, stable identity, and host access are unresolved. | C02-C04 `NOT_VERIFIED`; bounded `/dev` enumeration found no robot/stable serial candidates. | Later state/control adapters cannot be reproduced safely. | `BLOCKING` | Hardware owner; native robot/edge host verification |
| DEV-IO-R03 | Concrete state-feedback path and safe non-motion observation are absent. | C05 `BLOCKED`; C06 `NOT_VERIFIED` | Robot state cannot support later supervised operation or verification. | `BLOCKING` | Robot integration owner; resolve before `TASK-P0-004R` |
| DEV-IO-R04 | Future actuator and gripper paths are unidentified. | C07-C08 `BLOCKED`; neither path was invoked. | Later typed control integration has no reviewed interface boundary. | `BLOCKING` | Robot integration owner; interface discovery only until separately authorized |
| DEV-IO-R05 | Camera identity, stable path, configuration, and frame acquisition are unresolved. | C09 `BLOCKED`; C10-C12 `NOT_VERIFIED`; no video candidate enumerated. | Image observations and future dataset capture cannot proceed. | `BLOCKING` | Perception/hardware owner; bounded native-host camera check |
| DEV-IO-R06 | Target-specific workspace, limits, prohibited zones, pose assumptions, and gripper constraints are missing. | C13 `BLOCKED` | A later motion task cannot establish deterministic safety bounds. | `BLOCKING` | Safety operator / hardware owner |
| DEV-IO-R07 | Manual abort/E-stop strategy is unresolved and untested. | C14 `BLOCKED`; classification `NOT_VERIFIED`; `functionally_tested_under_motion=false` | No authorized stop plan exists for a later supervised motion test. | `BLOCKING` | Safety operator; later explicitly authorized safety verification |
| DEV-IO-R08 | Supervised teleoperation prerequisites are incomplete. | C15 `BLOCKED`, derived from C01-C14 | `TASK-W1-002` cannot safely begin physical teleoperation. | `BLOCKING` | VLA data owner after Phase 0 authorization |
| DEV-IO-R09 | Device discovery or frame/state probes could otherwise hang. | Fixed `/dev` patterns use a 5 s child-process bound; state uses 2 s; camera uses 5 s/1 frame in the canonical run; timeout tests PASS. | A diagnostic could leak or block the readiness workflow. | `RESOLVED` | Maintainer; keep bounds and timeout regression tests |
| DEV-IO-R10 | Physical teleoperation implementation is not part of this task. | Explicit scope and safety flags | Must not be mistaken for a completed prerequisite implementation. | `DEFERRED` | `TASK-W1-002`, only after authorization |
| DEV-IO-R11 | Dataset V1 and episode recording were not started. | C17 `PASS`; safety flags false | No physical dataset readiness claim exists. | `DEFERRED` | `TASK-W1-003`, only after authorization |
| DEV-IO-R12 | SmolVLA loading/inference and training/fine-tuning were not run. | C17 `PASS`; model/dataset safety flags false | Model/device compatibility and training capacity remain unknown. | `OUT_OF_SCOPE` | `TASK-P0-007` and later authorized VLA tasks |
| DEV-IO-R13 | ROS/VLA and Agent integration were not started. | C17 `PASS`; integration safety flag false | No integrated physical execution path is established. | `OUT_OF_SCOPE` | Later authorized integration tasks |
| DEV-IO-R14 | Final Phase 0 readiness decision is not owned by P0-006. | `p0_004r_required=true` | A correct P0-006 implementation cannot authorize Week 1. | `DEFERRED` | `TASK-P0-004R` |

## Readiness stop rule

Keep the aggregate decision `DEVICE_IO_BLOCKED` while any `BLOCKING` row remains
unresolved. Do not reclassify declared, derived, documented, or unverified facts
as `MEASURED`. Do not execute a vendor/device operation whose physical side
effect is uncertain. Implementation completion for `TASK-P0-006` does not
change these blockers and does not authorize `TASK-W1-001`.
