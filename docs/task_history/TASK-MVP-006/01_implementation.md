# Implementation — TASK-MVP-006

## 1. 작업 정보

- TASK: `TASK-MVP-006`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: `2026-08-28`
- 시작 시 Repository 상태: TASK-MVP-001~005는 global/per-task history상 `ACCEPTED`였고, TASK-MVP-006~008은 시작되지 않았다.
- 선행 조건: `results/phase0/P0-002_architecture_freeze.json`의 `status = GO`; TASK-MVP-005 `ACCEPT` 및 SQLite/JSONL evidence boundary 사용 가능.

## 2. 작업 목적

canonical Korean operator text `Line B에 Brake ECU Type-B 1개를 공급해줘.`를 `FactoryAgent` semantic boundary부터 deterministic WMS/Robot Skill fake, `MissionStatus.COMPLETED`, SQLite, JSONL/JSON evidence까지 한 번의 정상 경로로 실행한다.

## 3. 구현 범위

### 구현한 내용

- `CanonicalNormalMissionExecutor`가 existing `FactoryAgent`, `FactoryToolGateway`, `MissionRecord`, `ActionRecord` 경계를 순서대로 연결한다.
- inventory observation이 `Rack A19`와 충분한 수량을 반환해야만 one logical `transfer_part`를 dispatch한다.
- normal path는 `CREATED → READY → EXECUTING → COMPLETED`, `REQUESTED → EXECUTING → SUCCEEDED`, `retry_count = 0`, `timeout_detected = false`만 허용한다.
- 기존 SQLite schema에 normal-run persistence와 JSONL/JSON artifact writer를 추가했다.
- `results/mvp/normal_e2e/latest.json` 및 run-scoped SQLite/JSONL/summary artifact를 생성했다.

### 명시적으로 구현하지 않은 내용

- timeout/reconciliation/retry recovery fixture, ROS 2, Nav2, MoveIt, VLA, physical robot, real WMS, hosted provider, Docker, PostgreSQL, telemetry stack, MVP-007.

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/mission_runtime/normal.py` | canonical normal-path coordinator, immutable `NormalRun`, deterministic service metadata fixture |
| `src/mission_runtime/persistence.py` | normal-run SQLite persistence, JSONL/JSON run artifacts, `normal_e2e/latest.json` writer |
| `tests/test_normal_e2e.py` | canonical E2E fields, Rack A19, exactly one transfer, no timeout/retry, evidence reconstruction test |
| `results/mvp/normal_e2e/latest.json` | task-required latest normal E2E output |
| `results/mvp/runs/mvp-006-canonical-normal-20260829T000000Z/` | SQLite, JSONL trace, machine-readable summary |
| `results/mvp/MVP-006.json` | source/test/artifact provenance 및 Exit Criteria evidence |

## 5. 주요 구현 내용

`CanonicalNormalMissionExecutor.run()`은 `FactoryAgent.parse_mission()`의 validated `MissionRequest`를 입력으로 사용한다. executor는 inventory query와 transfer에 별도 `request_id`를 사용하고, side effect에는 하나의 `action_id`/`idempotency_key`를 유지한다. `DeterministicRobotSkillFake`의 default successful fixture만 사용했으며 test-only counter가 `transfer_part` dispatch가 정확히 한 번인지 검증한다.

`MissionLifecycleStore.persist_normal_run()`은 canonical fields, component correlation, transition sequence, one inventory query + one transfer attempted-call trace를 validate한 뒤에만 `tool_call_valid = true`를 기록한다. run summary는 `timeout_detected = false`, `reconciliation_performed = false`, `retry_count = 0`, `recovery_result = NOT_REQUIRED`를 기록한다.

## 6. 주요 설계 판단

- MVP-005의 SQLite/event schema를 재사용해 durable lifecycle/evidence ownership을 한 곳에 유지했다.
- normal path module을 `mission_runtime.__init__`에서 re-export하지 않았다. 기존 `factory_tools → mission_runtime.state` import chain에 순환 의존을 만들지 않는 explicit `mission_runtime.normal` boundary를 유지한다.
- fixture-derived 5,000 ms duration은 physical latency claim이 아니라 deterministic evidence timestamp difference다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_normal_e2e.py -v` | 2 PASS, 0 FAIL |
| Regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 46 PASS, 0 FAIL |
| Syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |
| Artifact validation | JSON/JSONL parse, SQLite query/reload, source/test/artifact SHA-256 recomputation | PASS |
| Diff integrity | `git diff --check` 및 intended untracked text file check | PASS |

## 8. Exit Criteria

- normal mission passes from text input through evidence output — PASS
- no failure fixture is enabled — PASS
- one transfer only — PASS
- final state COMPLETED — PASS
- regression tests from MVP-001~005 pass — PASS

## 9. Evidence

- 경로: `../../../results/mvp/MVP-006.json`
- SHA-256: `93574bacbea3d787c262d3e8762c303f9b2d509d0f60a668d2d6ffb1f548a6d2`
- 상태: PASS

## 10. 구현 결과

`TASK-MVP-006 is complete.`

## 11. 다음 단계

Independent Read-only Review로 `TASK-MVP-006` acceptance를 판단한다. MVP-007은 시작하지 않는다.
