# Read-only Review — TASK-SIM-C01

## 1. 검토 정보

- TASK: `TASK-SIM-C01`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 검토 대상 commit: `7ca63be136e272b3c73031d3fb5fd24760cc62e6`
- 비교 기준: `360c42ef2c61374788dfa0fdc36088305c309960`
- 검토 시점 Git 상태: clean worktree, staged changes 없음
- 검토 범위: TASK specification, implementation diff, Simulation Lane contract/schema, focused tests, evidence, 변경 경계를 제약하는 frozen architecture/ADR/P0 sources

## 2. 검토 결론

- Recommendation: `REJECT`
- BLOCKER: 1
- HIGH: 2
- MEDIUM: 1
- LOW: 0

Focused suite와 full regression은 통과했지만, 별도 부정 검증에서 `MODEL_TIMEOUT`이 terminal failure로 허용되어 mandatory timeout invariant를 우회했다. 또한 실제 달력상 불가능한 timestamp와 요청 목적지와 다른 arrival success가 수락됐다. 따라서 evidence의 `C23`, `C36`, `C40` 및 `SIM_CONTRACT_GAPS_RESOLVED` 결론은 현재 revision을 정확히 나타내지 않는다.

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| Analysis baseline 및 exact six gaps 보존 | contract Section 12, evidence `input_bindings` / `gap_resolution` | hash 재계산 | C01–C10 | PASS |
| project-wide planning-only 상태와 Simulation Lane delegation | `docs/contracts/contract_plan.md` | diff/source inspection | C13–C15 | PASS |
| frozen topology 및 ownership | contract Sections 1, 6, 7, 13 | forbidden-field tests | C29–C34 | PASS |
| 정확한 다섯 logical operation | contract Sections 1, 5–10; schema operation branches | positive operation vectors | C16–C20 | PASS |
| versioned common request/result 및 fail-closed timestamp | schema `Timestamp`, envelopes | malformed text timestamp test만 존재 | C27, C36 | FAIL |
| Mission invocation/result/lifecycle | Mission schemas, `MissionTransition` | mission result/transition tests | GAP-SIM-001, C16, C22 | PASS |
| Navigation success가 requested destination과 일치 | contract Section 6, `NavigationExecuteResult` | destination correlation test 없음 | GAP-SIM-002, C17, C36 | FAIL |
| VLA bounded semantic interface 및 actuator exclusion | VLA schemas, contract Section 7 | positive/forbidden-field tests | GAP-SIM-003, C18, C29 | PASS |
| 모든 timeout은 `unknown`이며 success/failure가 아님 | contract Sections 8–9; result conditionals | `DEPENDENCY_TIMEOUT` Navigation case만 검증 | GAP-SIM-005, C23 | FAIL |
| `unknown -> succeeded` 금지, reconciliation/retry guards | transition/reconciliation/retry schemas and semantic predicates | transition, wrong identity, retry tests | C24–C26 | PASS |
| operational verification와 deterministic verdict 분리 | Verification schemas, `sim-exact-match-v1` | pass/fail/uncertain tests | GAP-SIM-004, C19, C28 | PASS |
| fixture identity/hash/manifest determinism | fixture schemas, `_deterministic_verdict` | tampered hash/duplicate identity regression 없음 | GAP-SIM-006, C21, C28 | FAIL |
| physical/Dataset/training/Week/hardware exclusion | contract Section 13, frozen hashes | diff/hash inspection | C29–C34 | PASS |
| P0-004R historical `NO_GO` 보존 | unchanged P0-004R evidence | SHA-256 재계산 | C10, authorization snapshot | PASS |
| implementation/decision/acceptance/downstream authorization 분리 | evidence authorization snapshot, updated TASK-SIM-001 | source inspection | re-evaluation false, SIM-002 false | PASS |
| focused/full tests 및 evidence가 실제 acceptance state를 입증 | tests/evidence | focused `22 passed`, full `154 passed`, reviewer probes | C35–C40 | FAIL |

## 4. 주요 Findings

### BLOCKER

- **ID:** `TASK-SIM-C01-REV-B01`
- **File / Symbol:** `docs/contracts/schemas/simulation_execution_contract_v1.schema.json` — `ErrorCategory`, `NavigationExecuteResult`, `VLAExecuteResult`
- **Issue:** timeout conditional은 `DEPENDENCY_TIMEOUT`에만 적용된다. 허용된 `MODEL_TIMEOUT`은 Navigation/VLA에서 `result=failure`, `status=failed`로 schema validation을 통과한다.
- **Why it matters:** frozen contract와 TASK는 timeout을 success/failure로 분류하지 않고 반드시 `unknown`으로 기록한 뒤 reconciliation하도록 요구한다. 현재 schema는 이 핵심 state invariant를 우회한다.
- **Requirement / Contract affected:** TASK Sections 14–17, C23, C24, C40; `contract_plan.md` timeout rule; system architecture recovery invariant.
- **Evidence:** reviewer probe에서 Navigation과 VLA의 terminal `MODEL_TIMEOUT` payload 모두 validation error 0건. Evidence는 C23/C40을 `PASS`로 기록했다.
- **Recommended remediation:** 모든 timeout-category 결과를 `pending/unknown`으로 강제하거나, `MODEL_TIMEOUT`이 caller-visible timeout이 아니라는 별도 비-timeout semantics를 frozen rules와 모순 없이 명확히 정의한다. 양 operation의 각 timeout category에 대한 negative regression을 추가하고 evidence를 재생성한다.

