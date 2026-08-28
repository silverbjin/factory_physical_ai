# Read-only Review — TASK-MVP-004

## 1. 검토 정보

- TASK: `TASK-MVP-004`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 검토 대상: `tasks/TASK-MVP-004.md`, MVP-004 변경 코드/테스트, frozen scope/architecture/contracts, `results/mvp/MVP-004.json`
- 검토 시점 Git 상태: `src/factory_tools/gateway.py`, `src/factory_tools/__init__.py`, `docs/task_history/README.md` 수정 및 `src/mission_runtime/recovery.py`, `tests/test_recovery.py`, `results/mvp/MVP-004.json`, TASK 이력 문서 미추적. 모두 TASK-MVP-004 범위와 일치한다.

## 2. 검토 결론

- Recommendation: ACCEPT
- BLOCKER: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 2

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| 단일 timeout이 `UNKNOWN` action을 만든다 | `DeterministicTimeoutRecoverySkillFake.transfer_part`, `SingleFailureRecoveryCoordinator.run` | `test_timeout_reconciles_once_then_retry_succeeds` | `action_sequence` | PASS |
| reconciliation 후 typed retryability를 읽는다 | `get_action_status`, `reconciled.error.retryable` | success/non-retryable recovery tests | `reconciliation_precedes_retry`, `retryability_read_from_typed_result` | PASS |
| retry 전 status query가 발생한다 | fixture `call_trace`와 coordinator 순서 | `test_timeout_reconciles_once_then_retry_succeeds` | `call_sequence` | PASS |
| retry는 동일 mission/logical operation에 대해 한 번만 발생한다 | 동일 `mission_id`/`idempotency_key`, `MissionRecord._RETRY_LIMIT` | `test_recovering_uses_only_one_bounded_retry`, recovery success test | `measured_retry_count: 1` | PASS |
| non-retryable reconciliation은 escalation한다 | `MissionRecord.apply_action_observation` | `test_non_retryable_reconciliation_escalates_without_retry` | `non_retryable_reconciliation_escalates` | PASS |
| Agent가 physical outcome/retry budget을 제어하지 못한다 | coordinator의 고정 API 및 state transition table | `test_runtime_owns_retry_budget_and_agent_cannot_supply_outcome` | `runtime_policy_is_not_agent_controlled` | PASS |
| 단일 failure/recovery 범위와 deterministic evidence | scripted fixture, `MVP-004.json` | focused 3 PASS, regression 39 PASS | state/call sequence, hashes | PASS |

## 4. 주요 Findings

### BLOCKER

없음.

### HIGH

없음.

### MEDIUM

없음.

### LOW

1. `SingleFailureRecoveryCoordinator._RETRY_BUDGET`는 선언되지만 실제 제한은 `MissionRecord._RETRY_LIMIT`가 강제한다. 동작은 안전하게 한 번으로 제한되지만, 중복 상수와 implementation history의 소유권 설명은 향후 유지보수에서 혼동을 줄 수 있다.
2. `SingleFailureRecoveryCoordinator._trace()`가 `FactoryToolGateway._robot_skill` private attribute와 `DeterministicTimeoutRecoverySkillFake` 구체 타입에 의존한다. Day-10 scripted fixture에는 적합하지만, coordinator를 일반 gateway와 재사용하려면 관찰용 trace interface를 별도 contract로 분리해야 한다.

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: PASS
Contract compliance: PASS
State / invariant safety: PASS
Test adequacy: PASS
Regression safety: PASS
Evidence integrity: PASS
```

## 6. 검토에서 확인한 핵심 위험

- timeout result는 physical completion/failure로 해석되지 않고 `UNKNOWN` 후 reconciliation으로 이동한다.
- retryable 판단은 fixture의 typed `ToolError`에서 읽고, non-retryable 결과는 `ESCALATED`로 종료한다.
- `MissionRecord`의 finite transition table이 두 번째 retry를 `StateTransitionError`로 fail-closed 처리한다.
- evidence의 현재 SHA-256은 uncommitted MVP-004 source/test snapshot과 일치하며, fixture 결과를 physical execution evidence로 주장하지 않는다.

## 7. 최종 Recommendation

`ACCEPT TASK-MVP-004`
