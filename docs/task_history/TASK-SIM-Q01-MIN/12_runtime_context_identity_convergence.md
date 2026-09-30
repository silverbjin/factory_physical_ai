# Runtime Context and Identity Convergence — TASK-SIM-Q01-MIN

## 1. Approved Architecture Decision

This implementation followed `11_architecture_convergence_diagnosis.md`:

- root cause: `COMBINED_RUNTIME_CONTEXT_DEFECT`
- correction: `RUNTIME_CONTEXT_AND_IDENTITY_CONSOLIDATION_REQUIRED`
- architecture change: yes
- MIN-Q01 scope-contract change: no

The frozen scope remains one SIM-008 and ten explicitly keyed SIM-009
operations. The Full-Q01 gate was not restored.

## 2. Pre-Implementation State

The legitimate accumulated TASK-SIM-Q01-MIN changes were preserved. In
particular, the protected dirty
`results/simulation/SIM-004_navigation_backend.json` was not touched. No reset,
clean, stash, restore, staging, commit, or orchestrator command was used.

The four required focused test modules initially passed (`101 passed`).

## 3. Task 1 — Immutable Runtime Context

Implemented immutable per-instance runtime authority in
`scripts/run_simulation_navigation.py`:

- `NavigationRuntimeBounds` owns startup, localization, execution, and cleanup
  bounds.
- `NavigationRuntimeContext` owns world, initial pose, explicit ROS
  environment, fresh ROS domain, Gazebo partition, and ROS log directory.
- Environment and pose mappings are read-only.
- Launch, probes, execution, and cleanup use the same instance context.
- Parent `os.environ` is unchanged.
- SIM-008 passes instance bounds instead of mutating timeout globals.
- Launch pose and AMCL pose share one authority.

Meaningful RED covered independent bounds, cross-instance leakage, and
SIM-008 global mutation. The focused gate passed:

```text
27 passed
RUNTIME_CONTEXT_IMMUTABLE = PASS
```

## 4. Task 2 — Shared Navigation Session

Added `NavigationReadinessResult` and
`BoundedGazeboNav2Runtime.establish_readiness()` as the shared lifecycle:

```text
LAUNCH -> CLOCK -> ODOM -> LOCALIZATION -> ACTION -> READY
```

It preserves the first failed stage and exact error. `GazeboSystemWorld` and
`run_failure_suite()` now delegate to this lifecycle instead of independently
starting/bootstraping or erasing exceptions into a Boolean.

The SIM-009 private client now uses an explicit `rclpy.Context` initialized
with the immutable runtime's numeric domain ID. It no longer mutates
process-global `ROS_DOMAIN_ID`. A failed private-client preflight is preserved
as stage `PRIVATE_ACTION` and error
`SIM009_PRIVATE_ACTION_CLIENT_UNAVAILABLE`.

Controlled tests passed, but the mandatory live micro-gate blocked. The
approved stop condition therefore prevented Task 3.

## 5. Task 3 — Identity Lifecycle

Not executed. No mission/request/trace/action identity was fabricated.

Status: `BLOCKED_BY_TASK_2`

## 6. Task 4 — Single Canonical Supplier Execution

Not executed. Canonical supplier counts and suite routing were not changed.

Status: `BLOCKED_BY_TASK_2`

## 7. Static / Focused Verification

Meaningful Task-2 RED:

```text
3 failed
- NavigationReadinessResult absent (2)
- private client mutated process-global ROS_DOMAIN_ID (1)
```

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  -m pytest -q -p no:cacheprovider \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_failure_recovery.py \
  tests/test_simulation_provenance_qualification.py
```

Result:

```text
106 passed in 4.58s
UNIT_PASS
SCENARIO_COVERAGE_PASS (controlled tests only)
```

Compilation of all touched runtime/adapter/qualification modules passed.
`git diff --check` passed.

## 8. GATE-1 STATIC_PROVENANCE

Not run after the Task-2 live stop condition. Existing immutable Git authority
was not weakened or changed.

Status: `BLOCKED_BY_TASK_2`

## 9. GATE-2 RUNTIME_ENVIRONMENT

Controlled tests proved independent bounds, pose authority, environment, and
isolation IDs without parent-environment mutation. The live Task-2 context
used:

```text
ROS_DOMAIN_ID = 81
GZ_PARTITION = sim004-6d18e8c84311
```

Its launch-owned group was cleaned successfully. A post-run process-table
check found no surviving process for that domain, partition, launch, or
private client. The full standalone Gate-2 declaration was not made because
the plan stopped at Task 2.

Status: `BLOCKED_BY_TASK_2`

## 10. GATE-3 SIM008_RUNTIME

Not run after convergence changes because Task 2 did not pass. Earlier SIM-008
success cannot substitute for this post-convergence gate.

Status: `BLOCKED_BY_TASK_2`

## 11. GATE-4 SIM009_NAVIGATION_RUNTIME

Execution path:

```text
GoalTrackedGazeboNav2Runtime()
  -> establish_readiness()
  -> start()
  -> bootstrap_localization()
  -> private rclpy action-client preflight
  -> close()
