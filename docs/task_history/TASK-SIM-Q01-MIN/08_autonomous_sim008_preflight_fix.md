# Autonomous SIM-008 Canonical Preflight Diagnosis and Fix

## 1. Trigger

The canonical MIN-Q01 preflight was invoked with the Q01 Python interpreter
and temporary output paths.  It failed before writing either artifact:

```text
collect_qualification_subjects
  -> run_sim008_qualification
  -> ValueError: MISSING_STRUCTURED_SIMULATION_TIME
```

The adapter exception was secondary.  The first runtime invariant that failed
was the normal-system runtime's structured `/clock` observation.

## 2. Isolated Control Result

The isolated control used the same executor as the SIM-008 adapter:

```text
NormalSystemE2E(GazeboSystemWorld(load_scenario()), scenario).execute()
```

It was run with both the Q01 interpreter and the system interpreter, without
writing repository Evidence.  In the current runtime state both controls
returned `SYSTEM_E2E_FAILED` with `SIMULATION_CLOCK_UNAVAILABLE`; consequently
there was no structured simulator-time result to collect.  Cleanup of the
top-level launch process reported complete.

The current control result does not reproduce the earlier isolated PASS, so it
cannot truthfully be used as a successful live-verification claim.

## 3. Canonical Preflight Result

The canonical command was:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  scripts/run_simulation_provenance_qualification.py \
  --output /tmp/SIM-Q01-MIN_preflight.json \
  --report /tmp/SIM-Q01-MIN_preflight.md
```

It failed in the SIM-008 live supplier with
`MISSING_STRUCTURED_SIMULATION_TIME`; no preflight JSON or Markdown artifact
was produced.  This is correct fail-closed adapter behavior: it did not
substitute wall time, historical Evidence, or a fabricated simulator clock.

## 4. Execution-Path Comparison

The isolated control and canonical path use the same:

- `GazeboSystemWorld` and `BoundedGazeboNav2Runtime`;
- SIM-008 scenario and initial-pose authority;
- `NormalSystemE2E` executor;
- localization bootstrap and structured-time source.

The canonical path differs only after that executor returns: it calls
`run_sim008_qualification`, which recursively extracts the runtime
`simulation_time` and correctly rejects an outcome where execution stopped
before a live observation was made.

The observed stale graph condition was concrete.  A fixed
`ROS_DOMAIN_ID=44` contained reparented `ros_gz_bridge`, robot-state-publisher,
and Nav2 component processes from an earlier launch.  Action/topic discovery
reported their graph while `gz topic -l` in the new run's unique transport
partition was empty and `/clock` timed out.

## 5. Root Cause

Primary root cause class: `SIM008_RUNTIME_CLEANUP_DEFECT`.

`BoundedGazeboNav2Runtime.close()` terminated only the top-level `ros2 launch`
process group.  Launch-created descendant process groups could survive,
become reparented, and contaminate a subsequent run's fixed DDS domain.  The
previous cleanup result therefore did not prove the whole launch tree had
ended.

The first failing invariant in the canonical run remained
`SIMULATION_CLOCK_UNAVAILABLE`; the adapter's
`MISSING_STRUCTURED_SIMULATION_TIME` is its required fail-closed consequence.

## 6. Decision

`architecture_change_required: NO`.

The correction is a runtime lifecycle/isolation repair within the existing
SIM-008 execution boundary.  It does not alter MIN-Q01 scope, accepted
predecessor authority, timing requirements, or qualification semantics.

Rejected alternatives:

- treating cached ROS graph data as readiness;
- using wall time or accepted Evidence as simulator time;
- globally killing host processes;
- changing accepted SIM-008 artifacts.

## 7. Implementation

Modified `scripts/run_simulation_navigation.py` only within
`BoundedGazeboNav2Runtime`:

- added launch-descendant process-group discovery while the owned launch root
  is alive;
- terminates every captured owned process group during bounded cleanup;
- records owned process groups in cleanup provenance;
- allocates a per-run DDS domain and disables the ROS CLI daemon cache for
  that run, preventing a later launch from using a prior run's graph.

Modified `tests/test_simulation_navigation_backend.py` with regression tests
for descendant-group termination and fresh daemon-free DDS isolation.

## 8. Tests

`UNIT_PASS`:

```text
PYTHONDONTWRITEBYTECODE=1 Q01_PYTHON -m pytest -q -p no:cacheprovider \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_provenance_qualification.py
60 passed
```

`SCENARIO_COVERAGE_PASS`: the focused cleanup/isolation regression tests pass.

`python -m py_compile` passed for the touched runtime and qualification entry
points.  `git diff --check` passed.

## 9. Live SIM-008 Verification

`BLOCKED`.

After the correction, the runtime used a new DDS domain, a new Gazebo
partition, and daemon-free ROS CLI probes.  It no longer read the stale action
graph.  However, the top-level `ros2 launch` process remained alive without
spawning Gazebo child processes; `gz topic -l` was empty and every bounded
`/clock` probe timed out.  The first remaining runtime invariant is therefore:

```text
SIMULATION_CLOCK_UNAVAILABLE
```

This is a distinct, direct `SIM008_RUNTIME_LAUNCH_DEFECT` requiring a separate
bounded launch-start diagnosis.  No simulator time was fabricated.

## 10. Canonical 11-Subject Preflight

`CANONICAL_COMPLETE: NO`.

The preflight reaches SIM-008 and fails closed before any canonical output is
written.  The required subject count remains the frozen 11, but a complete
aggregate cannot be created until the live SIM-008 runtime produces a
structured clock observation.

## 11. Protected Scope Verification

The following remain unchanged by this correction:

- accepted SIM-004, SIM-005, SIM-007, SIM-008, and SIM-009 Acceptance/Evidence;
- MIN-Q01 architecture and 11-subject scope;
- frozen SIM-010 state.

The pre-existing dirty `results/simulation/SIM-004_navigation_backend.json`
was not read as authority, modified, restored, or staged.

## 12. Final State

NOT_READY_FOR_ORCHESTRATOR_RESUME

## 13. Next Action

Perform one bounded `SIM008_RUNTIME_LAUNCH_DEFECT` diagnosis focused on why
the owned `ros2 launch nav2_bringup tb4_simulation_launch.py` parent remains
alive without starting its Gazebo child processes in the fresh runtime
environment.  Do not reopen MIN-Q01 architecture or alter accepted artifacts.
