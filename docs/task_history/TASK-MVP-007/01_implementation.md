# Implementation — TASK-MVP-007

## 1. 작업 정보

- TASK: `TASK-MVP-007`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: `2026-08-29`
- 시작 시 Repository 상태: TASK-MVP-001~006은 automation history상 `ACCEPTED`; TASK-MVP-007은 `NOT STARTED`.
- 선행 조건: `TASK-P0-002 = GO`, TASK-MVP-006 `ACCEPT`, frozen one failure/one recovery invariant.

## 2. 작업 목적

canonical mission을 Factory Agent와 WMS fake success 뒤 frozen ambiguous Robot Skill timeout으로 실행하고, reconciliation 뒤 one bounded retry가 `COMPLETED`로 끝나는 E2E evidence를 생성한다.

## 3. 구현 범위

### 구현한 내용

- `CanonicalFailureRecoveryE2EExecutor`가 existing Factory Agent, `Rack A19` inventory query, `SingleFailureRecoveryCoordinator`를 순서대로 구성한다.
- existing timeout fixture의 one timeout → `UNKNOWN` → reconciliation → `FAILED/retryable` → `RECOVERING` → one retry → `SUCCEEDED` sequence를 재사용한다.
- existing SQLite/JSONL recovery artifacts를 task-required `results/mvp/failure_recovery/latest.json` wrapper와 연결한다.

### 명시적으로 구현하지 않은 내용

- inventory mismatch, PHM, navigation blockage, VLA failure, second failure/recovery, ROS 2, VLA, physical execution, MVP-008.

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/mission_runtime/failure_recovery.py` | canonical Agent/WMS/recovery composition 및 latest evidence writer |
| `tests/test_failure_recovery_e2e.py` | one timeout, reconciliation-before-retry, one retry, durable evidence assertions |
| `results/mvp/failure_recovery/latest.json` | task-required latest E2E failure/recovery output |
| `results/mvp/runs/mvp-007-canonical-failure-recovery-20260829T000000Z/` | SQLite/JSONL/summary run artifacts |
| `results/mvp/MVP-007.json` | current workspace provenance, run assertion, Exit Criteria evidence |

## 5. 주요 구현 내용

WMS fake가 `Rack A19`와 sufficient quantity를 반환하지 않으면 `FailureRecoveryMissionError`로 중단한다. 그 뒤 recovery coordinator는 existing deterministic timeout fake만 통해 physical ambiguity를 `UNKNOWN`으로 보존하고 action-status reconciliation 후 exactly one retry를 수행한다. normal E2E와 달리 this task has two logical transfer attempts: initial ambiguous timeout attempt and one recovery retry; `extra_execution_count = 0`은 frozen trace 밖 dispatch가 없다는 뜻이다.

## 6. 주요 설계 판단

- retry/reconciliation policy나 SQLite schema를 중복 구현하지 않고 TASK-MVP-004/005의 accepted deterministic runtime/persistence ownership을 사용했다.
- `failure_recovery/latest.json`은 WMS success context와 durable artifact paths를 제공하고, state transition source of truth는 SQLite/JSONL recovery artifact로 유지했다.
- fixture-derived timestamp difference는 physical latency 또는 recovery-rate claim이 아니다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_failure_recovery_e2e.py -v` | 2 PASS, 0 FAIL |
| Regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 49 PASS, 0 FAIL |
| Syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |
| Artifact validation | JSON/JSONL parse, SQLite transition query, SHA-256 recomputation | PASS |
| Diff integrity | `git diff --check` 및 intended untracked text file check | PASS |

## 8. Exit Criteria

- exactly one failure injected — PASS
- exactly one recovery attempt — PASS
- reconciliation precedes retry — PASS
- final mission completes — PASS
- evidence proves the sequence — PASS
- all previous regression tests pass — PASS

## 9. Evidence

- 경로: `../../../results/mvp/MVP-007.json`
- 상태: PASS

## 10. 구현 결과

`TASK-MVP-007 is complete.`

## 11. 다음 단계

Independent Read-only Review로 `TASK-MVP-007` acceptance를 판단한다. MVP-008은 시작하지 않는다.