### HIGH

- **ID:** `TASK-SIM-C01-REV-H01`
- **File / Symbol:** `docs/contracts/schemas/simulation_execution_contract_v1.schema.json` — `$defs.Timestamp`; `tests/test_simulation_execution_contract.py::test_versions_formats_and_unknown_values_fail_closed`
- **Issue:** 현재 환경의 `FormatChecker`에는 `date-time` checker가 등록되지 않았고 fallback regex는 월별 일수/윤년을 검증하지 않는다. `2026-02-31T00:00:00Z`와 `2026-09-31T00:00:00Z`가 모두 수락된다.
- **Why it matters:** TASK는 timestamp structural validation과 invalid input의 fail-closed 처리를 요구한다. deadline/reconciliation/audit ordering에 사용되는 불가능한 시간을 허용하면 executable contract claim이 성립하지 않는다.
- **Requirement / Contract affected:** TASK Sections 9, 21, 22, C27, C36, C40; contract Section 2.
- **Evidence:** focused test는 `not-a-timestamp`만 검증한다. reviewer probe에서 두 invalid calendar timestamp가 validation error 0건으로 통과했다.
- **Recommended remediation:** repository에서 실제로 동작하는 RFC 3339/date-time validator를 명시하거나 calendar-validating semantic validator를 제공하고, invalid day/month/leap-date tests를 추가한다.

- **ID:** `TASK-SIM-C01-REV-H02`
- **File / Symbol:** `tests/test_simulation_execution_contract.py::_assert_correlated`; schema `NavigationExecuteResult.arrival`
- **Issue:** Navigation request의 `destination_id`와 successful result의 `arrival.destination_id` 일치를 검증하지 않는다. 다른 목적지를 `verified=true`로 반환해도 schema와 semantic correlation helper가 모두 수락한다.
- **Why it matters:** contract Section 6은 requested destination 도착만 success로 인정한다. 현재 상태는 false-success를 허용하며 bounded deterministic smoke path가 잘못된 도착을 성공으로 처리할 수 있다.
- **Requirement / Contract affected:** TASK Sections 10, 12, 27; GAP-SIM-002; C17, C36, C40.
- **Evidence:** reviewer probe에서 `different-destination` success는 schema validation 및 `_assert_correlated`를 모두 통과했다.
- **Recommended remediation:** request/result semantic validation에 exact destination correlation을 추가하고 mismatched destination negative test 및 evidence를 갱신한다.

### MEDIUM

- **ID:** `TASK-SIM-C01-REV-M01`
- **File / Symbol:** schema `SimulationFixtureManifest.fixtures`; `_deterministic_verdict`; fixture tests
- **Issue:** manifest schema는 duplicate fixture identity와 content/hash 불일치를 구조적으로 허용한다. semantic helper는 조회 시 이를 차단할 수 있지만 tampered hash와 duplicate identity를 고정하는 regression test가 없다.
- **Why it matters:** fixture manifest의 identity/version/hash determinism과 immutability는 GAP-SIM-006의 핵심이다. helper가 향후 변경될 때 해당 guard가 사라져도 현재 suite가 탐지하지 못한다.
- **Requirement / Contract affected:** TASK Sections 19–21, 27, 29; C21, C28, C36.
- **Evidence:** reviewer probe에서 두 payload 모두 schema를 통과했고, stale hash는 helper 호출 시에만 `ContractSemanticError`가 발생했다.
- **Recommended remediation:** duplicate `(fixture_id, fixture_version)`와 stale `content_sha256`를 명시적으로 금지하는 semantics를 강화하고 각각 negative regression을 추가한다.

### LOW

No LOW findings.

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: FAIL
Contract compliance: FAIL
State / invariant safety: FAIL
Test adequacy: FAIL
Regression safety: PASS
Evidence integrity: FAIL
```

## 6. 검토에서 확인한 핵심 위험

- error taxonomy의 이름만 timeout이어도 state conditional이 적용되지 않으면 핵심 reconciliation invariant를 우회할 수 있다.
- JSON Schema `format`은 validator/runtime 지원 없이는 assertion이 아닐 수 있으므로 실제 프로젝트 환경에서 malformed calendar value를 검증해야 한다.
- request/result correlation은 UUID 일치만으로 충분하지 않으며 success를 구성하는 semantic target도 동일해야 한다.
- hash/uniqueness guard는 helper 구현만 확인하지 말고 tamper/duplicate regression으로 고정해야 evidence claim을 신뢰할 수 있다.

## 7. 최종 Recommendation

`REJECT TASK-SIM-C01`

`TASK-SIM-001 re-evaluation authorized = false`와 `TASK-SIM-002 authorized = false`를 유지한다.
