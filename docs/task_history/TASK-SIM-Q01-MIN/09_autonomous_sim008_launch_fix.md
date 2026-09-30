# Autonomous SIM-008 Runtime Launch Diagnosis and Fix

## 1. Trigger

The isolated and canonical SIM-008 paths were failing closed with
`SIMULATION_CLOCK_UNAVAILABLE`. The `ros2 launch` owner remained alive, but the
expected Gazebo/Nav2 runtime was not established and no structured simulator
time could be observed.

This investigation treated the missing clock as a downstream invariant and
searched for the first launch failure.

## 2. Current Worktree / Previous Correction

The worktree already contained legitimate TASK-SIM-Q01-MIN changes, including
the preceding `SIM008_RUNTIME_CLEANUP_DEFECT` correction in
`scripts/run_simulation_navigation.py`. That correction introduced per-run DDS
and Gazebo isolation plus launch-owned descendant process-group cleanup. It was
preserved.

The pre-existing dirty
`results/simulation/SIM-004_navigation_backend.json` was not restored,
rewritten, staged, or used as accepted authority. No existing target-task work
was discarded.

## 3. Direct Launch Control

The exact launch command was the repository runtime command:

```text
/opt/ros/jazzy/bin/ros2 launch nav2_bringup tb4_simulation_launch.py \
  headless:=True use_rviz:=False use_simulator:=True \
  world:=<task world> params_file:=<task Nav2 params>
```

The unsourced control, matching the runtime's inherited worker environment,
failed before creating the launch description or child runtime:

```text
importlib.metadata.PackageNotFoundError: No package metadata was found for ros2cli
```

The same command after sourcing `/opt/ros/jazzy/setup.bash` remained healthy
for the bounded observation period and spawned `gz sim`,
`ros_gz_bridge/parameter_bridge`, `robot_state_publisher`, and the Nav2
component container. The launch log recorded creation of the `/clock` bridge.
The control was intentionally terminated at the end of the bounded experiment;
only its owned processes were cleaned.

Direct launch control: **PASS**.

## 4. Runtime-Managed Launch

Before the correction, `BoundedGazeboNav2Runtime` copied `os.environ` and added
per-run isolation values, but did not source or otherwise materialize the ROS
installation environment. The launch executable could start as a process while
its Python entry point failed during package metadata discovery, so no Gazebo
or Nav2 child runtime appeared.

After the correction, the runtime-managed path used one explicitly materialized
ROS/Gazebo environment for the launch process and all readiness probes. It
spawned the expected child processes and completed the SIM-008 mission.

Runtime-managed launch: **PASS**.

## 5. Environment Delta

Before correction, the worker environment did not contain the setup-derived
values required by the Jazzy installation, including:

```text
ROS_DISTRO
AMENT_PREFIX_PATH
CMAKE_PREFIX_PATH
LD_LIBRARY_PATH
PYTHONPATH
GZ_CONFIG_PATH
GZ_SIM_RESOURCE_PATH
GZ_SIM_SYSTEM_PLUGIN_PATH
```

Materializing `/opt/ros/jazzy/setup.bash` supplied `ROS_DISTRO=jazzy`, the ROS
Python package path, ROS/Gazebo executable and library paths, and Gazebo
resource/plugin paths. The existing per-run `ROS_DOMAIN_ID`, `GZ_PARTITION`,
and task-local `ROS_LOG_DIR` were then applied to that environment.

No evidence implicated `RMW_IMPLEMENTATION`, Fast DDS/Cyclone DDS variables,
`DISPLAY`, or `WAYLAND_DISPLAY`. Per-run graph and transport isolation did not
prevent child creation once the ROS installation environment was present.

## 6. Process Lifecycle Evidence

The corrected live Gate A run observed:

```text
launch owner PID/PGID: 11177
ros_gz_bridge PID:     11246
gz sim PID:            11250
robot state PID:       11253
Nav2 container PID:    11254
```

The runtime then observed a live clock, odometry/localization transforms, and
navigation readiness. Cleanup terminated the owned launch group within the
5-second bound. None of the listed PIDs remained after the run. No global
kill-all operation was used.

## 7. First Concrete Launch Failure

The first failing invariant was:

```text
The ROS 2 launch Python entry point must resolve the ros2cli distribution
before evaluating the launch description or spawning child processes.
```

The first concrete error was:

```text
importlib.metadata.PackageNotFoundError: No package metadata was found for ros2cli
```

`SIMULATION_CLOCK_UNAVAILABLE` occurred later because Gazebo had never been
created; it was not the root cause.

## 8. Root Cause

```yaml
root_cause_class: SIM008_LAUNCH_ENVIRONMENT_DEFECT
first_failing_invariant: ros2cli distribution must be importable by the launch process
first_concrete_error: importlib.metadata.PackageNotFoundError for ros2cli
working_control: identical command after /opt/ros/jazzy/setup.bash
failing_control: identical command in the unsourced worker/runtime environment
```

The non-interactive runtime incorrectly assumed its parent process had already
sourced ROS. Consequently, the absolute `ros2` executable was found while its
Python package metadata and the Gazebo/Nav2 setup paths were not. This explains
why an owner process could be observed without the expected child runtime.

