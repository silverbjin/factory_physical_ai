# Implementation — TASK-MVP-004

## 1. 작업 정보

- TASK: `TASK-MVP-004`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: `2026-08-28`
- 선행 조건: `TASK-P0-002 = GO`, `TASK-MVP-003 = ACCEPT`

## 2. 작업 목적

Robot Skill의 첫 timeout을 `UNKNOWN`으로 보존하고, reconciliation 결과가 retryable일 때만 deterministic runtime이 정확히 한 번 retry하도록 구현한다.

## 3. 구현 범위

### 구현한 내용

- `DeterministicTimeoutRecoverySkillFake`의 단일 scripted timeout/reconciliation/success path
- `SingleFailureRecoveryCoordinator`의 runtime-owned retry policy
- `UNKNOWN -> RECONCILING -> RECOVERING -> COMPLETED` 상태 sequence와 non-retryable escalation regression

### 명시적으로 구현하지 않은 내용

- physical robot, ROS 2, Nav2, MoveIt, VLA, Agent integration, persistence, SQLite, external process/network, MVP-005

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/factory_tools/gateway.py` | timeout/reconciliation fixture 추가 |
| `src/factory_tools/__init__.py` | fixture export 추가 |
| `src/mission_runtime/recovery.py` | deterministic recovery coordinator 추가 |
| `tests/test_recovery.py` | canonical recovery 및 policy regression 검증 |
| `results/mvp/MVP-004.json` | machine-readable test evidence |

## 5. 주요 설계 판단

retry budget은 `SingleFailureRecoveryCoordinator._RETRY_BUDGET`가 소유하며 caller나 Agent가 전달할 수 없다. retry 전 `get_action_status`를 반드시 호출하도록 fixture가 강제한다. retry dispatch는 동일 `mission_id`와 `idempotency_key`를 유지하고 새 `action_id`를 사용한다.

## 6. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_recovery.py -v` | 3 PASS |
| Regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 39 PASS |
| Syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |

## 7. Exit Criteria

- one failure only — PASS
- UNKNOWN/reconciliation observable — PASS
- retry bounded — PASS
- final result deterministic — PASS
- no duplicate/unbounded execution — PASS
- tests pass — PASS

## 8. Evidence

- 경로: `../../../results/mvp/MVP-004.json`
- 상태: PASS

## 9. 구현 결과

`TASK-MVP-004 is complete.`

## 10. 다음 단계

Independent Read-only Review가 필요하다.
