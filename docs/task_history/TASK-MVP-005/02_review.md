# Read-only Review — TASK-MVP-005

## 1. 검토 정보

- TASK: `TASK-MVP-005`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 검토 대상: `src/mission_runtime/persistence.py`, `tests/test_persistence.py`, `results/mvp/runs/mvp-005-canonical-recovery-20260829T000000Z/`, `results/mvp/MVP-005.json`
- 검토 시점 Git 상태: MVP-005 source/test/evidence는 untracked, `docs/task_history/README.md`는 MVP-005 index row 추가로 수정됨. 모두 TASK-MVP-005 구현 범위에 속한다.

## 2. 검토 결론

- Recommendation: REJECT
- BLOCKER: 0
- HIGH: 1
- MEDIUM: 1
- LOW: 0

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| SQLite schema와 mission/action lifecycle persistence | `MissionLifecycleStore.create_schema`, `persist_recovery_run` | `test_sqlite_schema_and_mission_action_lifecycle_are_persisted` | `run_artifacts.database` | PASS |
| state transition, idempotency key, deadline/timestamp, reconciliation, retry/final result persistence | `actions`, `mission_transitions`, `action_transitions`, `events`, `runs` tables | focused DB inspection and persistence test | `summary.json`, `trace.jsonl` | PASS |
| reload 뒤 `UNKNOWN` 유지 | `load_action_state` | `test_unknown_transition_remains_unknown_after_database_reload` | `action_transitions` ordinal 2 = `UNKNOWN` | PASS |
| parseable JSONL과 run reconstruction | `write_run_artifacts`, `load_summary` | `test_jsonl_trace_is_parseable_and_evidence_reconstructs_run` | `trace.jsonl`, `summary.json` | PASS |
| mission/action ID validity | `summary` construction | `test_evidence_references_valid_mission_and_action_ids` | `canonical_run.mission_id`, `action_ids` | PASS |
| frozen observability correlation envelope | `_events`, `trace.jsonl` | 없음 | JSONL event에 `request_id`/`component_version` 없음 | FAIL |

## 4. 주요 Findings

### BLOCKER

없음.

### HIGH

- **ID:** `TASK-MVP-005-REV-H01`
- **File / Symbol:** `src/mission_runtime/persistence.py` — `MissionLifecycleStore._events`, `actions` schema, `write_run_artifacts`; generated `trace.jsonl`
- **Issue:** 모든 JSONL event와 SQLite lifecycle record가 attempted-call `request_id`를 보존하지 않는다. JSONL event에는 `component_version`도 없으며, 따라서 trace만으로 per-call correlation과 emitting component version을 재구성할 수 없다.
- **Why it matters:** timeout/reconciliation/retry는 multiple attempted calls를 포함한다. `request_id`가 없으면 같은 mission/action의 first dispatch, reconciliation query, retry dispatch를 frozen contract 수준으로 audit할 수 없다. version도 없으면 evidence를 producing component revision에 안전하게 연결할 수 없다.
- **Requirement / Contract affected:** `docs/contracts/contract_plan.md` cross-cutting envelope (`request_id`, `component_version`) 및 `ADR-009`의 JSONL `mission_id`, `request_id`, timestamps, state transition, model/tool/skill version, retry/HITL observability requirement.
- **Evidence:** `trace.jsonl`의 세 event는 `schema_version`, `run_id`, `mission_id`, `action_id`, timestamp/status를 가지지만 `request_id`/`component_version`을 갖지 않는다. `runs`, `actions`, `mission_transitions`, `action_transitions`, `events` schema에도 request ID column이 없고 `RecoveryRun`이 request ID sequence를 persistence layer에 전달하지 않는다. focused tests도 JSONL event type과 mission/action UUID만 검사한다.
- **Recommended remediation:** `RecoveryRun` 또는 별도 immutable attempted-call trace contract에 dispatch/reconciliation/retry 각각의 `request_id`와 component version을 보존한다. 이를 SQLite 및 every JSONL event와 reconstructable summary에 persist하고, event별 request/action/mission correlation과 component version regression test를 추가한다.

### MEDIUM

- **ID:** `TASK-MVP-005-REV-M01`
- **File / Symbol:** `src/mission_runtime/persistence.py` — `write_run_artifacts(..., tool_call_valid: bool = True)`
- **Issue:** required evidence field `tool_call_valid`가 caller-supplied boolean이며 default가 `True`다. persistence layer는 validated gateway observation이나 immutable runtime trace로부터 그 claim을 도출하지 않는다.
- **Why it matters:** evidence consumer가 tool-call validity를 independent observation으로 해석할 수 있지만 현재는 artifact writer caller가 임의로 claim을 정한다.
- **Requirement / Contract affected:** TASK-MVP-005 required run evidence field `tool_call_valid` 및 deterministic runtime ownership/evidence integrity.
- **Evidence:** `persist_recovery_run`은 boolean type만 검사하고 그대로 `runs`/summary에 기록한다. tests는 default `True`만 검사한다.
- **Recommended remediation:** H01에서 추가하는 attempted-call trace의 strict validation 결과로 이 field를 derive하거나, artifact writer가 externally supplied validity claim을 받지 못하게 한다. H01 fix와 함께 처리하는 것이 안전하다.

### LOW

없음.

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: FAIL
Contract compliance: FAIL
State / invariant safety: PASS
Test adequacy: FAIL
Regression safety: PASS
Evidence integrity: FAIL
```

## 6. 검토에서 확인한 핵심 위험

- SQLite snapshot은 `UNKNOWN` action state를 `UNKNOWN`으로 reload하며 ambiguous action을 success로 바꾸지 않는다.
- lifecycle DB, JSONL, JSON summary가 canonical timeout/reconciliation/retry sequence를 보존하지만, attempted-call `request_id`가 빠져 retry/reconciliation audit correlation이 끊긴다.
- source/test/artifact SHA-256은 evidence manifest와 일치하고 focused 4개/full 43개 test는 PASS했지만, 현 테스트는 frozen JSONL envelope completeness를 검증하지 않는다.

## 7. 최종 Recommendation

`REJECT TASK-MVP-005`
