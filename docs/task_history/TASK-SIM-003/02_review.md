# Review — TASK-SIM-003

- Recommendation: REJECT
- Failed Gates: Requirement compliance, Invariant safety, Test adequacy, Evidence integrity
- Validation: focused PASS (`48 passed`); task verifier 재실행은 `SIM_BASELINE_BLOCKED`; regression NOT REQUIRED
- Evidence: canonical payload/hash와 현재 측정값은 일치하지만 fail-closed 보장이 불충분하여 FAIL

## Blocking Findings

### F-SIM-003-001 — HIGH

- Requirement / Contract: R1, R8, R9; stale 또는 hash-inconsistent predecessor는 `SIM_BASELINE_BLOCKED`로 닫혀야 한다.
- File / Symbol: `scripts/verify_simulation_toolchain_baseline.py` / `_commit_exists`, `validate_predecessors`, deterministic regression result
- Issue: `reviewed_commit`은 존재 여부만 확인하고 accepted artifact의 Git blob과 연결하지 않으며, deterministic regression 이후 predecessor hash를 재검증하지 않고 `accepted_evidence_modified = False`를 상수로 기록한다.
- Why it blocks acceptance: 무관한 기존 commit으로 `reviewed_commit`을 바꿔도 predecessor validation이 `PASS`가 되어 exact accepted identity를 증명하지 못한다.
- Recommended remediation: canonical path와 reviewed Git blob hash를 검증하고, regression 전후 accepted artifact snapshot을 비교하여 결과와 blocker를 파생하며 해당 변조 테스트를 추가한다.

### F-SIM-003-002 — HIGH

- Requirement / Contract: R2 및 fail-closed runtime identity 규칙
- File / Symbol: `scripts/verify_simulation_toolchain_baseline.py` / `evaluate_baseline` ROS 2 identity 판정
- Issue: ROS 2 판정이 사용자 제어 `ROS_DISTRO` 값과 일반 CLI/import 성공만 신뢰하고 executable/package prefix가 Jazzy runtime과 일치하는지 검증하지 않는다.
- Why it blocks acceptance: `ROS_DISTRO=jazzy`와 `/opt/ros/humble/bin/ros2` 조합도 `ROS status = PASS`, `SIM_BASELINE_READY`가 될 수 있다.
- Recommended remediation: `ros2 pkg prefix rclpy` 등 측정된 installation prefix/distro identity를 실행 파일과 교차 검증하고 mismatch negative test를 추가한다.
