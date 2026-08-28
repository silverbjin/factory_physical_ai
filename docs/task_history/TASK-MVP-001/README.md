# TASK-MVP-001 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-001`
- 목표: canonical natural-language line-side supply mission을 validated structured mission으로 변환하는 Factory Agent semantic boundary를 구현한다.
- 구현 범위: provider abstraction, deterministic fake provider, typed proposal/request model, fail-closed schema validation.
- 주요 비범위: execution, WMS/Fleet/PHM, persistence, retry/recovery, ROS 2, VLA, physical hardware, MVP-002 이후 기능.
- 관련 Context / Plan / Contract: `tasks/TASK-MVP-001.md`, `plans/day10_mvp_scope_v1.md`, `docs/architecture/system_architecture_v1.md`, `docs/contracts/contract_plan.md`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | provider semantic proposal → service-owned metadata → validated `MissionRequest` | `01_implementation.md` |

## 3. 주요 설계 / 문제 해결 포인트

- provider output은 `MissionProposal`의 네 semantic field만 가지며, `request_id`와 `mission_id` 같은 runtime metadata는 `FactoryAgent` service가 소유한다.
- `MissionRequest`는 extra field, non-mapping input, blank string, invalid quantity/UUID/timestamp를 `MissionValidationError`로 fail-closed 처리한다.
- deterministic fake provider는 canonical mission에 대한 semantic proposal만 reproducible하게 만들며, timestamp/UUID는 semantic determinism으로 주장하지 않는다.
- Agent boundary는 raw ROS command, pose, trajectory 또는 execution command를 노출하지 않는다.

## 4. 검증 결과

- Focused tests: 이력 보강 시 16 PASS
- Unit/regression: 당시 measured 16 PASS
- Evidence: `../../../results/mvp/MVP-001.json`
- Final review: `TBD` — 이력 보강 범위에서는 implementation record만 추가했다.

## 5. 최종 상태

`IMPLEMENTATION COMPLETE / REVIEW HISTORY TBD`

## 6. 포트폴리오 요약

TASK-MVP-001은 Korean manufacturing mission을 provider-neutral semantic proposal과 deterministic validated request boundary로 분리했다. provider는 part, quantity, destination 같은 semantic intent만 만들고, application service가 UUID 및 UTC metadata를 생성한다. strict schema validation은 malformed/extra provider output을 fail-closed 처리하며 execution-layer command가 structured output에 스며들지 못하도록 한다. 이 작업은 이후 state model, factory-tool gateway, timeout reconciliation을 붙일 수 있는 최소 안전 경계를 제공한다.

## 7. Explain TASK-MVP-001

TASK-MVP-001은 전체 MVP의 시작점으로, 한국어 생산 물류 요청을 안전한 구조화 mission으로 바꾸는 Factory Agent 경계를 구현한 작업입니다.

```text
Natural-language mission
→ provider semantic proposal
→ FactoryAgent service
→ validated MissionRequest
```

Canonical input:

> `Line B에 Brake ECU Type-B 1개를 공급해줘.`

결과 mission에는 다음이 포함됩니다.

- `schema_version`
- `request_id`
- `mission_id`
- `mission_type`
- `part_id`
- `quantity`
- `destination`
- `requested_by`
- `created_at`

책임 분리는 명확합니다.

- `DeterministicFakeProvider`는 semantic field만 반환합니다:
  `mission_type`, `part_id`, `quantity`, `destination`.
- `FactoryAgent` service가 `request_id`, `mission_id`, `requested_by`, `created_at` 같은 runtime metadata를 생성합니다.
- `MissionProposal`과 `MissionRequest`가 strict schema validation을 수행합니다.

이 경계는 fail-closed입니다. 다음은 모두 `MissionValidationError`로 거부됩니다.

- `None`, list, tuple, string, integer 같은 non-mapping provider output
- 누락 또는 추가 field
- non-string mapping key
- 빈/공백 문자열
- `0`, 음수, bool, float, numeric string quantity
- 잘못된 UUID
- naive 또는 non-UTC timestamp
- `execution_command` 같은 실행 관련 extra field

검증 결과는 Factory Agent focused test 16개 PASS이며, evidence는 [MVP-001.json](/home/jinho/projects/factory_physical_ai/results/mvp/MVP-001.json)에 있습니다.

의도적으로 포함하지 않은 범위는 Robot Skill/WMS 실행, retry·timeout·reconciliation, persistence, ROS 2/Nav2/MoveIt, VLA, physical robot, hosted LLM SDK, LangGraph, Docker와 multi-agent입니다. 이후 TASK-MVP-002가 state model을, MVP-003이 typed factory-tool boundary를, MVP-004가 timeout recovery를 이 경계 위에 추가했습니다.