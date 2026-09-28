# Diagnosis — TASK-SIM-Q01-MIN

- Status: RESOLVED
- Trigger: Review REJECT 후 네 개 blocking finding의 formal diagnosis
- Triggering status: `REJECTED / FIX REQUIRED`
- Finding IDs: `Q01MIN-EVIDENCE-001`, `Q01MIN-APPLICABILITY-002`, `Q01MIN-SIM009-SEMANTICS-003`, `Q01MIN-CONTRACTB-004`

## Trigger

독립 Review에서 canonical Evidence 부재, physics-executed subject의 잘못된 applicability, SIM-009 retry/reconciliation 의미 손실, frozen Contract-B 비교 부재가 확인되었다.

## Root Cause

구현이 MIN-Q01 경로를 11개 subject로 축소했지만 qualification 경계를 완결하지 않았다. 구현 단계가 fixture 기반 unit test 통과만으로 완료 처리되어 실제 bounded run과 canonical Evidence 생성을 수행하지 않았고, collector는 실행 결과를 축약하면서 physics measurement 및 scenario별 retry/reconciliation/Verification 구조를 버렸다. 또한 `resolve_predecessor_binding`은 worktree Acceptance가 가리키는 Git object를 해석할 뿐 frozen commit/hash/task-specific result와의 일치를 검증하지 않는다.

따라서 네 finding은 하나의 target implementation/validation 결함의 독립적인 발현이며 architecture 또는 predecessor provenance 충돌이 아니다.

## Requirement / Contract

- `tasks/TASK-SIM-Q01-MIN.md` Sections 3, 6–8, 10–12: exact Contract-B binding, physics 실행 시 `physics_measurement=REQUIRED`, SIM-009 retry/recovery/reconciliation/Verification 의미 보존, canonical Evidence 생성.
- `configs/simulation/min_q01_scope.json#applicability_policy`: physics 실행 시 measurement는 `REQUIRED`, 구조적으로 증명된 pre-physics 종료에서만 `NOT_APPLICABLE`.
- `docs/contracts/simulation_execution_contract_v1.md` Sections 4, 8–10: correlation identity, reconciliation evidence, retry authorization, Verification result 의미를 보존해야 한다.

## Authoritative Sources

- `tasks/TASK-SIM-Q01-MIN.md`
- `tasks/TASK-SIM-Q01.md` Sections 2–3
- `configs/simulation/min_q01_scope.json`
- `docs/contracts/simulation_execution_contract_v1.md`
- frozen predecessor Acceptance와 accepted Git blob
- `docs/task_history/TASK-SIM-Q01-MIN/03_review.md`
- `scripts/run_simulation_provenance_qualification.py`
- `src/simulation_runtime/provenance_qualification.py`
- `scripts/q01_execution_adapters.py`
- `src/simulation_runtime/failure_recovery.py`
- `tests/test_simulation_provenance_qualification.py`

Frozen blob의 SHA256은 TASK 표와 모두 일치했고 task-specific result는 각각 `SIM_NAVIGATION_BACKEND_READY`, `SIM_MANIPULATION_BACKEND_READY`, `SIM_MISSION_INTEGRATION_BLOCKED`, `SIM_NORMAL_E2E_READY`, `SIM_FAILURE_SUITE_READY`이다. `results/simulation/SIM-Q01_provenance_qualification.json`은 현재 존재하지 않는다.

## Fault Domain

Target implementation and validation. Environment는 실제 bounded qualification 실행의 전제이지만 이번 네 finding의 원인은 아니다.

## Resolution

Fix는 frozen predecessor tuple(commit, Evidence path, SHA256, task-specific result)을 collector 실행 전에 exact-match로 검증하고, physics-executed path에서 실제 measurement와 structured time을 둘 다 `REQUIRED`로 fail-closed 검증해야 한다. SIM-009 wrapper/collector는 source row의 applicable retry authorization/result, reconciliation identity/outcome, recovery 및 Verification 구조를 동일 run의 `semantic_outcome`에 보존해야 한다. 이후 qualified Gazebo/MuJoCo 환경에서 canonical runner로 11개 subject를 실제 실행하고 READY Evidence를 생성해야 한다.

## Authorized Correction Boundary

- `scripts/run_simulation_provenance_qualification.py`: frozen tuple 비교 및 canonical run orchestration
- `src/simulation_runtime/provenance_qualification.py`: exact Contract-B 검증, physics measurement model/validation, lossless applicable semantics
- `scripts/q01_execution_adapters.py`: same-run measurement와 SIM-009 retry/reconciliation/recovery/Verification 전달
- `tests/test_simulation_provenance_qualification.py`: 네 finding의 positive/negative regression coverage
- `results/simulation/SIM-Q01_provenance_qualification.json`: genuine bounded run으로만 생성

## Protected Boundary

- `tasks/TASK-SIM-Q01-MIN.md`와 `configs/simulation/min_q01_scope.json`의 frozen scope
- accepted SIM-004/005/007/008/009 Acceptance, Evidence, commits
- frozen SIM-010 state
- historical Full-Q01 history와 excluded operation paths
- `results/reviews/SIM-Q01_acceptance.json`
- canonical Evidence의 수동 작성 또는 fixture/historical value로의 backfill

## Required Verification

1. Focused tests에서 altered Acceptance commit, hash, path, task-specific result가 collector 실행 전에 모두 거부되는지 확인한다.
2. Physics-executed SIM-008/SIM-009 subject는 structured time과 actual measurement 중 하나라도 없거나 `OPTIONAL`이면 거부되고, 구조적으로 증명된 pre-physics path만 두 필드를 `NOT_APPLICABLE`로 허용하는지 확인한다.
3. `SIM009-NAV-TIMEOUT-RETRY`, `SIM009-VLA-TIMEOUT`, `SIM009-VLA-UNKNOWN` 및 applicable Verification path의 reconciliation/retry/Verification 구조와 correlation identity가 Evidence에 보존되는지 확인한다.
4. `pytest -q tests/test_simulation_provenance_qualification.py`를 통과시킨다.
5. Qualified runtime에서 canonical runner를 실행해 정확히 11개 고유 subject, frozen binding, READY result를 가진 `results/simulation/SIM-Q01_provenance_qualification.json`을 생성하고 독립 검증한다.

## Assumptions Forbidden

- 현재 worktree Acceptance가 frozen binding과 같다고 가정하지 않는다.
- `physics_measurement=OPTIONAL` 또는 timing만으로 physics measurement 요구가 충족된다고 가정하지 않는다.
- decision/result/status 요약이 retry/reconciliation/recovery/Verification 의미 전체를 보존한다고 가정하지 않는다.
- unit test 통과를 실제 runtime qualification 또는 canonical Evidence의 대체물로 사용하지 않는다.
- missing Evidence를 수동 JSON, historical result, expected value로 채우지 않는다.

## Next Action

IMPLEMENT_RESOLVED_FIX

Final diagnosis status: RESOLVED
