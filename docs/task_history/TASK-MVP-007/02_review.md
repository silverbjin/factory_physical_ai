# Read-only Review — TASK-MVP-007

## 1. 검토 정보

- TASK: `TASK-MVP-007`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 검토 대상: `src/mission_runtime/failure_recovery.py`, `tests/test_failure_recovery_e2e.py`, `results/mvp/failure_recovery/latest.json`, `results/mvp/MVP-007.json`
- 검토 시점 Git 상태: TASK-MVP-006/007 implementation artifacts가 uncommitted였다.

## 2. 검토 결론

- Recommendation: `REJECT`
- BLOCKER: 없음
- HIGH: 1
- MEDIUM: 없음
- LOW: 없음

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| single timeout → reconciliation → one retry → completed | `CanonicalFailureRecoveryE2EExecutor`, existing recovery coordinator | `test_single_timeout_reconciles_before_one_retry_and_completes` | SQLite/JSONL recovery artifacts | PASS |
| WMS Rack A19 precedes recovery | executor inventory query | happy-path assertion only | latest wrapper inventory section | PASS |
| E2E evidence correlation/provenance | `write_failure_recovery_e2e_latest` | tamper regression 없음 | `MVP-007.json` | FAIL |

## 4. 주요 Findings

### BLOCKER

없음.

### HIGH

- **ID:** `TASK-MVP-007-REV-H01`
- **File / Symbol:** `src/mission_runtime/failure_recovery.py` — `write_failure_recovery_e2e_latest`
- **Issue:** wrapper가 `FailureRecoveryE2ERun.inventory`와 `RunArtifacts.summary`/recovery run의 mission/request/action correlation을 검증하지 않고 JSON을 merge한다. valid UUID로 inventory `request_id`를 변조한 run도 latest evidence가 생성된다.
- **Why it matters:** E2E evidence가 WMS success와 timeout/recovery sequence가 같은 mission/run에 속함을 보장하지 못한다. frozen cross-cutting `request_id`/`mission_id` correlation과 TASK-MVP-007 evidence requirement를 우회한다.
- **Evidence:** temporary probe가 `tampered E2E wrapper accepted: True`를 출력했다.
- **Recommended remediation:** writer boundary가 canonical mission fields, inventory success/correlation, recovery mission/action IDs, artifact summary run/mission/action IDs와 required timeout/reconciliation/retry values를 cross-check하고 mismatch를 typed exception으로 fail-closed 처리한다. corresponding regression을 추가한다.

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

- durable recovery artifact만 valid해도 E2E wrapper metadata가 동일 run과 연결된다는 보장은 별도로 필요하다.
- `request_id`는 valid UUID 형식 검증만으로 충분하지 않고 typed component observation 및 run manifest와의 relation을 검증해야 한다.

## 7. 최종 Recommendation

`REJECT TASK-MVP-007`
