# Diagnosis — TASK-SIM-010

- Status: RESOLVED
- Trigger: Review `06_review.md`가 synthetic normalization과 검증되지 않은 baseline 분류 때문에 REJECT
- Triggering status: REJECTED / FIX REQUIRED
- Finding IDs: `SIM010-REV-001`, `SIM010-REV-002`

## Trigger

`results/simulation/SIM-010_observability_regression.json`이 predecessor에 없는 identity, provenance, scenario, replay 값을 생성하여 `SIM_OBSERVABILITY_REGRESSION_READY`를 기록했고, full-suite 실패도 실제 baseline 실행 없이 `PROVEN_PREEXISTING`으로 분류했다.

## Requirement / Contract

TASK R2–R11과 EC2–EC6은 실제 accepted run 관계, exact source/config hash, 실제 replay/semantic 비교, fail-closed Evidence, 동일 regression command 실행 기록을 요구한다. `simulation_execution_contract_v1.md`는 required identity를 default할 수 없고 관련 call의 `mission_id`, `action_id`, `request_id`, `trace_id` 관계를 그대로 보존하도록 규정한다.

## Authoritative Source

- `tasks/TASK-SIM-010.md`
- `docs/contracts/simulation_execution_contract_v1.md`
- `results/reviews/SIM-003_acceptance.json` through `SIM-009_acceptance.json`
- 각 Acceptance가 고정한 accepted commit의 declared Evidence blob
- `docs/task_history/TASK-SIM-010/06_review.md`
- `src/simulation_runtime/observability_regression.py`
- `scripts/run_simulation_observability_regression.py`
- `tests/test_simulation_observability_regression.py`
- `results/simulation/SIM-010_observability_regression.json`

## Root Cause

`_normalize_evidence()`가 서로 다른 predecessor schema를 하나의 artifact-level run으로 취급하고, recursive `_find_first()` 결과와 `accepted-*`, `accepted-artifact`, Evidence digest, zero/default 값을 조합한다. 이 때문에 서로 다른 scenario의 identity와 failure가 한 correlation에 섞이고, aggregate/provenance artifact인 SIM-003/SIM-006에도 존재하지 않는 run이 만들어진다. 이어서 fabricated `accepted == accepted` scenario와 task result 기반 replay가 PASS하므로 `build_regression_evidence()`가 결측을 탐지하지 못한다.

별도 원인으로 runner의 `PROVEN_PREEXISTING_FAILURES`는 node ID 상수일 뿐이다. baseline commit에서 동일 command를 실행하거나 failure signature를 비교하지 않아 `PROVEN_PREEXISTING`이라는 관찰을 증명하지 않는다.

## Fault Domain

`SIM010_IMPLEMENTATION_DEFECT` — target normalization/data model, regression provenance validation, test coverage. Predecessor Evidence나 contract의 결함으로 판정하지 않는다.

## Resolution

Accepted-source index와 normalized run/scenario collection을 분리한다. SIM-003 through SIM-009 source row는 exact Acceptance path/hash, accepted commit, Evidence path/blob hash, task decision만 기록한다. Run/scenario row는 task-specific extractor가 같은 scenario/execution subtree에서 실제 값을 읽을 때만 생성하며 source JSON path를 함께 기록한다. Aggregate 또는 provenance-only artifact에 run identity를 만들지 않는다.

SIM-004/005 component scenarios, SIM-007 profile smoke, SIM-008 normal E2E, SIM-009 mandatory failures는 각각의 실제 schema를 명시적으로 해석한다. 하나의 artifact에서 첫 값을 고르는 recursive search를 금지하고, scenario 사이 identity/failure/decision을 혼합하지 않는다. Gazebo/MuJoCo provenance와 source/config hashes는 accepted blob의 명시적 path/hash/version/settings만 사용한다. 필수 값, 관계, applicable scenario, replay input, invariant 또는 tolerance가 없으면 해당 row와 최종 result를 BLOCKED로 만들며 placeholder, Evidence digest 대용, `not_applicable`, zero, 또는 accepted-result 자기비교를 생성하지 않는다.

Full regression은 current worktree와 `6909c6cceb727598570f6e170ae8d1d293418c9a`의 disposable isolated worktree에서 동일한 declared pytest command를 실제 실행한다. 양쪽의 node ID와 정규화된 stable failure signature가 모두 일치할 때만 `PROVEN_PREEXISTING`이며, baseline 실행/파싱/cleanup 실패나 signature 차이는 `POSSIBLY_TASK_RELATED`와 BLOCKED로 처리한다.

## Authorized Correction Boundary

- `src/simulation_runtime/observability_regression.py`: generic `_find_first`/synthetic `_normalize_evidence` 제거 또는 대체, source index/run separation, explicit task-specific extraction, fail-closed validation, actual replay/semantic comparison
- `scripts/run_simulation_observability_regression.py`: isolated baseline/current execution, signature capture/comparison, truthful Evidence recording과 cleanup
- `tests/test_simulation_observability_regression.py`: real-shape positive fixtures와 모든 fail-closed/baseline negative coverage
- 검증 성공 후 TASK-owned `results/simulation/SIM-010_observability_regression.json`, `docs/simulation/simulation_observability_regression_v1.md` 재생성

## Protected Boundary

SIM-003 through SIM-009 Acceptance, Evidence, TASK/history/review, accepted commits와 `docs/contracts/`, `scripts/codex/run_task_orchestrator.py`, Acceptance tooling/policy, unrelated source/tests/configs는 변경하지 않는다. Predecessor 결측을 이 TASK에서 보완하거나 physics/behavior를 수정하지 않는다.

## Required Verification

- Focused pytest가 rich/minimal Acceptance와 immutable accepted-blob resolution을 PASS
- invalid/missing commit, missing blob/path, malformed JSON, task/result mismatch, rich hash/path conflict를 모두 fail closed
- synthetic identity/provenance/hash/scenario/replay rejection과 cross-scenario correlation 혼합 방지 테스트를 PASS
- SIM-008 normal scenario와 모든 mandatory SIM-009 scenario ID가 실제 source path 및 동일-subtree identity/timeline으로 추적됨을 확인
- aggregator가 exact source index와 실제 provenance를 기록하고 결측 시 `SIM_OBSERVABILITY_REGRESSION_BLOCKED`를 반환
- baseline/current 동일 full pytest command의 node ID + stable signature 비교와 baseline failure/parse/cleanup 실패 경계를 테스트
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_observability_regression.py`
- TASK aggregator, full repository regression, `git diff --check`

## Next Action

RESUME_FIX

Final diagnosis status: RESOLVED
