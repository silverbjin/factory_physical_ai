# Diagnosis — TASK-SIM-Q01-MIN

- Status: RESOLVED
- Trigger: Re-review REJECT의 protected Evidence, source revision, validation launcher blocker 진단
- Triggering status: `REJECTED / FIX REQUIRED`
- Finding IDs: `Q01MIN-PROTECTED-EVIDENCE-005`, `Q01MIN-SOURCE-REVISION-006`, `Q01MIN-VALIDATION-007`

## Trigger

`19_review.md`는 accepted predecessor Evidence 두 파일 변경, canonical Q01 Evidence의 선언 revision과 실제 source hash 불일치, 필수 literal `pytest` 명령 실패를 확인했다.

## Requirement / Contract

- `tasks/TASK-SIM-Q01-MIN.md` Sections 7, 10–12는 exact immutable source authority와 canonical Evidence를 요구하고 accepted SIM-004/SIM-008 Evidence 변경을 금지한다.
- `04_diagnosis.md` Required Verification 4는 `pytest -q tests/test_simulation_provenance_qualification.py`의 PASS를 요구한다.
- canonical Evidence의 `source_git_sha`는 run-local source path/hash를 재현하는 immutable commit이어야 하며 uncommitted worktree를 대신 지칭할 수 없다.

## Authoritative Source

- `tasks/TASK-SIM-Q01-MIN.md`
- `docs/task_history/TASK-SIM-Q01-MIN/04_diagnosis.md`
- `docs/task_history/TASK-SIM-Q01-MIN/17_autonomous_gate_resolution.md`
- `docs/task_history/TASK-SIM-Q01-MIN/19_review.md`
- commits `c3027fb708186d6ba2fa96444e8aae553687939d` and `d3952bd`
- `scripts/run_simulation_provenance_qualification.py:169-188`
- `scripts/q01_execution_adapters.py:146-192`
- observed executable resolution: `pytest -> /usr/bin/pytest`, `python3 -> /home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3`

## Root Cause

Fix의 final qualification에 **clean immutable-source preflight boundary가 없었다**. Canonical runner는 dirty-worktree 검증 없이 `git rev-parse HEAD`를 `source_git_sha`로 기록하면서 source asset은 현재 worktree에서 hash했다. 그 결과 `c3027fb...`를 선언한 Evidence에 당시 uncommitted source hash가 들어갔다. 같은 worktree에는 ad hoc runtime 실행으로 변경된 protected predecessor Evidence가 이미 있었고, 이를 보호한다며 복원하지 않은 상태에서 orchestrator의 all-changes commit이 `d3952bd`에 포함했다.

검증 launcher도 같은 boundary에서 qualification되지 않았다. PATH의 simulation venv에는 `pytest` entry point가 없어서 literal 명령은 `/usr/bin/pytest`와 `/usr/bin/python3`를 사용하고 `mujoco` import에 실패하지만, `python3 -m pytest`는 qualified simulation interpreter에서 39 tests를 통과한다. 이는 test defect가 아니라 executable/interpreter 불일치다.

## Fault Domain

Target qualification finalization과 validation environment. Predecessor contract, MIN-Q01 architecture, subject semantics의 결함은 아니다.

## Authorized Correction Boundary

- `results/simulation/SIM-004_navigation_backend.json`: accepted commit `b7e8266a...`의 exact blob/SHA256 `b4c0ce91...`로 복원.
- `results/simulation/SIM-008_normal_system_e2e.json`: accepted commit `ea91e0c1...`의 exact blob/SHA256 `ebf0ef0a...`로 복원.
- `results/simulation/SIM-Q01_provenance_qualification.json`: source를 더 변경하지 않은 상태에서 immutable commit `d3952bd...`를 authority로 genuine bounded run을 새로 수행하여 재생성.
- 필요 시 Q01 runner에 clean/protected-artifact/source-hash fail-closed preflight만 추가할 수 있다. 추가 source 변경이 생기면 그 변경을 먼저 immutable commit으로 만든 뒤 qualification을 다시 수행해야 하며, uncommitted source로 Evidence를 생성해서는 안 된다.
- qualified simulation environment의 `pytest` entry point/PATH만 정합화하여 literal command가 `python3`와 같은 interpreter를 사용하게 한다. test skip, import 완화, semantic assertion 변경은 허용하지 않는다.

## Protected Boundary

- frozen predecessor Acceptance, accepted commits, 그리고 SIM-005/SIM-007/SIM-009 Evidence
- MIN-Q01 11-subject scope, applicability, semantic validators, frozen SIM-010
- predecessor Evidence를 새 runtime 결과로 재생성하거나 current rejected blob을 새 authority로 승격하는 행위
- canonical Q01 Evidence의 `source_git_sha` 또는 run-local 값을 수동 편집/과거 실행으로 backfill하는 행위
- MuJoCo test를 skip하도록 변경하거나 `/usr/bin/pytest` 실패를 무시하는 행위

## Required Verification

1. 복원 후 두 protected Evidence의 SHA256이 각각 frozen `b4c0ce91...`, `ebf0ef0a...`와 일치하고 다른 predecessor Acceptance/Evidence가 변경되지 않았음을 확인한다.
2. source 변경이 없는 immutable `d3952bd...` 기준으로 canonical runner를 새로 실행하고 exactly 11 subjects, validation `PASS`, `SIM_PROVENANCE_QUALIFICATION_READY`를 확인한다.
3. 새 Evidence의 `source_git_sha=d3952bd...` 및 모든 declared source path hash가 `git show d3952bd:<path>`에서 재현됨을 확인한다.
4. `pytest -q tests/test_simulation_provenance_qualification.py`가 qualified simulation interpreter로 실행되어 39 tests PASS해야 한다. `python3 -m pytest -q tests/test_simulation_provenance_qualification.py`도 동일하게 PASS해야 한다.
5. `git diff --check`를 통과하고 diff가 authorized correction boundary 및 diagnosis/history bookkeeping 밖으로 확장되지 않았음을 확인한다.

## Assumptions Forbidden

- `HEAD`가 존재한다는 이유만으로 worktree source가 그 commit과 동일하다고 가정하지 않는다.
- protected predecessor Evidence의 dirty/committed 변경을 사용자 소유 변경으로 간주해 보존하지 않는다.
- Q01 Evidence의 revision/hash만 수동 수정하면 기존 run이 새 immutable-source run이 된다고 가정하지 않는다.
- `pytest`와 `python3 -m pytest`가 같은 interpreter를 사용한다고 가정하지 않는다.
- test skip 또는 optional dependency 처리로 required semantic coverage를 대체하지 않는다.

## Next Action

RESUME_FIX

Final diagnosis status: RESOLVED
