# TASK-MVP-006 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-006`
- 목표: canonical normal mission을 operator text부터 SQLite/JSON evidence까지 실행한다.
- 구현 범위: FactoryAgent → WMS fake → successful Robot Skill fake → `COMPLETED` → local evidence.
- 주요 비범위: failure/recovery, ROS 2, VLA, physical hardware, MVP-007.
- 관련 Context / Plan / Contract: `tasks/TASK-MVP-006.md`, `plans/day10_mvp_scope_v1.md`, `docs/architecture/system_architecture_v1.md`, `docs/contracts/contract_plan.md`, `ADR-006`, `ADR-008`, `ADR-009`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | canonical text → Rack A19 → one successful transfer → COMPLETED → SQLite/JSONL/JSON | `01_implementation.md` |
| 02 | Review | REJECT | attempted-call `request_id`와 component result correlation을 persistence가 교차 검증하지 않음 | `02_review.md` |
| 03 | Fix | READY FOR INDEPENDENT RE-REVIEW | strict attempted-call/result correlation validation 및 tamper regression 추가 | `03_fix.md` |
| 04 | Review | ACCEPT | normal path, strict evidence correlation, regression/evidence hash를 independent re-review에서 검증 | `04_review.md` |

## 3. 주요 설계 / 문제 해결 포인트

- normal path는 existing strict Agent, tool, state, persistence boundaries를 연결할 뿐 retry/recovery policy를 새로 구현하지 않는다.
- one logical transfer 및 no-timeout/retry outcome은 focused test와 machine-readable run artifact 모두에서 검증한다.
- local evidence는 deterministic fixture-derived 결과이며 physical execution 또는 measured performance claim이 아니다.

## 4. 검증 결과

- Focused tests: 2 PASS
- Full regression: 46 PASS
- Evidence: `../../../results/mvp/MVP-006.json`
- Final review: `ACCEPT TASK-MVP-006`

## 5. 최종 상태

`ACCEPT TASK-MVP-006`

## 6. 포트폴리오 요약

TASK-MVP-006은 Korean line-side supply request를 existing Factory Agent와 typed factory-tool gateway를 통해 canonical normal completion으로 연결했다. `Rack A19` inventory observation 뒤 정확히 한 번의 fake transfer가 실행되고 mission은 retry 없이 `COMPLETED`가 된다. Independent review가 발견한 valid-shaped attempted-call `request_id` 변조 evidence bypass는 typed inventory/transfer result와 immutable attempted-call trace를 cross-check하는 persistence validation 및 regression test로 보완했다. final independent re-review는 normal path, strict correlation, SHA-256 provenance, 47-test regression을 다시 검증하여 `ACCEPT`했다.

## 7. Explain TASK-MVP-006

`TASK-MVP-006`은 Day-10 MVP의 정상 경로를 처음으로 end-to-end 검증한 작업입니다.

흐름은 다음과 같습니다.

```text
Korean operator mission
→ Factory Agent
→ validated MissionRequest
→ WMS fake: Rack A19
→ Robot Skill fake: one transfer
→ Mission COMPLETED
→ SQLite + JSONL/JSON evidence
```

검증한 핵심 조건:

- `Brake ECU Type-B`, 수량 `1`, 목적지 `Line B` 파싱
- inventory source는 `Rack A19`
- logical transfer는 정확히 1회
- timeout 없음, reconciliation 없음, retry count `0`
- mission 최종 상태 `COMPLETED`
- SQLite lifecycle 및 JSONL/JSON artifact로 run 재구성 가능

중요한 품질 보완도 있었습니다. 첫 review에서 attempted-call `request_id`가 typed tool result와 달라도 `tool_call_valid = true` evidence가 만들어질 수 있음을 발견했습니다. 수정 후 persistence가 mission/action/request ID, component version, timestamp, result kind를 교차 검증하고, 변조된 run은 `PersistenceValidationError`로 fail-closed 처리합니다.

결과물:

- [normal E2E evidence](/home/jinho/projects/factory_physical_ai/results/mvp/normal_e2e/latest.json)
- [TASK-MVP-006 evidence](/home/jinho/projects/factory_physical_ai/results/mvp/MVP-006.json)
- [accepted review](/home/jinho/projects/factory_physical_ai/docs/task_history/TASK-MVP-006/04_review.md)

ROS 2, Nav2, MoveIt, VLA, physical robot, real WMS, timeout/recovery behavior는 이 task에 포함하지 않았습니다.