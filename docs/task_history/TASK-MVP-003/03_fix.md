# Fix — TASK-MVP-003

## 1. 수정 정보

- TASK: `TASK-MVP-003`
- 작업 유형: Review Finding Fix
- 실행 순번: `02`
- 기준 Review: `01_review.md` — `REJECT TASK-MVP-003`
- 수정 대상 Severity: `HIGH`
- `GIT_HISTORY_STATUS`: `NO HISTORY ACTION REQUIRED`

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-MVP-003-REV-H01` | HIGH | `ActionStatusResult` failure observation에 `schema_version` 및 non-null correlation/timestamp가 없음 | FIXED |

## 3. 원인 분석

기존 `get_action_status(action_id)`는 action ID만 받아 unknown action의 typed failure를 만들었다. 따라서 request boundary가 보유해야 하는 `schema_version`, `mission_id`, `request_id`, UTC `timestamp`를 result로 전파할 수 없었다. success path만 검사한 기존 test도 이 failure-envelope 누락을 발견하지 못했다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `src/factory_tools/gateway.py` | strict `ActionStatusQuery`를 추가하고 `ActionStatusResult`의 `schema_version`, `mission_id`, `request_id`, `action_id`, `timestamp`를 required field로 변경했다. `get_action_status` success/failure가 query envelope을 모두 반환한다. | `TASK-MVP-003-REV-H01` |
| `src/factory_tools/__init__.py` | `ActionStatusQuery` public export를 추가했다. | `TASK-MVP-003-REV-H01` |
| `tests/test_factory_tools.py` | unknown action typed failure의 full envelope과 malformed action-status query rejection을 regression test로 강화했다. | `TASK-MVP-003-REV-H01` |
| `results/mvp/MVP-003.json` | source hash, validation timestamp, H01 resolution claim을 현재 source snapshot에 맞게 갱신했다. | `TASK-MVP-003-REV-H01` |

## 5. 추가/강화한 테스트

`test_unknown_or_malformed_action_status_query_fails_typed`는 unknown action failure에 대해 `schema_version`, `mission_id`, `request_id`, UTC `timestamp`가 non-null으로 전파되는지 검증한다. 또한 non-mapping, missing field, invalid UUID, naive timestamp action-status query가 `ToolValidationError`로 fail-closed 되는지 검증한다.

## 6. 테스트 결과

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused tests | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_factory_tools.py -v` | 8 PASS, 0 FAIL |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 36 PASS, 0 FAIL |
| Syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS |
| Evidence/hash | JSON parse 및 SHA-256 재계산 | PASS |
| Intended-file whitespace | `git diff --no-index --check /dev/null` | PASS |
| `git diff --check` | repository check | PASS |

## 7. Evidence 갱신

- Evidence: `../../../results/mvp/MVP-003.json`
- 상태: PASS
- 변경된 claim: `TASK-MVP-003-REV-H01`은 `FIXED`; action-status query가 full typed envelope을 갖는다고 기록했다.

## 8. 남은 Findings

없음

## 9. History Action

`No history action required.`

## 10. 수정 결과

`TASK-MVP-003 fixes are ready for independent re-review.`