```

Observed progression:

```text
launch                         PASS
structured /clock              PASS (sec=30, nanosec=729000000)
odom topic                     PASS
odom -> base_link              PASS
map_server active              PASS
amcl active                    PASS
canonical initial pose         PASS
map -> odom                    PASS
base /navigate_to_pose         PASS
private rclpy action client    BLOCKED
cleanup                        PASS
```

Structured result:

```json
{"ready": false, "stage": "PRIVATE_ACTION", "error": "SIM009_PRIVATE_ACTION_CLIENT_UNAVAILABLE"}
```

The ROS CLI in the same immutable environment observed
`/navigate_to_pose [nav2_msgs/action/NavigateToPose]`; the explicit-context
rclpy client did not discover it within five seconds. This is the first
remaining invariant. It was not mislabeled as missing correlation or generic
runtime readiness.

Status: `BLOCKED`

## 12. GATE-5 SAME_RUN_CORRELATION

Not run. No request was issued because private action readiness failed. No
synthetic or post-failure correlation was created.

Status: `BLOCKED_BY_GATE_4`

## 13. GATE-6 CANONICAL_11_SUBJECT

Not run. The approved plan prohibits using canonical preflight to debug an
earlier readiness gate.

Status: `BLOCKED_BY_GATE_4`

## 14. GATE-7 REPEATABILITY

Not run because Gate 6 was not reached.

Status: `BLOCKED_BY_GATE_4`

## 15. Modified Files and Architecture Delta

Changed by this convergence attempt:

- `scripts/run_simulation_navigation.py`: immutable context/bounds and shared
  readiness lifecycle.
- `scripts/run_simulation_normal_system_e2e.py`: SIM-008 delegation to the
  shared readiness lifecycle.
- `scripts/sim009_goal_tracked_navigation.py`: explicit rclpy context/domain
  and private-action failure classification.
- `src/simulation_runtime/failure_recovery.py`: suite delegation to shared
  readiness.
- `tests/test_simulation_navigation_backend.py`
- `tests/test_simulation_normal_system_e2e.py`
- `tests/test_simulation_failure_recovery.py`

The delta is intentionally incomplete: Task 1 completed; Task 2 has a concrete
live blocker; Tasks 3 and 4 were not started.

## 16. Protected Scope Verification

This transition did not modify accepted predecessor Acceptance/Evidence for
SIM-004, SIM-005, SIM-006, SIM-007, SIM-008, or SIM-009. It did not modify
`tasks/TASK-SIM-Q01-MIN.md`, the frozen MIN-Q01 scope, or frozen SIM-010.

The protected dirty current-worktree SIM-004 result was not restored,
rewritten, normalized, or staged. Other accumulated TASK-SIM-Q01-MIN changes
were preserved.

## 17. Remaining Risks

The exact remaining fault domain is explicit-context rclpy discovery in an
otherwise ready shared runtime. The next bounded diagnosis must establish
whether the cause is context initialization, RMW/domain propagation, discovery
timing, or another concrete private-client difference.

Correlation validation must remain unchanged, and request identities must not
exist until a real request exists.

## 18. Final State

`NOT_READY_FOR_ORCHESTRATOR_RESUME`

Task 1 passed. Task 2 is blocked at its mandatory live micro-gate. Tasks 3-4
and Gates 1-7 therefore cannot be declared complete.

## 19. Next Action

Perform one bounded diagnosis of explicit-context rclpy action discovery in
the ready shared SIM-009 runtime. Require:

```text
private action client readiness = PASS
```

Do not proceed to identity lifecycle, canonical aggregation, or orchestrator
resume until this passes.
