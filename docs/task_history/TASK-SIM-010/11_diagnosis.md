# Diagnosis — TASK-SIM-010

- Status: RESOLVED
- Trigger: R2–R7 normalized-run 차단이 extractor 결함, contract applicability, accepted provenance 결측을 혼합
- Triggering status: `SIM_OBSERVABILITY_REGRESSION_BLOCKED`
- Finding IDs: `SIM010-REV-001`, `SIM010-REV-002`

## Root Cause

현재 validator가 operation-message run, profile/artifact aggregate, backend qualification provenance를 하나의 필수-field 집합으로 평가한다. SIM-004 bounded/wall-time, SIM-007 accepted failure outcome, SIM-009 failure/Verification semantics는 명시적 accepted path에서 추출 가능하지만 누락되었다. 반면 SIM-004 simulation time, SIM-005 `trace_id`, 일부 run-local config/provenance는 accepted state에 존재하지 않는다. SIM-008의 `config_sha256`을 bridge/launch 양쪽 의미로 재사용하는 현재 mapping도 authoritative binding이 아니다.

## Requirement / Contract

`TASK-SIM-010` R2는 indexed operation run의 reconstructable correlation을 요구하지만 모든 aggregate row에 동일한 identity 필드를 요구하지 않는다. `simulation_execution_contract_v1.md`에서 common request/result는 `mission_id`, `request_id`, `trace_id`를 요구하고 `action_id`는 action-bound result에만 추가로 요구한다. Verification operational failure는 `error`를 가지며 `verdict`를 갖지 않는 것이 정상이다.

## Authoritative Sources

- `tasks/TASK-SIM-010.md`
- `docs/contracts/simulation_execution_contract_v1.md`
- accepted SIM-004 blob at `b7e8266abd17f48c18cca94d9433db50fd55464d`
- accepted SIM-005 blob at `542514a4d10bc03087834e8a5f672d53afe6aa21`
- accepted SIM-007 blob at `228eb7745aa05c230e1b272184601b5afd53853b`
- accepted SIM-009 blob at `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be`
- `src/simulation_runtime/observability_regression.py`
- `results/simulation/SIM-010_observability_regression.json`

## Resolution

- SIM-004: wall time/bounds 및 hashed bridge/run config는 extractor correction 대상이고 simulation-time은 accepted Evidence gap이다.
- SIM-005: `trace_id`는 다른 accepted artifact에서도 해당 run과 결합할 authority가 없는 true gap이다.
- SIM-007: `profile_smoke[]`는 multi-action aggregate이므로 단일 `request_id`/`action_id` operation run으로 강제하지 않는다. accepted failure outcome은 accepted expected outcome과 비교한다.
- SIM-009: `manifest_sha256`, `error.code`, `mismatch_code`, `verdict`, decision/route는 extractor correction 대상이다. `/accepted_bindings`와 matching `component_version`은 version-wide SIM-004/005 backend provenance만 조건부 결합하며 run-local world/config/time을 대체하지 않는다.
- 기존 accepted artifact mutation 없이 READY가 되려면 누락 run-level provenance를 새로 측정하고 immutable하게 bind하는 predecessor qualification task가 필요하다.

## Modification Scope

- 후속 TASK-SIM-010 Fix는 extractor/applicability/expected-outcome 비교만 수정 가능하며 누락 값을 생성할 수 없다.
- 별도 qualification task는 additive immutable provenance와 SIM-010 소비 contract를 명시해야 한다.

## Protected Scope

SIM-003..SIM-009 Acceptance/Evidence/contracts/accepted commits, orchestrator, 기존 predecessor history는 변경하지 않는다.

## Verification

명시적 source path, same-scenario identity, component-version binding, aggregate-vs-operation applicability, true-gap fail-closed 테스트가 필요하다. READY 판정은 qualification artifact가 없으면 금지한다.

## Next Action

IMPLEMENT_RESOLVED_FIX

Final diagnosis status: RESOLVED
