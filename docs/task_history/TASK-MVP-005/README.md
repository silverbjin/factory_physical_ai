# TASK-MVP-005 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-005`
- 목표: canonical mission/action lifecycle을 SQLite에 persist하고 reconstructable JSONL/JSON evidence를 생성한다.
- 구현 범위: single-process SQLite store, transition reload, fixture-derived run artifacts, machine-readable evidence.
- 주요 비범위: production telemetry, external services, ROS 2/VLA/physical execution, MVP-006.
- 관련 Context / Plan / Contract: `tasks/TASK-MVP-005.md`, `plans/day10_mvp_scope_v1.md`, `docs/architecture/system_architecture_v1.md`, `docs/contracts/contract_plan.md`, `ADR-008`, `ADR-009`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | SQLite lifecycle persistence, UNKNOWN reload, JSONL/JSON canonical-run evidence | `01_implementation.md` |
| 02 | Review | REJECT | JSONL/SQLite evidence에 attempted-call `request_id` 및 JSONL `component_version` 누락 | `02_review.md` |
| 03 | Fix | READY FOR INDEPENDENT RE-REVIEW | immutable attempted-call trace, JSONL/SQLite correlation/version, derived `tool_call_valid` | `03_fix.md` |
| 04 | Review | ACCEPT | correlation/version 및 derived `tool_call_valid` provenance를 independent re-review에서 검증 | `04_review.md` |

## 3. 주요 설계 / 문제 해결 포인트

- `UNKNOWN` transition은 action final state와 별도로 durable transition snapshot으로 저장되어 restart/reload 뒤에도 success로 변환되지 않는다.
- SQLite가 local source of truth이고 `summary.json`과 `trace.jsonl`은 run reconstruction/audit artifact다.
- retry budget과 recovery policy는 persistence layer가 아니라 existing deterministic runtime이 소유한다.
- run artifact는 deterministic fixture evidence이며 physical execution/latency evidence가 아니다.

## 4. 검증 결과

- Focused tests: 8 PASS
- Full regression: 44 PASS
- Evidence: `../../../results/mvp/MVP-005.json`
- Final review: `ACCEPT TASK-MVP-005`

## 5. 최종 상태

`ACCEPT TASK-MVP-005`

## 6. 포트폴리오 요약

TASK-MVP-005는 timeout/reconciliation/retry lifecycle을 single-process SQLite에 저장하고, 동일 run을 JSONL event stream과 JSON summary로 재구성 가능하게 만들었다. 저장된 `UNKNOWN` action transition은 reload 후에도 `UNKNOWN`이며, ambiguous physical result를 success로 추론하지 않는다. 독립 review가 발견한 attempted-call `request_id`와 JSONL `component_version` 누락은 immutable `AttemptedToolCall` trace와 strict persistence validation으로 보완했다. `tool_call_valid`도 caller parameter가 아니라 이 validated trace에서 derive하도록 변경했으며, final independent re-review에서 source/test/artifact SHA-256과 full regression까지 재검증하여 `ACCEPT`했다.

## 7. Explain TASK-MVP-005

`TASK-MVP-005`는 Day-10 MVP의 단일 mission lifecycle을 **SQLite에 저장하고, 감사·재현 가능한 JSONL/JSON evidence로 남기는 작업**입니다.

핵심 흐름은 다음입니다.

```text
1 Mission
→ timeout으로 UNKNOWN
→ reconciliation
→ 1회 제한 retry
→ COMPLETED
→ SQLite + JSONL + JSON evidence
```

구현된 범위는 다음과 같습니다.

- mission/action record, 상태 전이, idempotency key, deadline, retry count, 최종 결과를 SQLite에 저장
- 재시작 후에도 `UNKNOWN` 상태가 `SUCCEEDED`로 잘못 해석되지 않도록 reload 검증
- 각 run에 `lifecycle.sqlite3`, `trace.jsonl`, `summary.json` 생성
- 최상위 evidence [`MVP-005.json`](/home/jinho/projects/factory_physical_ai/results/mvp/MVP-005.json) 생성
- attempted tool call별 `request_id`, `action_id`, operation, component version, timestamp 보존
- `tool_call_valid`는 외부 입력이 아니라 검증된 attempted-call trace에서만 derive

명시적 비범위는 PostgreSQL, Grafana/Prometheus/OpenTelemetry, Docker, ROS 2, VLA, 실제 로봇 실행, MVP-006입니다.

초기 독립 검토에서 correlation metadata와 `tool_call_valid` ownership 문제가 발견됐고, 수정 후 re-review에서 ACCEPT되었습니다. 최종 검토 기록은 [`04_review.md`](/home/jinho/projects/factory_physical_ai/docs/task_history/TASK-MVP-005/04_review.md)에 있습니다.