# Fix — TASK-SIM-C01

## 1. 수정 정보

- TASK: `TASK-SIM-C01`
- 작업 유형: Review Finding Fix
- 실행 순번: `03`
- 기준 Review: `02_review.md`, `REJECT TASK-SIM-C01`
- 기준 HEAD: `fea1bdfb7b8c0e0f3f69c5b62d328e95b37a5561`
- 수정 대상 Severity: `BLOCKER`, `HIGH`, acceptance gate에 연결된 `MEDIUM`

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-SIM-C01-REV-B01` | BLOCKER | `MODEL_TIMEOUT` terminal failure가 timeout-to-`unknown` invariant 우회 | FIXED |
| `TASK-SIM-C01-REV-H01` | HIGH | calendar-invalid timestamp가 schema validator를 통과 | FIXED |
| `TASK-SIM-C01-REV-H02` | HIGH | requested destination과 다른 navigation arrival success 허용 | FIXED |
| `TASK-SIM-C01-REV-M01` | MEDIUM | fixture duplicate identity와 stale content hash regression 부재 | FIXED |

## 3. 원인 분석

- Timeout conditional이 `DEPENDENCY_TIMEOUT` 한 값만 비교해 동일 error taxonomy의 `MODEL_TIMEOUT`을 누락했다.
- JSON Schema `format: date-time`이 현재 환경에서 assertion checker로 등록되지 않았고 regex는 lexical shape만 검사했다.
- request/result correlation helper가 operation 및 ID만 비교하고 navigation success의 semantic destination을 비교하지 않았다.
- `_deterministic_verdict` 내부에는 선택된 fixture 검사가 있었지만 manifest 전체의 identity uniqueness/hash integrity를 독립 invariant로 고정하지 않았다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `docs/contracts/simulation_execution_contract_v1.md` | 두 timeout category의 `pending/unknown` 규칙, calendar-valid RFC 3339 검사, unique fixture identity/hash 재계산 의무 명시 | B01, H01, M01 |
| `docs/contracts/schemas/simulation_execution_contract_v1.schema.json` | `DEPENDENCY_TIMEOUT`/`MODEL_TIMEOUT` conditional 통합, manifest exact duplicate 차단 | B01, M01 |
| `tests/test_simulation_execution_contract.py` | 실제 calendar checker, destination correlation, manifest integrity validator 및 네 finding regression 추가 | B01, H01, H02, M01 |
| `results/simulation/SIM-C01_contract_resolution.json` | 현재 contract/schema/test hashes, test counts, finding status, review provenance, payload hash 갱신 | 전체 findings |

## 5. 추가/강화한 테스트

- Navigation/VLA의 `DEPENDENCY_TIMEOUT` 및 `MODEL_TIMEOUT`이 모두 `pending/unknown`만 허용하는지 검증했다.
- invalid non-leap date, 월별 invalid day를 거부하고 valid leap day는 허용하는 calendar validation을 추가했다.
- successful Navigation result의 `arrival.destination_id`가 request와 다르면 `ContractSemanticError`가 발생하도록 고정했다.
- 동일 fixture object duplicate는 schema에서, 같은 `(fixture_id, fixture_version)`의 다른 content와 stale hash는 semantic validator에서 거부하도록 검증했다.
- Review에서 사용된 네 부정 probe를 다시 실행해 모두 reject되는 것을 확인했다.

## 6. 테스트 결과

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused tests | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_simulation_execution_contract.py -q -p no:cacheprovider` | `26 passed` — PASS |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` | `158 passed` — PASS |
| Reviewer bypass probes | inline read-only Python | B01/H01/H02/M01 inputs 모두 rejected — PASS |
| Evidence/schema/source/payload | inline read-only Python | PASS |
| Repository whitespace | `git diff --check` | PASS |

## 7. Evidence 갱신

- Evidence: `../../../results/simulation/SIM-C01_contract_resolution.json`
- Evidence SHA-256: `4685588a2b3978b0a063328e94e8f0469f06af612fb50dae8aabf32dd3d349e5`
- Payload SHA-256: `e25fc1d9d3e4c8c1e3089dfcb116129b560a27e29e287b49436d8d93ae259acd`
- Contract SHA-256: `0451e9abae4cee911d9468d11e68b8bbb0e3aff1a1a2d9cf104ed64264d28caa`
- Schema SHA-256: `112b1e2e0d1fefb03d7b353e8ed4d875b025fe342380d5ba1cbf050bcc7d944a`
- Contract test SHA-256: `52b9e445207dd189a5dd76c2c31638b8ae90ef7c61493cc6c238313c0d945534`
- Task-specific decision: `SIM_CONTRACT_GAPS_RESOLVED`
- Independent acceptance: `PENDING`

## 8. 남은 Findings

없음.

## 9. History Action

`NO HISTORY ACTION REQUIRED`

기존 implementation/review commit과 audit record는 보존하고 현재 worktree correction으로 해결 가능하다.

## 10. 수정 결과

`TASK-SIM-C01 fixes are ready for independent re-review.`

```text
TASK-SIM-001 re-evaluation authorized: false
TASK-SIM-002 authorized: false
```
