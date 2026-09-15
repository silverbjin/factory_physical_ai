# Fix — TASK-SIM-GATE

## 1. 수정 정보

- TASK: `TASK-SIM-GATE`
- 작업 유형: Review Finding Fix
- 실행 순번: `03`
- 일자: `2026-09-14`
- 기준 Review: `02_review.md`
- 수정 대상 Severity: `BLOCKER`, acceptance를 실패시킨 `MEDIUM`

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-SIM-GATE-REV-B01` | BLOCKER | acceptance-bound current file을 reviewed commit의 실제 Git blob과 비교하지 않아 rehash된 unreviewed direct-actuator operation이 통과 | FIXED |
| `TASK-SIM-GATE-REV-M01` | MEDIUM | malformed P0 authorization 값이 snapshot에 non-boolean으로 전파 | FIXED |

## 3. 원인 분석

기존 immutable 검사는 acceptance SHA와 current file SHA만 비교하고 `reviewed_commit:path`의 실제 blob은 확인하지 않았다. 따라서 공격자가 runtime과 acceptance hash를 함께 바꾸면 독립 검토된 revision이라는 provenance를 우회할 수 있었다. C18도 제한된 문자열 blacklist에만 의존하여 `actuator.execute` 같은 새로운 logical operation을 발견하지 못했다.

Authorization decision은 malformed P0 값에서 fail-closed였지만, evidence snapshot 생성은 원본 값을 그대로 복사해 decision 안전성과 output schema 안전성이 분리되어 있었다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `scripts/verify_simulation_lane_gate.py` | SIM-001 profile/evidence 및 SIM-002 evidence/report/entry/runtime/test를 acceptance SHA, current file, exact reviewed Git blob과 삼중 결속 | `TASK-SIM-GATE-REV-B01` |
| `scripts/verify_simulation_lane_gate.py` | AST에서 operation-like string을 추출하고 frozen `EXPECTED_OPERATIONS`와 exact allowlist 비교 | `TASK-SIM-GATE-REV-B01` |
| `scripts/verify_simulation_lane_gate.py` | 실제 JSON boolean만 보존하고 malformed/missing P0 값은 boolean `false`로 정규화 | `TASK-SIM-GATE-REV-M01` |
| `tests/test_simulation_lane_gate.py` | reviewed-commit mismatch + `actuator.execute`, unknown operation, malformed string/int/null 회귀 테스트 추가 | 두 finding |
| `docs/simulation/simulation_lane_gate_v1.md` | 강화된 trust-chain, allowlist, negative validation과 최신 test count 기록 | 두 finding |
| `results/simulation/SIM-GATE_readiness.json` | 수정된 verifier/report/test hash와 C01–C20 결과로 재생성 | 두 finding |

## 5. 추가/강화한 테스트

- Runtime에 `actuator.execute`를 추가하고 acceptance runtime SHA를 다시 계산해도 C08/C18이 모두 `FAIL`하고 `SIM_NO_GO`인지 검증한다.
- AST operation set에 `controller.dispatch` 같은 미승인 operation이 추가되면 allowlist 검증이 실패하는지 확인한다.
- P0 authorization의 각 필드에 string, integer, null을 주었을 때 gate가 `SIM_NO_GO`이며 output snapshot의 모든 authorization이 JSON boolean인지 검증한다.

## 6. 테스트 결과

| 검증 | 결과 |
|---|---|
| Focused tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_simulation_lane_gate.py -q` | PASS — `19 passed in 1.44s` |
| Full regression: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q` | PASS — `188 passed in 42.14s` |
| Static compile | PASS |
| `git diff --check` | PASS |
| Independent payload recomputation | PASS |

## 7. Evidence 갱신

- Evidence: `../../../results/simulation/SIM-GATE_readiness.json`
- Evidence SHA-256: `d376b7f43580c27c500fd915b81f277e5b4c67215b36b80530d00b26e1c2c0ec`
- Payload SHA-256: `ff0cf6ccf1e72732719e3fde7e26cba90333d91054b2525f3102a000055be78d`
- 변경된 claim: reviewed-commit exact blob binding, AST operation allowlist, strictly boolean authorization snapshot을 검증한다.
- Gate result: `SIM_GO`
- Independent acceptance: `PENDING`
- Effective simulation-lane authorization: `false`

## 8. 남은 Findings

없음

## 9. History Action

`No history action required.`

## 10. 수정 결과

`TASK-SIM-GATE fixes are ready for independent re-review.`

