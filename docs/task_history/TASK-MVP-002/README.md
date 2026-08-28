# TASK-MVP-002 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-002`
- 목표: deterministic mission/action state model과 reconciliation lifecycle을 최소 범위로 정의한다.
- 구현 범위: finite transition table, immutable record, bounded retry invariant, escalation path, transition evidence.
- 주요 비범위: action execution, persistence, ROS 2, Nav2, MoveIt, VLA, physical robot, MVP-003 이후 기능.
- 관련 Context / Plan / Contract: `tasks/TASK-MVP-002.md`, `plans/day10_mvp_scope_v1.md`, `docs/architecture/system_architecture_v1.md`, `docs/contracts/contract_plan.md`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | finite mission/action lifecycle, `UNKNOWN` reconciliation, one bounded retry, escalation | `01_implementation.md` |

## 3. 주요 설계 / 문제 해결 포인트

- `UNKNOWN`은 physical success나 failure로 추론되지 않고 `RECONCILING`으로만 진행된다.
- `ActionRecord`와 `MissionRecord`는 immutable이며, constructor/transition table을 우회해 terminal state나 retry count를 주입할 수 없다.
- retry는 `MissionRecord._RETRY_LIMIT = 1`로 deterministic runtime이 소유하며 caller 또는 Agent가 budget을 전달하지 못한다.
- retryable reconciliation failure만 `RECOVERING`으로 진입하고, non-retryable failure는 `ESCALATED` terminal path로 종료한다.

## 4. 검증 결과

- Focused tests: 당시 measured 12 PASS, 이력 보강 시 recheck 12 PASS
- Full regression: 당시 measured 28 PASS
- Evidence: `../../../results/mvp/MVP-002.json`
- Final review: `TBD` — 이력 보강 범위에서는 implementation record만 추가했다.

## 5. 최종 상태

`IMPLEMENTATION COMPLETE / REVIEW HISTORY TBD`

## 6. 포트폴리오 요약

TASK-MVP-002는 line-side logistics mission의 physical side effect를 안전하게 추적하기 위한 deterministic state core를 만들었다. timeout/ambiguous outcome은 `UNKNOWN`으로 남기고 reconciliation 전에는 success로 전이할 수 없게 했다. mission/action record를 immutable하게 유지하고 finite transition table로 invalid state 변화와 두 번째 retry를 fail-closed 처리했다. 실행 adapter, persistence, ROS/VLA를 의도적으로 제외해 이후 TASK가 typed boundary 위에서 검증 가능한 recovery를 추가할 수 있게 했다.

## 7. Explain TASK-MVP-003

TASK-MVP-002는 이후의 모든 실행·복구 작업이 의존하는 “결정론적 상태 머신”을 만든 작업입니다.

핵심 목적은 mission과 physical action의 상태를 명시적으로 제한해, 모호한 결과나 임의의 상태 변경이 안전하지 않은 실행으로 이어지지 않게 하는 것입니다.

```text
Mission:
CREATED → READY → EXECUTING
                    ├─ 성공 → COMPLETED
                    └─ ambiguous → RECONCILING
                                     ├─ retryable → RECOVERING → EXECUTING
                                     └─ non-retryable → ESCALATED

Action:
REQUESTED → EXECUTING
              ├─ SUCCEEDED
              ├─ FAILED
              └─ UNKNOWN → RECONCILING → FAILED
```

주요 구현 내용:

- `MissionRecord`: mission lifecycle과 최대 1회의 retry budget을 관리합니다.
- `ActionRecord`: action correlation 정보와 lifecycle을 immutable record로 관리합니다.
- `MissionStatus` / `ActionStatus`: 허용된 상태 집합만 제공합니다.
- `StateTransitionError`: 허용되지 않은 transition, 두 번째 retry, terminal-state 우회를 fail-closed 처리합니다.
- `apply_action_observation()`: `UNKNOWN`은 절대 success가 아니며, 반드시 `RECONCILING`으로 보냅니다. reconciliation 결과가 retryable이면 `RECOVERING`, 아니면 `ESCALATED`입니다.

Action record에는 다음 contract field가 포함됩니다.

- `mission_id`
- `action_id`
- `idempotency_key`
- `schema_version`
- `timestamp`
- `deadline`
- `status`
- `error`
- `retryable`
- `component_version`

검증 결과는 당시 focused test 12개와 전체 regression 28개가 모두 PASS였고, 현재 focused state-model test도 12개 PASS입니다. 증거는 [MVP-002.json](/home/jinho/projects/factory_physical_ai/results/mvp/MVP-002.json)에 남아 있습니다.

의도적으로 포함하지 않은 것은 실제 Robot Skill 호출, timeout I/O, persistence/SQLite, ROS 2/Nav2/MoveIt, VLA, physical robot입니다. TASK-MVP-003이 typed factory-tool boundary를, TASK-MVP-004가 timeout reconciliation과 one-retry recovery를 이 상태 모델 위에 추가했습니다.