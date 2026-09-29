# Implementation — TASK-SIM-009

- Result: COMPLETE
- Evidence: `results/simulation/SIM-009_failure_recovery.json`
- Changed areas: `configs/simulation/sim009_failure_scenarios.json`, `src/simulation_runtime/failure_recovery.py`, `scripts/run_simulation_failure_recovery.py`, `tests/test_simulation_failure_recovery.py`
- Key implementation delta:
  - 안정 ID와 실행 예산을 가진 16개 L0/L1-NAV/L1-VLA/L2 결함 시나리오 manifest를 추가했다.
  - 기존 Navigation, MuJoCo VLA, Verification adapter를 통해 fail-closed, reconciliation, bounded retry, RECOVERY, HITL 결정을 검증했다.
  - retry 경로에서 `mission_id`, `action_id`, `idempotency_key` 보존과 새 `request_id` 및 증가한 `attempt`를 기록했다.
  - bounded runner가 `SIM_FAILURE_SUITE_READY` Evidence를 생성한다.
- Validation: PASS — prescribed 5-file pytest (49 passed); runner PASS; `git diff --check` PASS
- Deviation from TASK: NONE
- Next: Independent Read-only Review
