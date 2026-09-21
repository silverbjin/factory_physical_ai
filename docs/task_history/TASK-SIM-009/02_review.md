# Review — TASK-SIM-009

- Recommendation: REJECT
- Failed Gates: Scope, Requirements, Contract, Invariants, Tests, Evidence
- Validation: focused 49 PASS; 비변경 `build_evidence()` 실행 PASS; `git diff --check` PASS; 쓰기 전용 runner 진입점은 Evidence 변경 방지를 위해 직접 실행하지 않음
- Evidence: FAIL — 필수 predecessor binding, 실제 Gazebo fault 실행, retry authorization/idempotency/cleanup 증명이 없음

## Blocking Findings

### SIM009-REV-001 — HIGH

- Requirement / Contract: R3, R10, EC1, EC4; Gazebo가 Navigation/system fault world를 소유해야 함
- File / Symbol: `src/simulation_runtime/failure_recovery.py::_ScriptedNavigationRuntime`, `_navigation_scenario`, `_base_row`
- Issue: 모든 L1-NAV fault가 실제 accepted Gazebo/Nav2 runtime 대신 메모리 scripted observation을 사용하고, cleanup 성공을 상수 `True`로 기록한다.
- Why it blocks acceptance: blocked/abort/timeout/TF fault와 process cleanup이 Gazebo Navigation/system world에서 실행됐다는 증명이 없다.
- Recommended remediation: accepted bounded Gazebo runtime에 deterministic fault injection을 연결하고 실제 lifecycle/cleanup 결과를 Evidence에 기록한다.

### SIM009-REV-002 — HIGH

- Requirement / Contract: R6, R7, R8; `simulation_execution_contract_v1.md` Section 9 및 `RetryAuthorization`
- File / Symbol: `src/simulation_runtime/failure_recovery.py::_navigation_scenario`
- Issue: retry 전에 required `RetryAuthorization`을 생성/검증하지 않으며, `valid_retry`가 `reconciliation_completed`, resolved retryable `error`, remaining budget을 확인하지 않는다. `logical_side_effect_count`도 측정값이 아니라 상수 `1`이다.
- Why it blocks acceptance: unknown 이후 retry와 idempotency가 frozen retry policy를 만족한다는 machine-testable proof가 없다.
- Recommended remediation: authoritative failed reconciliation의 retryable error를 보존하고 schema-valid authorization record로 모든 조건을 검증하며 side-effect count를 runtime 측정에서 산출한다.

### SIM009-REV-003 — HIGH

- Requirement / Contract: R5, R9, EC2; skill success 뒤 Verification-before-Mission-success
- File / Symbol: `src/simulation_runtime/failure_recovery.py::_verification_scenario`
- Issue: `skill_reported_success = True`를 상수로 추가하고 verifier route만 호출한다. Mission lifecycle/commit 경로는 실행하지 않는다.
- Why it blocks acceptance: mismatch/uncertain/stale 결과가 Mission success를 막고 RECOVERY/RECONCILE/HITL 상태에 실제로 도달한다는 요구를 증명하지 못한다.
- Recommended remediation: accepted Mission execution/lifecycle adapter를 통해 skill-success 결과와 Verification fault를 연결하고 최종 Mission transition을 검증한다.

### SIM009-REV-004 — HIGH

- Requirement / Contract: R8, R10, TASK Evidence Section 11, EC5
- File / Symbol: `results/simulation/SIM-009_failure_recovery.json`; `tests/test_simulation_failure_recovery.py`
- Issue: Evidence에 accepted predecessor bindings가 없고, no-physical-dependency/no-dual-world-authority 증명도 없다. cleanup 및 idempotency 값은 구현 상수이며 테스트는 이 상수와 suite 자체의 `pass`만 확인한다.
- Why it blocks acceptance: 필수 Evidence가 accepted revisions, 실제 cleanup, side-effect 비중복을 독립적으로 재현하거나 검증할 수 없다.
- Recommended remediation: predecessor path/hash/result binding과 runtime-derived authority/physical-dependency/cleanup/idempotency facts를 추가하고 각 필수 사실을 직접 검증하는 negative/boundary tests를 작성한다.
