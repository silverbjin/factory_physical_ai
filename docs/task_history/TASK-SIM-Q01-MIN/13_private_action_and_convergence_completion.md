# Private Action Discovery and Convergence Completion — TASK-SIM-Q01-MIN

## 1. Trigger

Task 2 previously stopped at:

```text
PRIVATE_ACTION
SIM009_PRIVATE_ACTION_CLIENT_UNAVAILABLE
```

The shared Gazebo/Nav2 session was otherwise ready, and the ROS CLI could
observe `/navigate_to_pose [nav2_msgs/action/NavigateToPose]`.

## 2. Existing Shared Runtime State

The inherited shared session already established, in one fresh isolated run:

```text
launch                 PASS
/clock                 PASS
odom -> base_link      PASS
map_server / AMCL      PASS
canonical initial pose PASS
map -> odom            PASS
/navigate_to_pose      PASS
owned cleanup          PASS
```

No SIM-008 localization, launch, or process-cleanup behavior was changed by
this transition except through the already-approved shared session boundary.

## 3. Private rclpy Context Construction

The live discovery matrix established the concrete interpreter boundary:

| Control | Result |
| --- | --- |
| ROS CLI with immutable runtime environment | action visible |
| Q01 venv Python `import rclpy` | `ModuleNotFoundError` |
| venv after adding ROS package path | failed to load `librcl_action.so` |
| `/usr/bin/python3` started with immutable ROS runtime environment | explicit `rclpy.Context` initialized in the runtime domain and discovered the action |

The cause was not a domain or action-name mismatch. The Q01 venv process was
already running before the runtime materialized ROS `PYTHONPATH` and dynamic
loader paths; therefore it could not load Jazzy's Python extension.

The correction adds `scripts/sim009_private_action_worker.py`, an owned child
started with the immutable `NavigationRuntimeContext.environment`. It creates:

```text
rclpy.Context(domain_id=runtime context ROS_DOMAIN_ID)
  -> sim009_goal_tracker node(context=same context)
  -> NavigateToPose ActionClient(/navigate_to_pose)
  -> explicit SingleThreadedExecutor(context=same context)
```

The worker uses no parent `ROS_DOMAIN_ID` mutation and no default-context
production path. The executor is explicit: the first worker attempt exposed
that `rclpy.spin_until_future_complete()` selected the global executor, whose
context was absent; the worker now uses its context-bound executor.

## 4. CLI vs rclpy Discovery Matrix

The successful bounded control used runtime domain `8` and produced:

```json
{"domain": 8, "wait": true}
```

The updated Task-2 live gate then produced:

```json
{"ready": true, "stage": "READY", "error": null}
```

with `sim009_private_action_client: true` and bounded owned cleanup.

## 5. Root Cause

Primary class: `SIM009_RCLPY_CONTEXT_PROPAGATION_DEFECT`.

First failing invariant: the private client had to join the immutable runtime
domain without relying on the Q01 venv's ambient Python/loader configuration.

The effective Nav2 server and CLI used the immutable runtime environment. The
original private client ran in the already-started MuJoCo/Q01 venv and could
not import/load ROS Jazzy rclpy; its broad `ImportError` handler converted that
concrete dependency failure into an action-unavailable Boolean.

## 6. Task-2 Correction

Modified:

- `scripts/sim009_goal_tracked_navigation.py`
  - runtime-owned `PrivateActionWorker`
  - explicit JSON request/reconcile protocol
  - no process-global ROS-domain mutation
- `scripts/sim009_private_action_worker.py`
  - explicit rclpy Context and context-bound executor
- `tests/test_simulation_failure_recovery.py`
  - immutable environment, worker protocol, and same-goal reconciliation tests

The worker retains a pending action only for same-goal reconciliation. It is
closed before the shared Gazebo/Nav2 runtime cleanup.

## 7. Task-2 Live Gate

Exact execution path:

```text
GoalTrackedGazeboNav2Runtime.establish_readiness()
```

Result:

```text
launch                 PASS
clock                  PASS
odom                   PASS
localization           PASS
base action readiness  PASS
private action client  PASS
cleanup                PASS
```

`TASK2_SHARED_NAVIGATION_SESSION = PASS`.

## 8. Task-3 Identity Lifecycle

`run_failure_suite()` now allocates one `qualification_run_id` and one
`scenario_execution_id` per scenario before runtime startup. A pre-request
failure carries those two identifiers and its readiness stage/error, but has no
fabricated mission/request/trace/action correlation.

Live blocked-navigation control passed through a real Nav2 request and
returned a same-goal UUID, terminal status `6`, and same-run mission, request,
trace, and action identifiers. `SAME_RUN_CORRELATION = PASS` for that control.

