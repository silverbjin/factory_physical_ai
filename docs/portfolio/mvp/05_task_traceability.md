# TASK Traceability

| TASK | Goal | Major artifacts | Tests / evidence | First review | Fixes | Final result | Commit |
|---|---|---|---|---|---|---|---|
| `TASK-MVP-001` | Korean mission을 validated structured mission으로 변환 | `src/contracts/mission.py`, `src/factory_agent/` | `tests/test_factory_agent.py`, `results/mvp/MVP-001.json` | per-task review record 없음; global index는 `ACCEPTED` | strict provider/schema validation은 implementation evidence에 반영 | `ACCEPT` (global index) | `51a9bef` `feat(mvp): establish factory agent vertical slice` |
| `TASK-MVP-002` | finite mission/action state model | `src/mission_runtime/state.py` | `tests/test_mission_runtime.py`, `results/mvp/MVP-002.json` | per-task review record 없음; global index는 `ACCEPTED` | transition invariant 검증이 validation commit에 포함 | `ACCEPT` (global index) | `06fded7` implementation, `ce828f1` validation follow-up |
| `TASK-MVP-003` | typed tool gateway와 fakes | `src/factory_tools/gateway.py` | `tests/test_factory_tools.py`, `results/mvp/MVP-003.json` | `REJECT` | request validation/fake boundary 보강 | `ACCEPT` | `2c0270c` `feat(mvp): add deterministic factory tool gateway and skill fakes` |
| `TASK-MVP-004` | one timeout + bounded recovery | `src/mission_runtime/recovery.py` | `tests/test_recovery.py`, `results/mvp/MVP-004.json` | `ACCEPT` | 없음 | `ACCEPT` | `cbb002d` `feat(mvp): implement timeout reconciliation and bounded recovery` |
| `TASK-MVP-005` | SQLite persistence와 run evidence | `src/mission_runtime/persistence.py` | `tests/test_persistence.py`, `results/mvp/MVP-005.json` | `REJECT`: attempted-call correlation/version 부족 | immutable trace와 derived `tool_call_valid` | `ACCEPT` | `6561809` `feat(mvp): persist mission lifecycle and structured evidence` |
| `TASK-MVP-006` | canonical normal E2E | `src/mission_runtime/normal.py` | `tests/test_normal_e2e.py`, `results/mvp/MVP-006.json` | `REJECT`: attempted-call/result correlation bypass | tamper rejection test와 strict cross-check | `ACCEPT` | `6e5e549` `test(mvp): validate canonical normal end-to-end mission` |
| `TASK-MVP-007` | canonical failure/recovery E2E | `src/mission_runtime/failure_recovery.py` | `tests/test_failure_recovery_e2e.py`, `results/mvp/MVP-007.json` | `REJECT`: wrapper correlation bypass | WMS/recovery/artifact cross-check와 tamper test | `ACCEPT` | `95cb075` `test(mvp): validate single-failure recovery end to end` |
| `TASK-MVP-008` | reproducible portfolio release | `docs/mvp/day10_mvp.md`, `scripts/` | `results/mvp/release/day10_release.json` | `ACCEPT` | 없음 | `ACCEPT` | `0b8c224` `docs(mvp): publish day-10 physical AI portfolio release` |

## 읽는 방법

상세 workflow는 [`docs/task_history/README.md`](../../task_history/README.md)와 각 `TASK-MVP-00N/` 디렉터리에 있다. MVP-001/002의 per-task history에는 independent review 파일이 남아 있지 않지만, global index, evidence, source/tests, 그리고 Git commit이 acceptance/implementation trace를 제공한다. 이 문서는 그 이력 공백을 review가 존재했다는 식으로 보완하지 않는다.

MVP-003/005/006/007은 `REJECT → Fix → ACCEPT` 기록이 남아 있어, acceptance 전 defect discovery와 regression 보강을 직접 추적할 수 있다.
