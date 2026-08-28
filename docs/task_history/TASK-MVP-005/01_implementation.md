# Implementation — TASK-MVP-005

## 1. 작업 정보

- TASK: `TASK-MVP-005`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: `2026-08-28`
- 시작 시 Repository 상태: task implementation/test/evidence 파일은 없었고, prior TASK history backfill은 repository history에 보존되어 있었다.
- 선행 조건: `TASK-P0-002 = GO`; frozen invariant `1 Mission + 1 Failure + 1 Recovery + Evidence`; `TASK-MVP-004`의 deterministic timeout/reconciliation/retry lifecycle 사용 가능
- base commit: `d8a8b4d317583999d18cacd17972453f5b2364cf`

## 2. 작업 목적

canonical timeout/reconciliation/retry mission lifecycle을 single-process SQLite에 보존하고, 실행을 재구성할 수 있는 JSONL/JSON artifact를 `results/mvp/runs/<run_id>/`에 생성한다. 이를 통해 restart/reload 시 `UNKNOWN` action transition이 success로 변환되지 않음을 deterministic test로 증명한다.

## 3. 구현 범위

### 구현한 내용

- `MissionLifecycleStore`의 SQLite schema와 atomic canonical recovery-run persistence
- mission/action final records, mission/action state transitions, idempotency key, deadline/timestamp, reconciliation event, retry count, final result 저장
- `load_action_state()`를 통한 durable action transition reload; `UNKNOWN` snapshot은 해석 없이 `UNKNOWN`으로 반환
- `write_run_artifacts()`의 `lifecycle.sqlite3`, `trace.jsonl`, `summary.json` output
- one deterministic canonical run artifact: `results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/`
- SQLite schema/lifecycle, reload, JSONL parse/reconstruction, UUID correlation regression tests

### 명시적으로 구현하지 않은 내용

- PostgreSQL, OpenTelemetry collector, Prometheus, Grafana, Docker Compose, cloud/service telemetry
- physical robot, ROS 2, Nav2, MoveIt, `ros2_control`, VLA, real WMS/Fleet/PHM, external process/network
- additional failure scenarios, retry-policy changes, Agent functionality, MVP-006

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/mission_runtime/persistence.py` | SQLite lifecycle store, reload API, JSONL/JSON artifact writer |
| `tests/test_persistence.py` | schema, persistence, UNKNOWN reload, JSONL reconstruction, correlation-ID tests |
| `results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/lifecycle.sqlite3` | canonical fixture-derived durable lifecycle database |
| `results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/trace.jsonl` | timeout/reconciliation/recovery structured event trace |
| `results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/summary.json` | machine-readable reconstructed run summary |
| `results/mvp/MVP-005.json` | implementation evidence manifest and artifact hashes |

## 5. 주요 구현 내용

`MissionLifecycleStore`는 `runs`, `missions`, `actions`, `mission_transitions`, `action_transitions`, `events` table을 생성한다. canonical `RecoveryRun`을 하나의 SQLite transaction으로 기록하고 `summary.json`의 required fields인 `run_id`, `mission_id`, `action_ids`, `mission_result`, `tool_call_valid`, `state_transitions`, `timeout_detected`, `reconciliation_performed`, `retry_budget`, `retry_count`, `recovery_result`, `hitl_escalated`, `mission_duration_ms`, `error_category`, `component_versions`를 생성한다.

`load_action_state()`는 stored transition row를 `PersistedActionState`로 재구성할 뿐 state transition policy를 다시 적용하지 않는다. 따라서 first action의 ordinal `2` snapshot은 restart/reload 뒤에도 `ActionStatus.UNKNOWN`으로 유지된다.

`trace.jsonl`은 `timeout_detected`, `reconciliation_performed`, `recovery_completed` event를 parseable JSONL로 기록한다. 이 artifact는 deterministic fixture-derived output이며 physical robot result 또는 physical latency measurement를 주장하지 않는다.

## 6. 주요 설계 판단

- persistence/observability는 `ADR-008`, `ADR-009`에 따라 SQLite와 JSONL/JSON에 한정하고, production telemetry stack을 추가하지 않았다.
- retry/reconciliation policy는 기존 `SingleFailureRecoveryCoordinator`와 `MissionRecord`가 계속 소유한다. MVP-005는 policy를 변경하지 않고 observed lifecycle을 durable record로 남긴다.
- run summary는 SQLite에서 재구성 가능하도록 state transitions와 correlation IDs를 중복 보존한다. JSONL은 audit-friendly event stream이고 SQLite는 authoritative local lifecycle store이다.
- deterministic timestamp window는 fixture evidence의 reproducibility용이며, `mission_duration_ms = 5000`은 physical latency metric이 아니다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused persistence test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_persistence.py -v` | 4 PASS, 0 FAIL |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 43 PASS, 0 FAIL |
| Syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |
| JSON/JSONL validation | `python3 -m json.tool` 및 line-by-line `json.loads` | PASS |
| SQLite reconstruction | `test_unknown_transition_remains_unknown_after_database_reload`, `test_jsonl_trace_is_parseable_and_evidence_reconstructs_run` | PASS |
| Whitespace/integrity | `git diff --check` 및 intended untracked text file마다 `git diff --no-index --check /dev/null` | PASS |

## 8. Exit Criteria

- SQLite persistence works — PASS
- evidence is machine-readable — PASS
- run can be reconstructed from persisted evidence — PASS
- restart/reload test passes — PASS
- no production telemetry stack introduced — PASS

## 9. Evidence

- 경로: `../../../results/mvp/MVP-005.json`
- SHA-256: `727d02ce931b516f28b52a925d8aceae1778187d01f9e39e8f766290441e3233`
- 상태: PASS
- canonical run artifacts: `../../../results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/`
- source/test snapshot:
  - `src/mission_runtime/persistence.py`: `a5446038a84e1dafdb6885f8c744d567610a3630279a46458315fc4ba91d230a`
  - `tests/test_persistence.py`: `7739bae4fe3f990c657188b873b8dcc3e08767d9282d3304477604ae56655295`

## 10. 구현 결과

`TASK-MVP-005 is complete.`

## 11. 다음 단계

Independent Read-only Review가 필요하다. MVP-006은 시작하지 않았다.