## 9. Decision

```yaml
architecture_change_required: NO
```

The bounded correction was to materialize the authoritative Jazzy setup once
when constructing `BoundedGazeboNav2Runtime`, then reuse that exact environment
for launch and probes.

Rejected alternatives:

- weakening the clock or localization readiness checks;
- substituting wall time or historical simulator time;
- changing accepted SIM-008/SIM-009 artifacts;
- removing bounded child cleanup or using global process killing;
- hard-coding individual ROS/Gazebo path fragments without the installation's
  setup authority.

## 10. Implementation

Files changed for this correction:

- `scripts/run_simulation_navigation.py`
- `tests/test_simulation_navigation_backend.py`

Symbols changed:

- `ROS_SETUP`
- `ros_runtime_environment()`
- `BoundedGazeboNav2Runtime.__init__()`
- `test_runtime_materializes_the_ros_jazzy_launch_environment()`

`ros_runtime_environment()` runs a non-interactive Bash process, sources
`/opt/ros/jazzy/setup.bash`, captures its NUL-delimited environment, and fails
closed with `ROS_RUNTIME_ENVIRONMENT_UNAVAILABLE` if setup cannot be
materialized. The runtime then adds its existing per-run isolation settings.

## 11. Tests

The meaningful RED was:

```text
test_runtime_materializes_the_ros_jazzy_launch_environment
KeyError: 'ROS_DISTRO'
1 failed, 12 deselected
```

After the correction, that test passed. The complete focused command was:

```text
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  -m pytest -q -p no:cacheprovider \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_provenance_qualification.py
```

Result:

```text
61 passed in 2.51s
```

`py_compile` passed for the four required Python modules, and
`git diff --check` passed.

```yaml
UNIT_PASS: YES
SCENARIO_COVERAGE_PASS: YES
CANONICAL_COMPLETE: NO
```

Focused test success is not being reported as canonical completion.

## 12. Isolated SIM-008 Live Verification

The corrected `NormalSystemE2E -> GazeboSystemWorld ->
BoundedGazeboNav2Runtime` live path produced:

```yaml
launch_parent: PASS
gazebo_child: PASS
ros_gazebo_bridge: PASS
ros_clock: PASS
odom_to_base: PASS
deterministic_initial_pose: PASS
map_to_odom: PASS
navigate_to_pose: PASS
mission_result: success
structured_simulation_time:
  - {sec: 40, nsec: 260000000}
  - {sec: 46, nsec: 401000000}
cleanup_complete: true
cleanup_bound_ms: 5000
```

Isolated SIM-008, structured simulator time, and owned cleanup all passed.

## 13. Canonical 11-Subject Preflight

The required preflight command advanced through the corrected SIM-008 live
execution. It then entered the SIM-009 failure-suite path and stopped in:

```text
run_failure_suite()
  -> _accepted_binding("SIM-004")
  -> ValueError: SIM-004 accepted evidence hash does not match
```

The process exited non-zero before producing `/tmp/SIM-Q01-MIN_preflight.json`
or `/tmp/SIM-Q01-MIN_preflight.md`. Therefore no canonical aggregate counts or
READY result exist to report:

```yaml
required_subjects: 11
observed_aggregate_subjects: NOT_PRODUCED
missing: NOT_EVALUATED
extra: NOT_EVALUATED
binding_errors: SIM-004 accepted evidence hash does not match
validation: BLOCKED
task_specific_result: NOT_PRODUCED
CANONICAL_COMPLETE: NO
```

This is the explicitly protected pre-existing dirty SIM-004 current-worktree
Evidence condition. It is outside the SIM-008 launch correction and was not
modified or bypassed.

## 14. Protected Scope Verification

```yaml
accepted_SIM-004_Acceptance_or_immutable_Evidence: UNCHANGED
accepted_SIM-005_Acceptance_or_immutable_Evidence: UNCHANGED
accepted_SIM-007_Acceptance_or_immutable_Evidence: UNCHANGED
accepted_SIM-008_Acceptance_or_immutable_Evidence: UNCHANGED
accepted_SIM-009_Acceptance_or_immutable_Evidence: UNCHANGED
MIN-Q01_architecture_and_11-subject_scope: UNCHANGED
frozen_SIM-010_state: UNCHANGED
historical_or_wall_time_backfill: NONE
orchestrator_resumed: NO
```

The dirty current-worktree SIM-004 result remained untouched and was not used
as accepted authority.

## 15. Final State

```text
NOT_READY_FOR_ORCHESTRATOR_RESUME
```

SIM-008 launch, runtime, simulator-time collection, and cleanup are corrected.
Canonical completion is blocked by the protected pre-existing SIM-004
current-worktree Evidence hash mismatch in the nested SIM-009 accepted-binding
path.

## 16. Next Action

Resolve the bounded accepted-binding consumption defect in the SIM-009
failure-suite path so it verifies the immutable accepted Git Evidence rather
than the protected dirty current-worktree SIM-004 result, without modifying the
dirty artifact. Then rerun the canonical 11-subject preflight.
