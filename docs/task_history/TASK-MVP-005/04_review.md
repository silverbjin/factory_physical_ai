# Read-only Review — TASK-MVP-005

## 1. 검토 정보

- TASK: `TASK-MVP-005`
- 작업 유형: Independent Read-only Review (Fix 후 re-review)
- 실행 순번: `04`
- 검토 대상: `src/mission_runtime/persistence.py`, `src/mission_runtime/recovery.py`, `tests/test_persistence.py`, `tests/test_recovery.py`, `results/mvp/MVP-005.json`, canonical run artifacts 및 관련 frozen contract/ADR
- 검토 시점 Git 상태: TASK-MVP-005 source/test/evidence는 uncommitted 상태였다. `AGENTS.md`, `prompts/codex/mvp_task_automation.md` 및 `prompts/codex/mvp_task_automation.md:Zone.Identifier`의 별도 사용자 변경은 보존했고 TASK 범위로 판단하지 않았다.

## 2. 검토 결론

- Recommendation: `ACCEPT`
- BLOCKER: 없음
- HIGH: 없음
- MEDIUM: 없음
- LOW: 없음

`02_review.md`의 `TASK-MVP-005-REV-H01`은 SQLite `attempted_calls`와 every JSONL event에 `request_id`/`action_id`/operation/`component_version`를 기록하는 것으로 해소되었다. `TASK-MVP-005-REV-M01`은 `tool_call_valid`가 caller input이 아니라 immutable attempted-call trace의 UUID, UTC timestamp, component version, action/operation 순서 검증 후 derive되도록 변경되어 해소되었다.

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| mission/action, transitions, idempotency key, deadline/timestamp, reconciliation/retry/final result persist | `MissionLifecycleStore.persist_recovery_run`, SQLite tables | `test_sqlite_schema_and_mission_action_lifecycle_are_persisted` | `MVP-005.json`, `lifecycle.sqlite3`, `summary.json` | PASS |
| reload 뒤 `UNKNOWN`이 success로 변환되지 않음 | `load_action_state`가 raw persisted `ActionStatus`를 reload | `test_unknown_transition_remains_unknown_after_database_reload` | `MVP-005.json` exit criterion `restart_reload_test_passes` | PASS |
| machine-readable JSONL/JSON run reconstruction | `write_run_artifacts`, `_events`, `load_summary` | `test_jsonl_trace_is_parseable_and_evidence_reconstructs_run` | `trace.jsonl`, `summary.json`, `MVP-005.json` | PASS |
| required run identifiers/fields 및 attempted-call correlation/version | `_validated_attempted_calls`, `attempted_calls` table, `_call_dict` | `test_evidence_references_valid_mission_and_action_ids`, `test_timeout_reconciles_once_then_retry_succeeds` | SHA-256-verified canonical artifacts | PASS |
| `tool_call_valid` fail-closed provenance | `_validated_attempted_calls` before `tool_call_valid = True` | `test_tool_call_validity_is_derived_from_a_strict_attempted_call_trace` | `MVP-005.json` `tool_call_valid_provenance` | PASS |
| no production telemetry stack or later-task execution behavior | task-scoped modules and dependency/diff inspection | full regression suite | `MVP-005.json` limitations/exit criteria | PASS |

## 4. 주요 Findings

### BLOCKER

없음.

### HIGH

없음.

### MEDIUM

없음.

### LOW

없음.

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: PASS
Contract compliance: PASS
State / invariant safety: PASS
Test adequacy: PASS
Regression safety: PASS
Evidence integrity: PASS
```

## 6. 검토에서 확인한 핵심 위험

- `UNKNOWN`은 durable `action_transitions`에 그대로 저장되고 reload test가 이를 success로 해석하지 않음을 검증했다.
- attempted dispatch, reconciliation, retry의 correlation은 ordered immutable `AttemptedToolCall` trace로 보존된다. 각 JSONL event와 SQLite record가 request/action ID 및 emitting `component_version`을 갖는다.
- `tool_call_valid`는 public writer argument가 아니며, 잘못된 request UUID trace는 `PersistenceValidationError`로 artifact 생성을 fail-closed 한다.
- `MVP-005.json`의 source/test/artifact SHA-256을 현재 workspace에서 독립 재계산했고 일치했다. focused 8 tests 및 full 44 tests를 재실행해 모두 통과했다.
- SQLite + JSONL/JSON local evidence 외의 telemetry stack, ROS 2/VLA/physical execution 또는 MVP-006 기능은 확인되지 않았다.

## 7. 최종 Recommendation

`ACCEPT TASK-MVP-005`
