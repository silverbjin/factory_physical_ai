# Diagnosis — TASK-SIM-009

- Stage: `diagnosis`
- Status: `RESOLVED`
- Disposition: `MISSING_ROS_JAZZY_ENVIRONMENT_SETUP`
- Read-only mode: YES
- Trigger: `.venv-sim/bin/python scripts/run_simulation_failure_recovery.py`에서 모든 L1-NAV scenario가 `live_runtime_ready=false`, process return code `1`로 중단됨
- Triggering lifecycle status: `REJECTED / FIX REQUIRED`
- Diagnosis tier/model: `GPT-5.6 Sol Medium` 요청 경로

## Root Cause

`GoalTrackedGazeboNav2Runtime → BoundedGazeboNav2Runtime.start()`가 상속한 process environment에 ROS Jazzy setup이 없었다. `PYTHONPATH=null` 상태에서 `/opt/ros/jazzy/bin/ros2`는 `PackageNotFoundError: ros2cli`로 종료했다. `source /opt/ros/jazzy/setup.bash` 후 동일 ROS CLI는 return code `0`이며 `.venv-sim`의 `mujoco==3.13.0` import도 유지된다.

## Violated or Missing Contract

accepted SIM-004 runtime launch는 ROS 2 Jazzy CLI/package environment를 전제로 한다. current Codex shell은 해당 environment propagation이 없어 runtime startup prerequisite를 만족하지 못했다.

## Authoritative Sources

- minimal `GoalTrackedGazeboNav2Runtime` startup probe
- `/opt/ros/jazzy/bin/ros2` entry-point traceback
- `scripts/run_simulation_navigation.py` (`BoundedGazeboNav2Runtime.environment`)
- `/opt/ros/jazzy/setup.bash` sourced CLI probe

## Resolution

remaining validation commands are executed as `source /opt/ros/jazzy/setup.bash && PYTHONDONTWRITEBYTECODE=1 .venv-sim/bin/python …`. No source, contract, or accepted predecessor change is required.

## Modification Scope

None. Per-command environment setup only.

## Protected Scope

- `scripts/run_simulation_navigation.py`
- `src/simulation_runtime/navigation_backend.py`
- accepted SIM-004/SIM-005/SIM-006/SIM-008 sources and canonical Evidence

## Verification Plan

- sourced minimal startup probe
- sourced focused pytest already passing interpreter
- sourced SIM-009 full suite twice and canonical repeatability validation

## Handoff / Next Action

- Next action: `IMPLEMENT_RESOLVED_FIX`
