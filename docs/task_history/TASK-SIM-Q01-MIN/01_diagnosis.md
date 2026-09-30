# Diagnosis — TASK-SIM-Q01-MIN

- Status: RESOLVED
- Trigger: `initial_red_classification`
- Triggering status: `RED`

## Trigger

분류기는 architecture/contract, authoritative source, live runtime, integration, Evidence 신호가 함께 있는 동결 계약을 `RED`로 판정했다. 이는 런타임 실패 자체가 아니라 구현 전 계약 경계 확인 요구다.

## Root Cause

현재 Q01 실행기는 MIN-Q01 계약 이전의 Full-Q01 readiness 구성을 유지한다. `scripts/run_simulation_provenance_qualification.py::required_subject_manifest`는 SIM-004/SIM-005/SIM-007을 readiness 집합에 포함하고, `collect_qualification_subjects`는 해당 경로를 실행한다. 또한 `QualificationSubject`/`validate_subject`는 operation timing을 숫자로만 요구하여 구조적으로 증명된 pre-physics 종료의 명시적 `NOT_APPLICABLE`을 표현할 수 없고, aggregator는 required subject의 누락만 검사하여 extra Full-Q01 subject를 거부하지 않는다.

로컬 focused test의 4개 FAIL은 제외 대상인 standalone SIM-005 테스트가 설치되지 않은 `mujoco`를 import한 환경 증상이며, MIN-Q01 readiness 실패 근거가 아니다.

## Requirement / Contract

`tasks/TASK-SIM-Q01-MIN.md` Sections 4, 6, 9, 10, 12에 따라 readiness에는 SIM-008 1개와 SIM-009 10개만 참여해야 한다. SIM-004/SIM-005/SIM-007은 immutable non-execution authority로 표현해야 하며, run-local 필드는 `REQUIRED | OPTIONAL | NOT_APPLICABLE`을 명시하고 extra subject, 누락, 잘못된 binding, 모호한 재사용을 fail closed 해야 한다.

## Authoritative Sources

- `tasks/TASK-SIM-Q01-MIN.md`
- `configs/simulation/min_q01_scope.json`
- predecessor Acceptance와 각 `accepted_commit`의 task-declared Evidence blob
- `src/simulation_runtime/provenance_qualification.py`
- `scripts/run_simulation_provenance_qualification.py`
- `scripts/q01_execution_adapters.py`
- `tests/test_simulation_provenance_qualification.py`

동결된 5개 predecessor commit/Evidence SHA256은 모두 재계산 결과 계약과 일치했다. machine scope는 중복 없는 정확히 11개 subject(SIM-008 1, SIM-009 10)를 선언한다.

## Fault Domain

Target implementation/validation. Architecture와 predecessor provenance는 충돌하지 않는다.

## Resolution

MIN-Q01 machine scope를 readiness manifest의 단일 입력으로 사용하고, canonical Q01 identity/token은 유지한다. readiness 실행은 SIM-008/SIM-009 11개만 수집하며 SIM-004/SIM-005/SIM-007은 immutable authority bindings로 직렬화한다. applicability를 명시적으로 모델링하고 structured execution state 없이 `NOT_APPLICABLE`을 허용하지 않으며, required 집합과 실제 operation 집합의 정확한 일치를 검증한다.

## Modification Scope

- `scripts/run_simulation_provenance_qualification.py`: MIN scope 로딩, 정확한 11-subject routing/readiness, non-execution authority 조립
- `src/simulation_runtime/provenance_qualification.py`: applicability와 authority representation, exact-set/fail-closed validation
- `scripts/q01_execution_adapters.py`: SIM-008/SIM-009 same-run 관측과 pre-physics 구조 상태의 명시적 `NOT_APPLICABLE`
- `tests/test_simulation_provenance_qualification.py`: MIN manifest, exclusions, applicability, binding/reuse, compatibility identity 회귀 검증
- `results/simulation/SIM-Q01_provenance_qualification.json`: 실제 bounded qualification 성공 시에만 canonical Evidence 생성

## Protected Scope

- `configs/simulation/min_q01_scope.json`과 `tasks/TASK-SIM-Q01-MIN.md`의 동결 계약
- accepted SIM-004/SIM-005/SIM-007/SIM-008/SIM-009 Evidence/Acceptance
- frozen SIM-010 state
- historical Full-Q01 task/history와 기존 구현 경로 자체
- `results/reviews/SIM-Q01_acceptance.json`은 독립 Review 이후 별도 acceptance 단계 전까지 생성/수정 금지

## Verification

1. focused unit tests에서 operation readiness 집합이 정확히 11개이며 extra/duplicate/missing/wrong binding/cross-scenario reuse를 거부하는지 확인한다.
2. simulator 실행 시 structured time이 필수이고, pre-physics `NOT_APPLICABLE`은 구조적 실행 상태와 justification 없이는 거부되는지 확인한다.
3. standalone SIM-004/SIM-005와 SIM-007 runtime/profile session이 readiness supplier로 호출되지 않는지 확인한다.
4. 다섯 Contract-B binding의 commit/blob SHA256과 unchanged Q01 task/result token을 확인한다.
5. qualified Gazebo/MuJoCo 환경에서 1개 SIM-008과 10개 SIM-009 bounded run을 수행해 canonical Evidence를 생성하고 READY를 확인한다. runtime dependency 부재는 READY로 우회하지 않고 BLOCKED로 남긴다.

## Assumptions Forbidden

- Full-Q01 25-subject manifest가 여전히 readiness authority라고 가정하지 않는다.
- 현재 worktree Evidence, historical timing, wall time, expected value로 run-local claim을 보충하지 않는다.
- `0.0` timing이나 필드 부재를 `NOT_APPLICABLE`로 해석하지 않는다.
- 로컬 `mujoco` 미설치를 계약 결함 또는 제외 대상 SIM-005 실행 요구로 해석하지 않는다.
- 구현 중 새로운 subject/claim을 조용히 추가하지 않는다. 필요 시 `MIN_Q01_SCOPE_REOPEN_REQUIRED`를 보고한다.

## Next Action

IMPLEMENTATION

Final diagnosis status: RESOLVED
