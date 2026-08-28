# Implementation — TASK-MVP-002

## 1. 작업 정보

- TASK: `TASK-MVP-002`
- 작업 유형: Implementation history backfill
- 실행 순번: `01`
- 원 구현 일자: `2026-08-28`부터 `2026-08-29`까지
- 이력 보강 일자: `2026-08-29`
- 시작 시 Repository 상태: 구현 결과와 evidence는 Git history 및 `results/mvp/MVP-002.json`에 존재했으나 `docs/task_history/TASK-MVP-002/` 기록은 없었다.
- 선행 조건: `TASK-P0-002 = GO`
- 구현 provenance: `06fded7b3a4145d64280c384cd72167cabd70ded` (`feat(mvp): define durable mission and action state model`), 후속 invariant/test 정비 `ce828f1bf50feaf5a704f80fda603d397bffa552` (`test(mvp): define durable mission and action state model`)

## 2. 작업 목적

frozen Architecture v1.0이 요구하는 최소 deterministic mission/action state model을 구현한다. 이 모델은 physical action의 ambiguous result를 `UNKNOWN`으로 보존하고, reconciliation과 bounded recovery가 이후 TASK에서 안전하게 연결될 수 있는 finite transition table을 제공한다.

## 3. 구현 범위

### 구현한 내용

- `MissionStatus`: `CREATED`, `READY`, `EXECUTING`, `RECONCILING`, `RECOVERING`, `COMPLETED`, `ESCALATED`, `FAILED`의 finite mission lifecycle
- `ActionStatus`: `REQUESTED`, `EXECUTING`, `SUCCEEDED`, `FAILED`, `UNKNOWN`, `RECONCILING`의 physical-action lifecycle
- immutable `MissionRecord`와 `ActionRecord`, explicit transition table, `StateTransitionError`
- `UNKNOWN`을 success로 해석하지 않는 reconciliation semantics
- runtime-owned Day-10 one-retry limit과 non-retryable reconciliation의 `ESCALATED` terminal path
- UUID, non-blank string, UTC timestamp 및 lifecycle field validation

### 명시적으로 구현하지 않은 내용

- action dispatch, timeout/reconciliation I/O, evidence event emission, SQLite persistence
- physical robot, ROS 2, Nav2, MoveIt, VLA, hosted LLM SDK, Docker, PostgreSQL, Grafana, multi-agent
- `TASK-MVP-003` 이후의 Factory Tool gateway 또는 execution functionality

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/mission_runtime/__init__.py` | mission runtime public import surface 제공 |
| `src/mission_runtime/state.py` | immutable mission/action record와 finite transition table 구현 |
| `tests/test_mission_runtime.py` | state transition 및 invariant regression 검증 |
| `results/mvp/MVP-002.json` | transition test와 implementation provenance의 machine-readable evidence |

## 5. 주요 구현 내용

`MissionRecord.transition()`은 허용된 mission transition만 통과시키며, `RECOVERING -> EXECUTING`에서만 retry count를 소비하고 Day-10 limit `1`을 초과하면 `StateTransitionError`로 fail-closed 처리한다. `ActionRecord.transition()`은 action outcome을 constructor로 주입하거나 terminal state를 우회하지 못하게 한다.

`MissionRecord.apply_action_observation()`은 `EXECUTING + UNKNOWN`을 반드시 `RECONCILING`으로, reconciliation 후 `FAILED` observation을 retryable 여부에 따라 `RECOVERING` 또는 `ESCALATED`로 매핑한다. 따라서 Agent 또는 caller가 임의의 success/action outcome을 직접 기록할 수 없다.

## 6. 주요 설계 판단

- state model은 external adapter와 분리된 순수 in-memory, immutable value object로 유지했다. physical result를 추론하거나 ROS/VLA 구현에 결합하지 않는다.
- retry budget은 caller parameter가 아니라 `MissionRecord._RETRY_LIMIT`라는 deterministic runtime invariant로 제한했다.
- action lifecycle에는 contract correlation field인 `mission_id`, `action_id`, `idempotency_key`, `schema_version`, `timestamp`, `deadline`, `component_version`을 포함했다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| 당시 focused transition test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_mission_runtime.py -v` | 12 PASS (`MVP-002.json` measured result) |
| 당시 full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 28 PASS (`MVP-002.json` measured result) |
| 당시 syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS (`MVP-002.json` measured result) |
| 당시 task-file whitespace 검증 | `git diff --no-index --check /dev/null`을 intended TASK-MVP-002 file마다 수행 | PASS (`MVP-002.json` measured result) |
| 이력 보강 시 focused recheck | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_mission_runtime.py -v` | 12 PASS |

`MVP-002.json`은 repository-wide `git diff --check`가 task 외부의 `AGENTS.md` trailing blank-line warning 때문에 `NOT_PASS`였음을 명시한다. 이는 TASK-MVP-002 변경이 아닌 pre-existing warning이며, task-file integrity claim과 혼동하지 않는다.

## 8. Exit Criteria

- finite mission transition table implemented — PASS
- action lifecycle implemented — PASS
- reconciliation semantics explicit — PASS
- invalid transitions rejected — PASS
- one HITL/escalation state supported — PASS
- tests pass — PASS
- evidence generated — PASS

## 9. Evidence

- 경로: `../../../results/mvp/MVP-002.json`
- SHA-256: `0c493493c99697b14944ae33f156a007f2ade8abce66a3a20b5cea19c77cc3c5`
- 상태: implementation evidence의 measured result는 PASS
- source/test snapshot hash는 evidence에 다음과 같이 기록되어 있고 현재 파일과 일치한다.
  - `src/mission_runtime/__init__.py`: `c58cca0a3db7cb011a8e508cb22d9c1284c01830cf700d66587511315be618ec`
  - `src/mission_runtime/state.py`: `207782244144f5780698c0cb60bbe9cf6acb806936ecb540191660e88491e99c`
  - `tests/test_mission_runtime.py`: `7949c3657e8a03c5cc29d9c354b4275f13e9ff7e560eaa29e73625c8b50c1f95`

## 10. 구현 결과

`TASK-MVP-002 is complete.`

## 11. 다음 단계

독립 Read-only Review 기록은 이력 보강 범위에 포함하지 않았다. 이후 review workflow가 별도로 실행될 때 acceptance 결과를 추가한다.
