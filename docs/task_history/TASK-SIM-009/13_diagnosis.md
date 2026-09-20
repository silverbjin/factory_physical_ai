# Diagnosis — TASK-SIM-009

- Stage: `diagnosis`
- Status: `RESOLVED`
- Disposition: `MISSING_PROJECT_ENVIRONMENT_DEPENDENCY`
- Read-only mode: YES
- Trigger: focused pytest 및 `scripts/run_simulation_failure_recovery.py`가 `ModuleNotFoundError: mujoco`로 import 단계에서 중단됨
- Triggering lifecycle status: `REJECTED / FIX REQUIRED`
- Diagnosis tier/model: `GPT-5.6 Sol Medium` 요청 경로

## Root Cause

`.venv-sim/bin/python`과 `/usr/bin/python3` 모두 `import mujoco`에 실패했다. wrong interpreter가 아니라 `.venv-sim`에 MuJoCo 의존성이 누락된 상태다. accepted `SIM-003_baseline.json` 및 `docs/simulation/simulation_baseline_v1.md`는 headless step 검증을 통과한 정확한 버전 `mujoco==3.13.0`을 기록한다.

## Violated or Missing Contract

TASK-SIM-009은 accepted SIM-005 MuJoCo backend를 실행해야 하지만, 현재 project venv는 해당 accepted runtime dependency를 제공하지 않아 test/suite import 경계에서 중단된다.

## Authoritative Sources

- `.venv-sim/bin/python` interpreter/import probe
- `results/simulation/SIM-003_baseline.json`
- `docs/simulation/simulation_baseline_v1.md`
- `src/simulation_runtime/mujoco_vla_backend.py`

## Resolution

`mujoco==3.13.0`만 `.venv-sim`에 설치한 뒤 같은 interpreter로 headless import/step, focused regression, 그리고 SIM-009 suite를 재검증한다. system-wide install 및 accepted predecessor source 변경은 불필요하다.

## Modification Scope

- `.venv-sim` Python environment only: `mujoco==3.13.0`

## Protected Scope

- `src/simulation_runtime/mujoco_vla_backend.py`
- accepted SIM-004/SIM-005/SIM-006/SIM-008 source, acceptance records, canonical Evidence

## Verification Plan

- `.venv-sim/bin/python -c "import mujoco; print(mujoco.__version__)"`
- `.venv-sim/bin/python` headless model-load/step probe
- requested focused pytest set
- `scripts/run_simulation_failure_recovery.py` and repeatability only after focused PASS

## Handoff / Next Action

- Next action: `IMPLEMENT_RESOLVED_FIX`
