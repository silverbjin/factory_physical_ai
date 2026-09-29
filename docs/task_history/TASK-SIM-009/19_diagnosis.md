# Diagnosis — TASK-SIM-009

- Status: RESOLVED
- Disposition: `SIM009-REREV-001` scenario-local Evidence attribution defect

## Trigger

`18_review.md` independent re-review rejected TASK-SIM-009 because later L1-NAV rows reused cumulative server-log tails and cumulative `runtime_calls`.

## Observed evidence

- `GoalTrackedGazeboNav2Runtime._server_log_tail()` reads the final 4000 bytes of each shared process log and attaches that value to every later `GoalAttemptRecord`.
- `failure_recovery._navigation_scenario()` derives `runtime_calls` and TIMEOUT `logical_side_effect_count` from global `goal_attempts`.

## Failing boundary

`scripts/sim009_goal_tracked_navigation.py::GoalTrackedGazeboNav2Runtime._server_log_tail` and `src/simulation_runtime/failure_recovery.py::_navigation_scenario`.

## Root cause

Cumulative process-log tail and global runtime call counter were incorrectly exposed as scenario-local Evidence.

## Rejected hypotheses

- Accepted SIM-004 process launch/logging boundary is not the cause: SIM-009 inherits it without changing process ownership or log paths.
- Fault routing/injection and scenario execution identity are not the cause: attempts already carry and filter by `scenario_execution_id`.

## Authorized Fix scope

- `scripts/sim009_goal_tracked_navigation.py`
- `src/simulation_runtime/failure_recovery.py`
- `tests/test_simulation_failure_recovery.py`

## Protected scope

- `src/simulation_runtime/navigation_backend.py`
- `scripts/run_simulation_navigation.py`
- `src/simulation_runtime/normal_system_e2e.py`
- `scripts/run_simulation_normal_system_e2e.py`

## Next action

`IMPLEMENT_RESOLVED_FIX`
