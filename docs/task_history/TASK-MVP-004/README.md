# TASK-MVP-004 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-004`
- 목표: 단일 Robot Skill timeout을 reconciliation 후 한 번 bounded retry로 복구한다.
- 구현 범위: deterministic fixture와 runtime recovery coordinator.
- 주요 비범위: ROS 2, physical robot, VLA, persistence, MVP-005.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | timeout -> reconciliation -> one retry -> completed | `01_implementation.md` |
| 02 | Review | ACCEPT | scope, state invariant, tests, evidence acceptance | `02_review.md` |

## 3. 검증 결과

- Focused tests: 3 PASS
- Full regression: 39 PASS
- Evidence: `../../../results/mvp/MVP-004.json`
- Final review: ACCEPT

## 4. 최종 상태

`ACCEPT TASK-MVP-004`

## 5. 포트폴리오 요약

단일 Robot Skill timeout을 physical result의 실패로 성급히 해석하지 않고 `UNKNOWN` 상태로 보존했다. deterministic runtime은 같은 mission과 idempotency key를 유지한 채 status reconciliation을 먼저 수행하고, typed retryability가 참일 때만 한 번 retry한다. non-retryable reconciliation은 retry 없이 `ESCALATED`로 끝나며, focused 3개와 전체 39개 regression test 및 machine-readable evidence로 확인되었다. review에서는 retry limit의 실제 소유자가 `MissionRecord`임과 fixture trace의 구체 타입 결합을 LOW 유지보수 위험으로 기록했다.

## 6. Explain TASK-MVP-004

TASK-MVP-004는 Day-10 MVP의 유일한 실패·복구 경로를 구현한 작업입니다.

정상 흐름 중 Robot Skill 호출이 timeout되면, 물리 동작의 성공/실패를 추측하지 않습니다. 대신 action을 `UNKNOWN`, mission을 `RECONCILING`으로 전이한 뒤 같은 `action_id`로 상태를 조회합니다.

```text
Robot Skill timeout
→ Action UNKNOWN
→ Mission RECONCILING
→ get_action_status(action_id)
→ FAILED + retryable=true
→ Mission RECOVERING
→ 같은 mission/idempotency_key로 1회 재시도
→ SUCCEEDED
→ Mission COMPLETED
```

핵심 구현은 다음과 같습니다.

- `DeterministicTimeoutRecoverySkillFake`: 첫 호출은 항상 ambiguous timeout, reconciliation 뒤 한 번의 retry는 성공하도록 만든 테스트용 fake입니다.
- `SingleFailureRecoveryCoordinator`: reconciliation 전 retry를 허용하지 않고, typed `retryable` 결과에 따라 한 번만 재시도하거나 `ESCALATED`로 끝냅니다.
- 기존 `MissionRecord` 상태 머신이 retry 횟수를 최대 1회로 강제합니다.
- `results/mvp/MVP-004.json`: 상태 전이, 호출 순서, retry count, 소스 해시, 테스트 결과를 기록합니다.

검증된 사항:

- timeout은 즉시 성공/실패 처리되지 않고 `UNKNOWN`이 됩니다.
- reconciliation이 retry보다 먼저 실행됩니다.
- retryable 결과만 recovery로 진입합니다.
- non-retryable 결과는 retry 없이 `ESCALATED`됩니다.
- retry는 정확히 1회이며, 두 번째 retry는 상태 머신이 fail-closed 처리합니다.
- focused test 3개와 전체 regression 39개가 통과했습니다.

명시적 비범위는 physical robot, ROS 2/Nav2/MoveIt, VLA, persistence/SQLite, 외부 네트워크·프로세스, MVP-005입니다. 검토 결과는 `ACCEPT`입니다.