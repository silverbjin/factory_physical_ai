# Diagnosis — TASK-SIM-009

- Status: RESOLVED
- Disposition: `INFRASTRUCTURE_GATE_PLUS_SEMANTIC_REPEATABILITY`

## Trigger

Later repeatability attempts failed in `GoalTrackedGazeboNav2Runtime.start() → bootstrap_localization()` before L1-NAV dispatch, producing `live_runtime_ready=false` and `runtime_calls=0`.

## Primary fault domain

`VALIDATION_OWNERSHIP_DEFECT`

## Repeatability ownership

`TASK-SIM-009` owns semantic repeatability: distinct BLOCKED/ABORTED/TIMEOUT-RETRY/TF-UNAVAILABLE outcomes, scenario-local Evidence, identities, bounded recovery, and logical side-effect invariants. It consumes SIM-004 as the accepted Gazebo/Nav2 backend boundary.

`TASK-SIM-004` acceptance proves its specified bounded Navigation backend behavior and cleanup, not that every independent cold Gazebo/ROS/AMCL/TF/Nav2 bootstrap succeeds deterministically on every attempt. TASK-SIM-009 does not explicitly require cold-bootstrap reliability characterization.

## Infrastructure failure semantics

A cold bootstrap failure is `INFRASTRUCTURE_NOT_READY`, not a SIM-009 semantic repeatability failure. The canonical task result remains `SIM_FAILURE_SUITE_BLOCKED` for a run that cannot dispatch the required live scenarios; semantic comparison must not treat its absent scenario Evidence as a failed fault class.

## Cold-start requirement

For strong isolation, semantic run1/run2 retain independent cold runtime startup and shutdown. Infrastructure gate status is recorded separately for each run. Reusing one validated runtime for both suites is not authorized because it weakens independent Evidence.

## Observability finding

`BoundedGazeboNav2Runtime.bootstrap_localization()` already records probe/process measurements, but `run_failure_suite()` collapses startup exceptions and failed probe details to `live_runtime_ready=false`. This is an `OBSERVABILITY_GAP` in the SIM-009-owned validation harness; accepted SIM-004 launch/bootstrap code need not change.

## Bounded retry policy

Existing SIM-004 startup and localization probes are bounded. SIM-009 may add a bounded, explicitly recorded infrastructure readiness gate for independent cold attempts, but must not use arbitrary sleeps, extend semantic scenario budgets, or relabel a failed bootstrap as semantic success.

## Authorized Fix scope

- `src/simulation_runtime/failure_recovery.py`
- `scripts/run_simulation_failure_recovery.py`
- `tests/test_simulation_failure_recovery.py`
- SIM-009-owned repeatability Evidence generation artifacts

## Protected predecessor scope

- `src/simulation_runtime/navigation_backend.py`
- `scripts/run_simulation_navigation.py`
- `src/simulation_runtime/normal_system_e2e.py`
- `scripts/run_simulation_normal_system_e2e.py`

## Next action

`AUTONOMOUS_FIX_VALIDATE`
