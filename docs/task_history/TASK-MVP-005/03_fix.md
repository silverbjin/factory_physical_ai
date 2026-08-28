# Fix — TASK-MVP-005

## 1. 수정 정보

- TASK: `TASK-MVP-005`
- 작업 유형: Review Finding Fix
- 실행 순번: `03`
- 기준 Review: `02_review.md` — `REJECT TASK-MVP-005`
- 수정 대상 Severity: `HIGH`, acceptance-gate를 막는 `MEDIUM`
- `GIT_HISTORY_STATUS`: `NO HISTORY ACTION REQUIRED`

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-MVP-005-REV-H01` | HIGH | JSONL/SQLite evidence에 attempted-call `request_id` 및 JSONL `component_version` 누락 | FIXED |
| `TASK-MVP-005-REV-M01` | MEDIUM | `tool_call_valid`가 caller-supplied default boolean | FIXED |

## 3. 원인 분석

기존 `RecoveryRun`은 textual `call_trace`만 갖고 attempted dispatch/reconciliation/retry request metadata를 보존하지 않았다. 따라서 persistence layer는 action ID만으로 JSONL event를 만들었고, per-attempt `request_id`와 emitting component version을 reconstruct할 수 없었다. 같은 이유로 `tool_call_valid`도 validated trace가 아닌 writer parameter에서 전달받았다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `src/mission_runtime/recovery.py` | immutable `AttemptedToolCall`을 도입하고 `RecoveryRun.attempted_calls`에 transfer/reconciliation/retry의 `request_id`, `action_id`, operation, component version, timestamp를 보존 | `TASK-MVP-005-REV-H01` |
| `src/mission_runtime/persistence.py` | `attempted_calls` SQLite table과 strict trace validation을 추가했다. 모든 JSONL event와 summary가 `request_id`, `action_id`, operation, `component_version`를 emit/reconstruct하며 `tool_call_valid`는 validated trace 통과 뒤에만 derive된다. | `TASK-MVP-005-REV-H01`, `TASK-MVP-005-REV-M01` |
| `tests/test_recovery.py` | canonical recovery의 attempted-call correlation trace를 검증 | `TASK-MVP-005-REV-H01` |
| `tests/test_persistence.py` | every JSONL event의 request/action/component correlation 및 malformed attempted-call trace rejection regression을 추가 | `TASK-MVP-005-REV-H01`, `TASK-MVP-005-REV-M01` |
| `results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/` | correlation-bearing SQLite/JSONL/summary artifacts로 재생성 | `TASK-MVP-005-REV-H01` |
| `results/mvp/MVP-005.json` | source/test/artifact hashes, test counts, attempted-call provenance, fixed finding claim을 갱신 | `TASK-MVP-005-REV-H01`, `TASK-MVP-005-REV-M01` |

## 5. 추가/강화한 테스트

- `test_timeout_reconciles_once_then_retry_succeeds`는 three attempted calls의 ordered `request_id`/`action_id`/operation/`component_version`를 검증한다.
- `test_jsonl_trace_is_parseable_and_evidence_reconstructs_run`은 every JSONL event의 `request_id`, `action_id`, `mission_id`, `component_version`를 검증한다.
- `test_tool_call_validity_is_derived_from_a_strict_attempted_call_trace`은 malformed request UUID trace가 `PersistenceValidationError`로 artifact generation을 fail-closed 처리하는지 검증한다.

## 6. 테스트 결과

| 검증 | 결과 |
|---|---|
| Focused tests: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_recovery.py tests/test_persistence.py -v` | 8 PASS, 0 FAIL |
| Full regression: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 44 PASS, 0 FAIL |
| Syntax/static: `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |
| JSON/JSONL/trace correlation verification | PASS |
| `git diff --check` 및 intended untracked text file integrity | PASS |

## 7. Evidence 갱신

- Evidence: `../../../results/mvp/MVP-005.json`
- SHA-256: `c0e15adc3e13ca0848d1b18fd9f3c473a2ccee7f0f0daab6d89da6805c08560d`
- 상태: PASS
- 변경된 claim: every JSONL event와 SQLite `attempted_calls` record가 immutable attempted-call correlation/version metadata를 보존하며 `tool_call_valid`는 strict trace validation에서 derive됨.

## 8. 남은 Findings

없음. Independent re-review에서 contract/evidence completeness를 다시 판단해야 한다.

## 9. History Action

`No history action required.`

## 10. 수정 결과

`TASK-MVP-005 fixes are ready for independent re-review.`
