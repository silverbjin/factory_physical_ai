# TASK-MVP-003 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-003`
- 목표: canonical mission을 위한 deterministic factory-tool gateway와 WMS/Robot Skill fake를 구현한다.
- 구현 범위: in-process typed gateway, deterministic fixture, action-status query.
- 주요 비범위: physical robot, ROS 2, Nav2, MoveIt, VLA, timeout/retry/reconciliation policy, persistence.
- 관련 Context / Plan / Contract: `plans/day10_mvp_scope_v1.md`, `docs/architecture/system_architecture_v1.md`, `docs/contracts/contract_plan.md`, `tasks/TASK-MVP-003.md`

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Review | REJECT | action-status failure envelope의 schema/correlation/timestamp 누락 | `01_review.md` |
| 02 | Fix | READY FOR INDEPENDENT RE-REVIEW | strict `ActionStatusQuery`와 full `ActionStatusResult` envelope 추가 | `02_fix.md` |
| 03 | Review | ACCEPT | full action-status envelope 및 failure regression 검증 | `03_review.md` |
| 04 | Implementation | COMPLETE (backfilled) | final accepted gateway/fixture implementation history | `04_implementation.md` |

## 3. 주요 설계 / 문제 해결 포인트

- `ActionStatusResult`는 MVP-004 reconciliation의 관찰 boundary이므로 success path뿐 아니라 unknown action typed failure에도 frozen cross-cutting envelope이 필요하다.
- `ActionStatusQuery`가 schema/correlation/UTC timestamp를 소유하고 fake result가 이를 전파하도록 하여 failure audit contract를 고정했다.

## 4. 검증 결과

- Focused tests: 8 PASS
- Full regression: 36 PASS
- Evidence: `../../../results/mvp/MVP-003.json`
- Final review: `ACCEPT TASK-MVP-003`

## 5. 최종 상태

`ACCEPT TASK-MVP-003`

## 6. 포트폴리오 요약

MVP-003은 deterministic factory-tool gateway와 fixture 기반 WMS/Robot Skill boundary를 구현했다. 독립 검토에서 success 중심 테스트가 action-status failure의 correlation contract를 검증하지 못한 점을 발견했다. Fix는 `ActionStatusQuery`와 non-null `ActionStatusResult` envelope을 도입하고 unknown action failure regression을 추가했다. 독립 re-review에서 frozen contract, scope, tests, evidence를 다시 검증하여 `ACCEPT TASK-MVP-003`을 결정했다.

## 7. Explain TASK-MVP-003

TASK-MVP-003는 Factory Agent가 만든 구조화된 mission을 바탕으로, 결정론적 Runtime이 WMS와 Robot Skill fake를 안전하게 호출하는 경계를 구현한 작업입니다.

흐름은 다음과 같습니다.

```text
Validated Mission
→ Deterministic Runtime
→ WMS Fake: 재고/출발 위치 확인
→ Robot Skill Fake: typed transfer 요청
→ Typed Action Result
→ Mission state transition
```

핵심은 Agent가 실행을 직접 제어하지 못하도록 분리한 점입니다.

- Agent는 mission 의미 해석과 구조화된 요청까지만 담당합니다.
- Runtime은 `mission_id`, `request_id`, `action_id`, `idempotency_key`, timestamp, deadline 등 실행 계약을 구성하고 검증합니다.
- Gateway는 strict schema를 적용해 누락·추가 필드, 잘못된 UUID, 비UTC 시간, 빈 문자열, 잘못된 quantity를 fail-closed 처리합니다.
- WMS와 Robot Skill은 실제 시스템이 아닌 deterministic fake입니다.
- Robot Skill 결과는 typed `SUCCESS`/`FAILURE`와 action status로 반환되며, raw ROS command·trajectory·physical execution은 없습니다.

MVP-003에서 검증한 대표 동작은 다음입니다.

- canonical part `Brake ECU Type-B`의 재고가 `Rack A19`에서 조회됩니다.
- Robot Skill 요청은 strict envelope로 검증됩니다.
- 같은 `action_id` 요청은 동일 결과를 반환해 action-level idempotency를 보장합니다.
- malformed request, unknown action, extra field는 typed failure 또는 validation error로 처리됩니다.
- execution layer API, ROS/Nav2/MoveIt/VLA, persistence, retry/recovery는 포함하지 않습니다.

즉, TASK-MVP-003는 “Agent의 semantic mission”과 “실행 가능한 typed tool boundary” 사이를 안전하게 연결한 작업이며, 이후 TASK-MVP-004가 이 action 결과 중 timeout/unknown 상태를 reconciliation과 bounded retry로 확장했습니다.
