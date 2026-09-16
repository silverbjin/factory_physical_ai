# Fix — TASK-SIM-004

- Result: READY FOR INDEPENDENT RE-REVIEW
- Based on Review: `02_review.md`

## Finding Results

| Finding | Severity | Status | Correction | Regression |
|---|---|---|---|---|
| SIM004-REV-001 | HIGH | FIXED | fake in-memory success를 실제 Gazebo/ROS 2/Nav2 runner로 교체하고, 격리된 runtime, deterministic AMCL bootstrap, output-observing TF probe, depot map 내부의 shared canonical start `(-6.5, 0.0, 0.0)`, symbolic action terminal parsing을 적용했다. | focused PASS (44) |
| SIM004-REV-002 | HIGH | FIXED | 실제 PID/PGID, lifecycle/TF probe, raw action output, terminal status/error code, timeout reconciliation 및 cleanup을 Evidence에 기록한다. | focused PASS (44) |

## Root-cause Progression

- fake in-memory success: 실제 Gazebo/Nav2 실행 경로와 process lifecycle 측정으로 교정했다.
- stale Gazebo / `TF_OLD_DATA`: `ROS_DOMAIN_ID`와 `GZ_PARTITION` 격리 및 process-group cleanup으로 오염을 제거했다.
- headless AMCL bootstrap 부재: `map_server`/AMCL lifecycle 활성화와 deterministic `/initialpose` 발행을 추가했다.
- `tf2_echo` false negative: 프로세스 종료 코드 대신 실제 transform 출력 관찰로 판정하도록 교정했다.
- `START_OUTSIDE_MAP = 203`: depot map 밖의 `(-8.0, 0.0)` 대신 Gazebo spawn과 AMCL이 공유하는 `(-6.5, 0.0)`을 사용했다.
- action terminal 해석: `SUCCEEDED`/`ABORTED`를 파싱하고 raw action output과 Nav2 `error_code`를 보존했다.

- Evidence: PASS — `results/simulation/SIM-004_navigation_backend.json` (`SIM_NAVIGATION_BACKEND_READY`, `generated_at=2026-09-16T10:38:32.775Z`)
- Runtime: canonical `line-b-drop` `SUCCEEDED`, `error_code=0`, arrival verified; `blocked-bay` `ABORTED`, `error_code=204`; 모든 5개 scenario PASS
- Cleanup: PASS — launch PGID `219798` 종료 후 관련 descendant 없음
- Regression: NOT REQUIRED
- Git history: NO HISTORY ACTION REQUIRED
- Conditional Sources loaded: 0
- Next: Independent Read-only Review
