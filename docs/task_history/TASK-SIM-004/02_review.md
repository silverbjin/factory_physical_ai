# Review — TASK-SIM-004

- Recommendation: REJECT
- Failed Gates: Scope, Requirements, Invariants, Tests, Evidence
- Validation: focused PASS (41 passed), `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — Gazebo/ROS 2/Nav2 실행과 process lifecycle 측정 없이 `SIM_NAVIGATION_BACKEND_READY`를 선언함

## Blocking Findings

### SIM004-REV-001 — HIGH

- Requirement / Contract: R3, R5, R6, R7, R9, EC1–EC3
- File / Symbol: `scripts/run_simulation_navigation.py:main`, `src/simulation_runtime/navigation_backend.py:NavigationBackend.execute`, `data/simulation/sim004_navigation_proxy_world.sdf`
- Issue: runner는 Gazebo, ROS 2, bridge, Nav2 process를 시작하지 않고 in-memory `behavior` 분기로 결과를 생성한다. proxy model은 `<static>true</static>`이므로 실제 navigation/도착/차단 검증을 수행할 수 없다.
- Why it blocks acceptance: TASK의 핵심은 accepted contract 뒤에서 Gazebo Harmonic + ROS 2 Jazzy + Nav2-facing L1-NAV backend과 bounded process lifecycle를 입증하는 것이다. 현재 구현은 L0 mock을 넘어선 실행 경로를 제공하지 않는다.
- Recommended remediation: 이동 가능한 proxy base와 고정 world/map을 사용해 Gazebo/bridge/Nav2 lifecycle과 NavigateToPose 경로를 실제로 시작·실행·종료하고, 각 시나리오의 권위 있는 상태와 도착을 bounded runtime에서 검증할 것.

### SIM004-REV-002 — HIGH

- Requirement / Contract: R10, R12, EC4–EC5
- File / Symbol: `results/simulation/SIM-004_navigation_backend.json`, `scripts/run_simulation_navigation.py:main`
- Issue: Evidence의 startup/execution/cleanup 수치와 `cleanup_complete`는 process 측정 결과가 아니며, runtime identity도 SIM-003 baseline에서 복사될 뿐 현재 backend 실행에서 측정되지 않았다. 그럼에도 `SIM_NAVIGATION_BACKEND_READY`를 선언한다.
- Why it blocks acceptance: READY는 mandatory Navigation scenarios와 bounded cleanup이 실제로 통과했을 때만 허용되며, 현 Evidence는 그 판정을 지지하지 않는다.
- Recommended remediation: 실제 runner의 process PID/group, readiness probe, scenario timing/result, timeout, termination/kill escalation, cleanup verification과 현재 runtime 식별자를 측정해 Evidence를 재생성하고, 필수 검증 실패 시 `SIM_NAVIGATION_BACKEND_BLOCKED`를 반환할 것.
