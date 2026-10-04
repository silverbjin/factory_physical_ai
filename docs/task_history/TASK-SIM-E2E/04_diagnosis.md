# Diagnosis — TASK-SIM-E2E

- Status: RESOLVED
- Trigger: Review REJECT 후 `SIM-E2E-REV-001`, `SIM-E2E-REV-002`의 unsafe-positive 원인 규명
- Triggering status: 최소 위조 fixture, acceptance `task_id` 불일치, 충돌 duplicate index row, `acceptance_path` 불일치가 모두 `SIM_E2E_QUALIFIED`를 반환
- Finding IDs: `SIM-E2E-REV-001`, `SIM-E2E-REV-002`

## Trigger

현재 verifier가 canonical accepted Evidence의 완전한 predicate proof와 정확한 immutable identity를 요구하지 않아, 축약·모순 fixture가 positive decision을 만들 수 있다.

## Requirement / Contract

`tasks/TASK-SIM-E2E.md` R1–R3, R5–R13은 정확한 predecessor identity, 유일한 acceptance/Evidence/index chain, canonical underlying Evidence schema의 predicate별 재구성을 요구한다. 누락·모순·모호성·부재 기반 추론은 `UNVERIFIED` 또는 `FAIL`이어야 한다.

## Authoritative Source

- `tasks/TASK-SIM-E2E.md`
- `docs/task_history/TASK-SIM-E2E/03_review.md`
- `scripts/verify_simulation_e2e_qualification.py`
- `tests/test_simulation_e2e_qualification.py`
- `results/reviews/SIM-003_acceptance.json` through `results/reviews/SIM-010_acceptance.json`
- 위 acceptance/index가 bind한 `results/simulation/SIM-003_baseline.json` through `SIM-010_observability_regression.json`

## Root Cause

`PREDICATES`가 canonical schema validator가 아니라 부분 필드, 문자열 포함, 단순 개수, 필드 부재, vacuous `all()`을 성공 증거로 사용하는 permissive lambda 집합이다. 예를 들어 non-empty `scenarios`, JSON 내 `jazzy`/`gazebo` 문자열, `forbidden_state_transition` 문자열 부재, 빈 profile 집합이 mandatory proof를 대신한다. 테스트의 qualifying fixture도 이 축약 schema를 그대로 발명하여 verifier와 같은 잘못된 가정을 검증한다.

동시에 `evaluate`가 `accepted_source_index`를 dict comprehension으로 축약하여 duplicate/conflict를 은폐하고, acceptance의 정확한 `task_id` 및 index row의 canonical `acceptance_path`를 검증하지 않는다. 따라서 immutable chain의 identity가 틀려도 hash만 재작성하면 positive decision이 가능하다.

## Fault Domain

Target verifier와 task-owned focused tests.

## Authorized Correction Boundary

- `scripts/verify_simulation_e2e_qualification.py`: `PREDICATES`, `evaluate`, 필요한 task-local schema/reconstruction helper만 수정한다.
- `tests/test_simulation_e2e_qualification.py`: canonical-shaped qualifying fixture와 adversarial identity/schema/predicate tests를 추가·수정한다.
- 수정된 verifier 결과와 일치하도록 `results/simulation/SIM-E2E_qualification.json`, `docs/simulation/simulation_e2e_qualification_v1.md`만 재생성한다.

수정은 다음을 요구한다.

1. index를 list로 검증하여 `SIM-003`–`SIM-009` 각각 정확히 한 row만 허용하고 duplicate를 모두 거부한다.
2. expected `task_id`, `short_task_id`(존재 시), acceptance status/decision, `acceptance_path`, acceptance hash, accepted commit/reviewed revision, Evidence path/hash를 상호 검증한다. `SIM-009`의 Evidence identity는 acceptance에 없는 값을 발명하지 않고 유일한 SIM-010 index binding에서 해석한다.
3. predicate ownership/source chain은 TASK의 frozen matrix와 required source contract를 task-local 명시적 schema로 정의하고, canonical Evidence의 exact field/value와 필수 scenario ID 전체를 검증한다. 문자열 검색, 단순 존재/개수, 부재 기반 false 증명, 빈 collection의 vacuous success를 제거한다.
4. `physical_dependency`, forbidden transition, leaked process, integrated-world/dual-world authority, provenance, observability/reproducibility를 실제 bound fields에서 재구성하며 output 상수를 proof로 사용하지 않는다.
5. full canonical-shaped positive fixture에 더해 duplicate/conflict, task/path identity mismatch, missing source, wrong READY/BLOCKED, stale hash/revision, forged top-level, incomplete scenario class, absent safety field, conditional lookalike non-repair를 각각 fail-closed로 검증한다.

## Protected Boundary

Predecessor implementation, acceptance JSON, underlying Evidence, SIM-010 source index, shared runtime/contract/backend/mission code, TASK specification, Git history는 변경하지 않는다. canonical negative result를 predecessor remediation로 바꾸지 않는다.

## Required Verification

1. `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_e2e_qualification.py`
2. canonical CLI가 stdout 한 줄, exit `0`, `SIM_E2E_NOT_QUALIFIED`를 반환하는지 확인한다.
3. 네 unsafe-positive reproducer와 새 predicate/schema adversarial cases가 모두 `SIM_E2E_NOT_QUALIFIED`인지 확인한다.
4. canonical predecessor acceptance/Evidence hash가 테스트 전후 불변인지 확인한다.
5. `git diff --check`와 TASK Section 7.4 allowlist를 확인한다.

## Assumptions Forbidden

- `predicate_sources`라는 canonical field가 SIM-010에 존재한다고 가정하지 않는다.
- READY/PASS/`qualified=true`, scenario 존재/개수, 문자열 포함, 필드 부재만으로 predicate를 PASS시키지 않는다.
- duplicate index row를 dict overwrite로 정규화하지 않는다.
- acceptance `task_id` 또는 recorded path가 파일 위치와 같을 것이라고 검증 없이 가정하지 않는다.
- current `HEAD`만으로 staleness를 판단하지 않는다.
- `SIM-007`의 accepted BLOCKED result를 READY로 승격하거나 predecessor Evidence를 수정하지 않는다.

## Next Action

FIX_RESOLVED_DIAGNOSIS

Final diagnosis status: RESOLVED
