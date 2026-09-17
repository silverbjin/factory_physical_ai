# Review — TASK-SIM-007

- Recommendation: REJECT
- Failed Gates: Requirements, Tests
- Validation: focused PASS (40 passed), `git diff --check` PASS; 직접 unavailable-runtime 재현은 FAIL
- Evidence: PASS — `results/simulation/SIM-007_mission_integration.json`은 `SIM_MISSION_INTEGRATION_BLOCKED`를 일관되게 기록

## Blocking Findings

### SIM007-RR-001 — HIGH

- Requirement / Contract: R11; unavailable requested backend/profile must produce explicit non-success
- File / Symbol: `src/simulation_runtime/mission_integration.py` / `MissionIntegrationRuntime._navigation`, `MissionIntegrationRuntime.execute`
- Issue: `gazebo_runtime_factory()` 또는 `runtime.start()`가 `ProfileUnavailable` 이외 예외를 발생시키면 예외가 호출자에게 그대로 전파되어 명시적 Mission non-success 결과를 생성하지 않는다. 현재 테스트는 readiness `False`만 검증하고 backend construction/start exception을 다루지 않는다.
- Why it blocks acceptance: 실제 ROS 2/Gazebo 실행 파일 누락이나 process startup 실패가 프로필의 fail-closed public-contract 결과 대신 workflow crash가 되어 R11과 bounded smoke 요구를 위반한다.
- Recommended remediation: backend construction/start 예외를 bounded cleanup 후 `PROFILE_UNAVAILABLE` Mission failure로 정규화하고, factory/start exception 및 cleanup 동작을 검증하는 회귀 테스트를 추가한다.
