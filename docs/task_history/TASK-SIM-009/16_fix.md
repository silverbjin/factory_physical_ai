# Fix — TASK-SIM-009

- Result: `READY_FOR_HOST_VALIDATION`
- Based on Diagnosis: `15_diagnosis.md`

## Root cause

current process environment omitted ROS Jazzy setup, so `/opt/ros/jazzy/bin/ros2` could not discover `ros2cli`.

## Correction

all remaining validation uses a command-local `source /opt/ros/jazzy/setup.bash` followed by the explicit `.venv-sim/bin/python` interpreter.

## Files modified

- None

## Regression

- sourced `/opt/ros/jazzy/bin/ros2 --help`: PASS
- sourced `.venv-sim/bin/python -c "import mujoco"`: PASS (`3.13.0`)

## Runtime validation

SIM-009 sourced full-suite validation is the next automatic step.

## Remaining blocker

NONE

## Next

Run sourced `scripts/run_simulation_failure_recovery.py`.
