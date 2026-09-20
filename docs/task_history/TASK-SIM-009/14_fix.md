# Fix — TASK-SIM-009

- Result: `READY_FOR_HOST_VALIDATION`
- Based on Diagnosis: `13_diagnosis.md`

## Root cause

`.venv-sim`에서 `mujoco` dependency가 누락되어 focused pytest와 failure-suite import가 중단됐다.

## Correction

accepted SIM-003 baseline version인 `mujoco==3.13.0`을 `.venv-sim`에만 복구했다.

## Files modified

- `.venv-sim` environment packages only

## Regression

- MuJoCo headless model load/step: PASS (`3.13.0`)
- focused pytest: `72 passed`
- `git diff --check`: PASS

## Runtime validation

SIM-004/SIM-005/SIM-006/SIM-008 accepted canonical Evidence SHA256: PASS. SIM-009 full-suite validation is the next automatic step.

## Remaining blocker

NONE

## Next

Run `scripts/run_simulation_failure_recovery.py` with `.venv-sim/bin/python`.
