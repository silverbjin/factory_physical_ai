# Fix — TASK-SIM-009

- Result: `READY_FOR_INDEPENDENT_RE_REVIEW`
- Based on Diagnosis: `13_diagnosis.md`, `15_diagnosis.md`

## Root cause

- `STALE_BUDGET`: BLOCKED의 live rclpy call은 최대 2초인 server discovery, goal acceptance, terminal-result 대기 세 단계를 포함하지만 기존 budget은 한 단계만 계산했다.
- validation environment: `.venv-sim`의 `mujoco==3.13.0` 누락 및 ROS Jazzy setup 미적용이 focused/full validation을 차단했다.

## Correction

- `LIVE_NAVIGATION_CALL_BUDGET_MS` 및 `SIM009-NAV-BLOCKED` budget을 `7000ms`로 정렬했다.
- BLOCKED budget regression을 추가했다.
- accepted baseline version `mujoco==3.13.0`을 `.venv-sim`에 복구하고, ROS commands를 `source /opt/ros/jazzy/setup.bash` 환경에서 실행했다.

## Files modified

- `src/simulation_runtime/failure_recovery.py`
- `configs/simulation/sim009_failure_scenarios.json`
- `tests/test_simulation_failure_recovery.py`
- `results/simulation/SIM-009_failure_recovery.json`
- `results/simulation/SIM-009_failure_recovery_run1.json`
- `results/simulation/SIM-009_failure_recovery_run2.json`
- `results/simulation/SIM-009_repeatability.json`

## Regression

- MuJoCo headless model load/step: PASS (`3.13.0`)
- focused pytest: `72 passed`
- `git diff --check`: PASS

## Runtime validation

- full suite run1: `SIM_FAILURE_SUITE_READY`
- full suite run2: `SIM_FAILURE_SUITE_READY`
- repeatability: PASS; semantic fault signatures equivalent, execution IDs/Nav2 goal UUIDs distinct, canonical equals run2
- accepted SIM-004/SIM-005/SIM-006/SIM-008 canonical Evidence SHA256: PASS

## Remaining blocker

NONE

## Next

Independent Read-only Re-review.
