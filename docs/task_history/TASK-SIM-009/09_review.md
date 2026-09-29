# Review — TASK-SIM-009

- Recommendation: REJECT
- Failed Gates: Scope, Requirements, Tests, Evidence
- Validation: focused/targeted regression set 103 PASS; `git diff --check` PASS; live runner는 tracked Evidence를 다시 쓰므로 재실행하지 않고 저장된 2회 연속 live run을 독립 검토함
- Evidence: FAIL — `SIM009-NAV-ABORTED`가 별도 abort fault가 아니라 `SIM009-NAV-BLOCKED`와 동일한 `blocked-bay` Nav2 실행이며, `SIM009-NAV-TF-UNAVAILABLE`도 live Gazebo/TF fault가 아님

## Blocking Findings

### SIM009-REREV-001 — HIGH

- Requirement / Contract: R3; L1-NAV의 blocked path, navigation abort/timeout, task-supported sensor/TF dependency fault를 각각 Gazebo Navigation/system fault world에서 실행해야 함
- File / Symbol: `src/simulation_runtime/failure_recovery.py::_navigation_scenario`; `results/simulation/SIM-009_failure_recovery.json`; `tests/test_simulation_failure_recovery.py`
- Issue: live `SIM009-NAV-BLOCKED`와 `SIM009-NAV-ABORTED`가 모두 기본 `destination_id = blocked-bay`를 전송해 동일한 Nav2 `ABORTED` 결과만 관찰한다. 별도 navigation-abort injection이 없고, TF-unavailable 경로는 live runtime이 준비된 상태에서도 `_ScriptedNavigationRuntime(ready=False)`를 사용한다. 테스트는 이 세 scenario의 injection 구분을 검증하지 않는다.
- Why it blocks acceptance: Evidence의 세 L1-NAV fault 행이 manifest가 선언한 서로 다른 fault classes를 입증하지 못하므로 R3 및 `SIM_FAILURE_SUITE_READY` 결론을 신뢰할 수 없다.
- Recommended remediation: accepted Gazebo/Nav2 runtime에 scenario별 deterministic abort 및 TF/dependency fault injection을 추가하고, 각 행에 scenario-local goal/fault evidence만 기록하며, 동일 fault 재사용을 거부하는 테스트를 추가한다.

```yaml
acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: TASK-SIM-009
  review_decision: REJECT
  reviewed_commit: edda14e26b26d33f7684128188fab743888d8c53
  task_specific_decision: SIM_FAILURE_SUITE_READY

  task_spec:
    path: tasks/TASK-SIM-009.md
    sha256: ed6ffaa125cec5fd595b2d31cad650d4d6b5b128651e8524e169531a881d40a9

  evidence:
    required: true
    path: results/simulation/SIM-009_failure_recovery.json
    sha256: f1257e5616add50243b9d9fb1df8fcadb53fa7a3070a45f462ede2bf182351f2

  supporting_artifacts:
    - path: results/simulation/SIM-009_failure_recovery_run1.json
      sha256: af8ce56b823f4f9376ac7cf96e13f395fa923efb059d4458eea10c925bea9922
    - path: results/simulation/SIM-009_failure_recovery_run2.json
      sha256: f1257e5616add50243b9d9fb1df8fcadb53fa7a3070a45f462ede2bf182351f2
    - path: results/simulation/SIM-009_repeatability.json
      sha256: fb60492701fba1f2319a586772b2c618d9ddb47f50e8abf0987fa69cd875ffe1

  acceptance_recording_eligible: false
  blocking_reason: R3 L1-NAV abort and TF fault classes are not independently exercised by live Gazebo/Nav2 scenarios.
```
