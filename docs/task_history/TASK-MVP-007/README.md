# TASK-MVP-007 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-007`
- 목표: canonical single failure/recovery E2E run을 evidence로 검증한다.
- 구현 범위: Agent/WMS success, frozen timeout, reconciliation, one retry, SQLite/JSONL evidence.
- 주요 비범위: additional failure scenarios, ROS 2/VLA/physical hardware, MVP-008.
- 관련 Context / Plan / Contract: `tasks/TASK-MVP-007.md`, `plans/day10_mvp_scope_v1.md`, `docs/contracts/contract_plan.md`, `ADR-007`, `ADR-008`, `ADR-009`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | WMS success → one timeout → reconciliation → one retry → COMPLETED | `01_implementation.md` |
| 02 | Review | REJECT | E2E wrapper가 WMS/recovery artifact correlation을 fail-closed 검증하지 않음 | `02_review.md` |
| 03 | Fix | READY FOR INDEPENDENT RE-REVIEW | immutable inventory call과 strict wrapper/artifact correlation validation | `03_fix.md` |
| 04 | Review | ACCEPT | tamper rejection, one-timeout/one-retry sequence, evidence provenance 검증 | `04_review.md` |

## 3. 주요 설계 / 문제 해결 포인트

- timeout은 success/failure로 추측되지 않고 `UNKNOWN` 후 reconciliation을 거친다.
- initial timeout attempt와 recovery retry 외 transfer dispatch는 없으며, retry budget은 existing deterministic state machine이 소유한다.
- evidence는 deterministic fixture run이며 physical operational metric을 주장하지 않는다.

## 4. 검증 결과

- Focused tests: 2 PASS
- Full regression: 49 PASS
- Evidence: `../../../results/mvp/MVP-007.json`
- Final review: `ACCEPT TASK-MVP-007`

## 5. 최종 상태

`ACCEPT TASK-MVP-007`

## 6. 포트폴리오 요약

TASK-MVP-007은 canonical part supply flow에 Day-10의 유일한 timeout failure와 one bounded recovery를 결합했다. 그러나 independent review는 WMS context와 durable recovery artifact를 임의로 결합해도 latest evidence가 생성되는 correlation bypass를 발견했다. acceptance 전 wrapper validation과 tamper regression이 필요하다.

## 7. Explain TASK-MVP-007

TASK-MVP-007은 Day-10 MVP의 **단일 실패 복구 경로**를 증명한 작업입니다.

정상 흐름(MVP-006)에서 한 단계 확장해, 같은 미션에서 로봇 스킬이 한 번 timeout 되는 상황을 재현했습니다.

```text
한국어 미션
→ Factory Agent / MissionRequest
→ WMS Rack A19 재고 확인
→ 로봇 이송 1차 시도: TIMEOUT
→ 상태 재조정(reconciliation)
→ 정확히 1회 재시도
→ 성공 및 COMPLETED
→ SQLite + JSONL + 증거 JSON
```

핵심 제약은 다음과 같습니다.

- 실패 주입은 정확히 1회
- 재조정은 정확히 1회
- 재시도는 정확히 1회
- 추가 retry, 복수 실패, 실제 로봇 실행은 구현하지 않음
- ROS 2, Nav2, MoveIt, VLA, 물리 하드웨어는 범위 밖

초기 검토에서 실패 복구 증거 wrapper가 WMS 호출의 `request_id` 상관관계를 충분히 검증하지 않는 HIGH 문제가 발견되었습니다. 수정 후에는 `AttemptedToolCall`과 `InventoryResult`의 request ID, 버전, timestamp를 교차 검증하므로, 상관관계가 변조된 증거는 저장 전에 거부됩니다.

최종 검증은 focused E2E 3건과 전체 회귀 50건이 모두 PASS였고, 독립 재검토에서 ACCEPT 되었습니다. 관련 산출물은 다음과 같습니다.

- [실패 복구 증거](results/mvp/failure_recovery/latest.json)
- [TASK evidence](results/mvp/MVP-007.json)
- [최종 독립 검토](docs/task_history/TASK-MVP-007/04_review.md)

즉, MVP-007은 “실패 없이 성공”이 아니라, 제한된 운영 정책 안에서 timeout을 감지하고 상태를 확인한 뒤 단 한 번만 안전하게 복구하는 수직 슬라이스입니다.