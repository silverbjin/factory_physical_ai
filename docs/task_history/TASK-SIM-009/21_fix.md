# Fix — TASK-SIM-009

- Result: `BLOCKED`
- Based on Diagnosis: `19_diagnosis.md`, `20_diagnosis.md`

## Root cause

- Cumulative process-log tails and global attempt counters were exposed as scenario-local Evidence.
- A newly constructed SIM-009 private rclpy `ActionClient` could lag the accepted bootstrap's external action-list readiness signal.

## Correction

- Added attempt-scoped byte-offset server-log windows with fail-closed attribution.
- Derived L1-NAV `runtime_calls` and logical side-effect counts from `scenario_execution_id`-filtered attempts.
- Added a bounded SIM-009 private ActionClient preflight after accepted bootstrap.

## Files modified

- `scripts/sim009_goal_tracked_navigation.py`
- `src/simulation_runtime/failure_recovery.py`
- `tests/test_simulation_failure_recovery.py`
- `results/simulation/SIM-009_failure_recovery.json`
- `results/simulation/SIM-009_failure_recovery_run1.json`
- `results/simulation/SIM-009_failure_recovery_run2.json`

## Regression

- focused pytest: `76 passed`
- `git diff --check`: `PASS`
- SIM-004/SIM-005/SIM-006/SIM-008 accepted Evidence SHA256: `PASS`

## Runtime validation

- One live run: `SIM_FAILURE_SUITE_READY`; attempt logs were scenario-local and L1-NAV `runtime_calls` were `1 / 1 / 2 / 1`.
- Subsequent runs exposed intermittent accepted bootstrap/readiness failures before scenario dispatch; the final run reported `live_runtime_ready=false` and `runtime_calls=0` for every L1-NAV row.

## Remaining blocker

The accepted `BoundedGazeboNav2Runtime.bootstrap_localization()` startup/readiness boundary is intermittent in the current environment. The latest blocked run never reached SIM-009 fault dispatch or log-window logic.

## Next

`READ_ONLY_RUNTIME_READINESS_DIAGNOSIS`
