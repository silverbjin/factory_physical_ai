# Review — TASK-SIM-007

- Recommendation: REJECT
- Failed Gates: Scope, Requirements, Tests, Evidence
- Validation: focused PASS (39 passed), `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — stub-backed smoke를 물리 백엔드 통합 성공으로 기록함

## Blocking Findings

### SIM007-RVW-001 — HIGH

- Requirement / Contract: R3, R4, R6; Scope 2, 4, 5, 6
- File / Symbol: `src/simulation_runtime/mission_integration.py` / `_ReadyNavigationRuntime`, `_navigation`, `_vla`, `_verification_request`
- Issue: `navigation_physics`와 `system`이 accepted Gazebo/ROS 2 runtime 대신 항상 성공하는 로컬 stub을 사용하며, `system` VLA surrogate와 profile별 Verification observation adapter도 Gazebo 실행/관측에 연결되지 않는다.
- Why it blocks acceptance: profile 이름과 contract-shaped 결과만 바뀌고 요구된 accepted backend integration 및 Gazebo 단일 authoritative world 실행이 증명되지 않는다.
- Recommended remediation: accepted bounded Gazebo runtime을 주입하고, system Gazebo-side manipulation surrogate 및 profile별 normalized observation 경로를 실제 backend 결과에 연결한다.

### SIM007-RVW-002 — HIGH

- Requirement / Contract: R10, R11; bounded startup/execution/cleanup and fail-closed dependency behavior
- File / Symbol: `src/simulation_runtime/mission_integration.py` / `execute`, `_require_backend`; `scripts/run_simulation_mission_integration.py` / `main`
- Issue: startup/availability는 문자열 set membership으로만 판정하고 cleanup은 `cleaned_up = True`로 표시한다. 실제 simulator/process readiness, timeout, teardown, startup failure를 실행하거나 검증하지 않는다.
- Why it blocks acceptance: requested backend가 실제로 unavailable이거나 cleanup이 실패해도 smoke가 성공할 수 있다.
- Recommended remediation: bounded process/runtime lifecycle을 구현하고 실제 readiness 및 teardown 결과를 fail-closed 결과와 Evidence에 반영한다.

### SIM007-RVW-003 — HIGH

- Requirement / Contract: R9, R10, R11, R12; EC2, EC5, EC6, EC7
- File / Symbol: `tests/test_simulation_mission_integration.py`; `results/simulation/SIM-007_mission_integration.json`
- Issue: tests는 stub 성공과 profile metadata만 검사하고 backend 호출, verification non-pass gating, startup failure, bounded cleanup을 검증하지 않는다. Evidence는 이 결과로 `SIM_MISSION_INTEGRATION_READY`를 선언한다.
- Why it blocks acceptance: machine-readable Evidence가 required integration과 lifecycle을 증명하지 않으며 reviewed reality와 불일치한다.
- Recommended remediation: backend-spy/failure-path 및 verification-gate tests를 추가하고 실제 bounded profile smoke에서 Evidence를 재생성한다.
