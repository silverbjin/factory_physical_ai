# Read-only Review — TASK-MVP-006

## 1. 검토 정보

- TASK: `TASK-MVP-006`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 검토 대상: `src/mission_runtime/normal.py`, `src/mission_runtime/persistence.py`, `tests/test_normal_e2e.py`, `results/mvp/normal_e2e/latest.json`, `results/mvp/MVP-006.json`
- 검토 시점 Git 상태: TASK-MVP-006 source/test/evidence/history가 uncommitted 상태였다. 별도 사용자 변경은 발견되지 않았다.

## 2. 검토 결론

- Recommendation: `REJECT`
- BLOCKER: 없음
- HIGH: 1
- MEDIUM: 없음
- LOW: 없음

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| canonical text → Factory Agent → structured mission | `CanonicalNormalMissionExecutor.run` | `test_canonical_text_reaches_completed_through_agent_wms_and_one_transfer` | `MVP-006.json.normal_run` | PASS |
| `Rack A19`, one transfer, `COMPLETED`, no timeout/retry | `CanonicalNormalMissionExecutor.run`, `persist_normal_run` | focused E2E tests | `normal_e2e/latest.json` | PASS |
| SQLite/JSONL/JSON run reconstruction | `write_normal_run_artifacts`, `write_normal_e2e_latest` | `test_normal_run_evidence_is_machine_readable_and_reconstructable` | run SQLite/trace/summary artifacts | PASS |
| attempted-call correlation과 `tool_call_valid` evidence integrity | `_validate_normal_run` | tampered trace negative test 없음 | `MVP-006.json` claims `tool_call_valid: true` | FAIL |

## 4. 주요 Findings

### BLOCKER

없음.

### HIGH

- **ID:** `TASK-MVP-006-REV-H01`
- **File / Symbol:** `src/mission_runtime/persistence.py` — `MissionLifecycleStore._validate_normal_run`
- **Issue:** attempted call의 UUID 형식과 action/operation 순서만 확인하고, `run.attempted_calls[0].request_id`가 `run.inventory.request_id`, `run.attempted_calls[1].request_id`가 `run.transfer.request_id`와 일치하는지는 검증하지 않는다. `dataclasses.replace()`로 inventory attempted-call `request_id`를 다른 valid UUID로 바꾼 `NormalRun`도 `write_normal_run_artifacts()`를 통과하여 `tool_call_valid = true` summary를 생성한다.
- **Why it matters:** frozen cross-cutting contract와 ADR-009의 per-call correlation/audit requirement를 우회한다. evidence의 `request_id`가 실제 mock component result와 다른데도 valid tool-call evidence로 기록되어 run reconstruction과 provenance가 거짓이 될 수 있다.
- **Requirement / Contract affected:** `docs/contracts/contract_plan.md` cross-cutting `request_id`/`action_id`/`component_version`; `ADR-009` structured JSONL correlation; TASK-MVP-006 evidence reconstruction requirement.
- **Evidence:** independent temporary-run probe가 `tampered normal evidence accepted: True`를 출력했다. 현재 `tests/test_normal_e2e.py`에는 이 bypass regression이 없다.
- **Recommended remediation:** persistence domain boundary에서 inventory/transfer `result`, `mission_id`, `request_id`, `action_id`, `idempotency_key`, timestamp/component version을 `NormalRun.attempted_calls` 및 request/action records와 완전히 cross-check하고, mismatched valid UUID trace가 `PersistenceValidationError`로 fail-closed 되는 regression test를 추가한다.

### MEDIUM

없음.

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

- normal path의 happy path와 SQLite reconstruction은 모두 동작하지만, durable evidence boundary는 happy-path object를 신뢰하면 안 된다.
- `tool_call_valid`는 caller-supplied 값은 아니지만, correlation 관계를 검증하지 않아 valid-shaped tampered trace에 대해 과도한 success claim을 만든다.
- task가 one normal transfer만 다루더라도 `request_id`는 per-call audit identity이므로 inventory와 transfer result에 연결돼야 한다.

## 7. 최종 Recommendation

`REJECT TASK-MVP-006`
