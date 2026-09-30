# Implementation — TASK-SIM-010

- Result: COMPLETE
- Evidence: `results/simulation/SIM-010_observability_regression.json`
- Changed areas: accepted-commit resolver, regression index/runner, focused tests, observability report
- Validation: focused PASS (6 passed); full pytest 347 passed / 4 failed, `PROVEN_PREEXISTING` against `6909c6cceb727598570f6e170ae8d1d293418c9a`; `git diff --check` PASS
- Deviation: baseline disposable worktree creation was sandbox-blocked; an isolated shared clone at the same commit produced the required baseline evidence
- Next: Independent Read-only Review

## Delta

- minimal SIM-009 Acceptance를 immutable `accepted_commit` Git blob으로 해석하고 SHA-256을 재계산하도록 변경했다.
- rich Acceptance binding 충돌, 잘못된 commit/blob/task/result를 fail-closed로 처리했다.
- predecessor별 Evidence shape을 Simulation 전용 공통 envelope로 정규화했다.
- working tree 변조를 무시하고 accepted blob을 사용하는 회귀 검증을 추가했다.
- full regression의 동일 baseline 실패 4건을 `PROVEN_PREEXISTING`으로 Evidence에 기록했다.