## 9. Task-4 Single Supplier Execution

`collect_qualification_subjects()` now caches one result per task supplier.
SIM-008 is invoked once; the SIM-009 suite is invoked once and its explicitly
keyed scenario mapping routes the ten MIN-Q01 subject IDs. Missing suppliers or
missing scenario rows now fail closed rather than being silently skipped.

Controlled routing test result: `sim008_supplier_calls=1`,
`sim009_supplier_calls=1`, `11` routed templates.

## 10. Focused Tests

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
112 passed in 3.48s
UNIT_PASS
SCENARIO_COVERAGE_PASS (controlled coverage)
```

All touched modules compiled and `git diff --check` passed before the live
gate. No controlled test result was treated as canonical Evidence.

## 11. GATE-1 STATIC_PROVENANCE

Controlled immutable resolver/routing checks passed (`2 passed`). The existing
accepted-commit → Git blob → SHA → task/result validation path remains the
only accepted binding authority.

Status: `PASS`

## 12. GATE-2 RUNTIME_ENVIRONMENT

The immutable-context tests passed: distinct contexts have distinct bounds,
ROS domains, partitions, and environment maps without parent environment or
timeout-global mutation. The private worker inherited the exact context
environment rather than ambient parent environment.

Status: `PASS`

## 13. GATE-3 SIM008_RUNTIME

A fresh post-convergence live SIM-008 adapter run returned:

```text
qualification run: q01-sim008-normal-system-authority
correlation: mission/request/trace present
structured Gazebo time: 40.71 seconds
semantic result: success/completed
cleanup: true
```

Status: `PASS` (`LIVE_RUNTIME_PASS`)

## 14. GATE-4 SIM009_NAVIGATION_RUNTIME

One fresh suite used the shared ready runtime and private client. It returned:

| Scenario | Real request lifecycle | Result |
| --- | --- | --- |
| `SIM009-NAV-BLOCKED` | yes | PASS |
| `SIM009-NAV-ABORTED` | yes | BLOCKED |
| `SIM009-NAV-TIMEOUT-RETRY` | yes | BLOCKED |
| `SIM009-NAV-TF-UNAVAILABLE` | yes | BLOCKED |

The suite result was `SIM_FAILURE_SUITE_BLOCKED`; all rows were within budget
and cleanup was true. The first failed scenario was
`SIM009-NAV-ABORTED`: `scenario_local_provenance` did not meet its accepted
semantic validator after the worker bridge. In particular, the worker path
captures the server-log window after executing the goal, so it cannot attest
goal-local abort log bytes required by the existing accepted semantic check.

Status: `BLOCKED`

This is not a readiness, correlation, accepted-binding, or scope failure. The
approved stop rule prohibits proceeding to GATE-5, canonical preflight, or
repeatability while the real navigation semantic gate is blocked.

## 15. GATE-5 SAME_RUN_CORRELATION

The single blocked-navigation live control passed same-run correlation, but the
gate across every required NAV scenario was not declared because GATE-4 failed.

Status: `BLOCKED_BY_GATE_4`

## 16. GATE-6 CANONICAL_11_SUBJECT

Not run. Canonical preflight must not be used to debug the failed earlier
semantic navigation gate.

Status: `BLOCKED_BY_GATE_4`

## 17. GATE-7 REPEATABILITY

Not run because GATE-6 was not reached.

Status: `BLOCKED_BY_GATE_4`

## 18. Protected Scope Verification

Unchanged by this transition:

- accepted SIM-004, SIM-005, SIM-006, SIM-007, SIM-008, and SIM-009
  Acceptance/Evidence;
- protected dirty `results/simulation/SIM-004_navigation_backend.json`;
- `tasks/TASK-SIM-Q01-MIN.md` and frozen MIN-Q01 scope;
- frozen SIM-010 implementation/state.

No orchestrator command, global process kill, source-history rewrite, accepted
artifact write, synthetic simulator time, or synthetic request identity was
used.

## 19. Final State

`NOT_READY_FOR_ORCHESTRATOR_RESUME`

Task 2, Task 3, and Task 4 completed their bounded implementation gates. The
convergence cannot be declared complete because GATE-4 is blocked by the first
post-worker SIM-009 semantic-provenance invariant.

## 20. Next Action

Perform one bounded SIM-009 worker semantic-provenance diagnosis. It must prove
how a private action worker can capture a pre-goal server-log boundary and
preserve the accepted abort/TF/timeout semantics without changing accepted
SIM-009 behavior or weakening its validators. Do not proceed to canonical
preflight until all four NAV rows pass GATE-4.
