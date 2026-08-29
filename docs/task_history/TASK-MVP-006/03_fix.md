# Fix — TASK-MVP-006

## 1. 수정 정보

- TASK: `TASK-MVP-006`
- 작업 유형: Review Finding Fix
- 실행 순번: `03`
- 기준 Review: `02_review.md` — `REJECT TASK-MVP-006`
- 수정 대상 Severity: `HIGH`
- `GIT_HISTORY_STATUS`: `NO HISTORY ACTION REQUIRED`

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-MVP-006-REV-H01` | HIGH | attempted-call `request_id`가 typed component result와 달라도 `tool_call_valid = true` evidence가 생성됨 | FIXED |

## 3. 원인 분석

`MissionLifecycleStore._validate_normal_run()`은 attempted-call의 UUID 형식과 operation 순서만 검사했다. 따라서 `NormalRun`의 immutable object graph를 `dataclasses.replace()`로 재구성해 valid UUID를 다른 값으로 바꿔도, inventory/transfer typed result가 보유한 실제 `request_id`와의 관계를 확인하지 않았다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `src/mission_runtime/persistence.py` | normal persistence가 mission/action/component correlation, inventory/transfer `ToolResultKind.SUCCESS`, attempted-call `request_id`/`component_version`/timestamp와 typed result의 일치를 cross-check한 뒤에만 `tool_call_valid = true`를 기록 | `TASK-MVP-006-REV-H01` |
| `tests/test_normal_e2e.py` | inventory/transfer attempted-call valid UUID mismatch 및 `ToolResultKind.FAILURE` 변조가 `PersistenceValidationError`로 fail-closed 되는 table-driven regression 추가 | `TASK-MVP-006-REV-H01` |
| `results/mvp/normal_e2e/latest.json`, `results/mvp/runs/mvp-006-canonical-normal-20260829T000000Z-fix1/`, `results/mvp/MVP-006.json` | current source/test hash와 fixed normal-run artifact provenance로 갱신 | `TASK-MVP-006-REV-H01` |

## 5. 추가/강화한 테스트

`test_persistence_rejects_tampered_normal_run_correlation_or_tool_result`는 두 attempted-call `request_id` mismatch와 inventory/transfer result-kind mismatch를 각각 시도한다. 이전 구현에서 accepted되던 valid UUID correlation bypass는 이제 `PersistenceValidationError`를 발생시킨다.

## 6. 테스트 결과

| 검증 | 결과 |
|---|---|
| Focused tests: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_normal_e2e.py -v` | 3 PASS, 0 FAIL |
| Full regression: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 47 PASS, 0 FAIL |
| Syntax/static: `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |
| JSON/JSONL/SQLite + SHA-256 verification | PASS |
| `git diff --check` | PASS |

## 7. Evidence 갱신

- Evidence: `../../../results/mvp/MVP-006.json`
- SHA-256: `be15d8952f5ad96a6a45cd09b2e0656a381456ee7d1ee6866ba1a15871e80771`
- 변경된 claim: `tool_call_valid`는 typed component result와 attempted-call correlation/version/timestamp를 cross-check한 strict normal persistence validation 뒤에만 기록된다.

## 8. 남은 Findings

없음. Independent re-review에서 contract/evidence completeness를 다시 판단해야 한다.

## 9. History Action

`No history action required.`

## 10. 수정 결과

`TASK-MVP-006 fixes are ready for independent re-review.`
