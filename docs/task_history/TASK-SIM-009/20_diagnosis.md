# Diagnosis — TASK-SIM-009

- Status: RESOLVED
- Disposition: SIM-009 rclpy ActionClient readiness preflight required

## Trigger

Scenario-local Evidence Fix validation produced intermittent `SIM_FAILURE_SUITE_BLOCKED` runs before or during L1-NAV readiness despite other full runs reaching `SIM_FAILURE_SUITE_READY`.

## Observed evidence

- A failed BLOCKED row had `live_runtime_ready=true`, `runtime_calls=0`, and `NAV2_ACTION_UNAVAILABLE`; ABORTED later in the same runtime accepted and completed a live goal.
- A minimal runtime probe observed accepted `bootstrap_localization()` failure together with false rclpy `wait_for_server` and false `map → base_link` probe.
- The failing `wait_for_server` happens before SIM-009 goal log-window capture, so it is not caused by `SIM009-REREV-001` changes.

## Failing boundary

Accepted SIM-004 bootstrap establishes external `/navigate_to_pose` availability; SIM-009 constructs its private rclpy `ActionClient` only at first scenario dispatch and immediately applies the scenario's 2-second wait.

## Root cause

The accepted bootstrap's external action-list readiness signal does not guarantee that a newly created SIM-009 rclpy `ActionClient` has completed DDS action discovery. The first scenario can therefore consume the scenario-local wait before its private client is ready, while later scenarios succeed.

## Rejected hypotheses

- Server-log offset slicing and scenario-local counters execute after action-server availability and cannot cause `runtime_calls=0`.
- Accepted predecessor process launch, ROS domain, Gazebo partition, and bootstrap implementations are unchanged.

## Authorized Fix scope

- `scripts/sim009_goal_tracked_navigation.py`
- `tests/test_simulation_failure_recovery.py`

## Protected scope

- `src/simulation_runtime/navigation_backend.py`
- `scripts/run_simulation_navigation.py`
- `src/simulation_runtime/normal_system_e2e.py`
- `scripts/run_simulation_normal_system_e2e.py`

## Next action

`IMPLEMENT_RESOLVED_FIX`
