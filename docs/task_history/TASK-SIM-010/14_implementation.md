# Implementation — TASK-SIM-010

- Result: IN PROGRESS
- Authority: `tasks/TASK-SIM-010.md` §14, `13_diagnosis.md`
- Boundary: `observability_regression.py`, regression runner, focused tests only

## Bounded plan

- 고정 Q01 Acceptance commit/path에서 Evidence blob과 SHA256를 해석하고, exact eleven subject 및 predecessor binding을 fail-closed로 검증한다.
- historical oracle와 qualification observation을 별도 namespace로 정규화하여 replay는 historical-only, physics는 oracle-versus-observation으로 평가한다.
- immutable candidate/baseline detached-worktree regression 비교와 node-plus-signature 분류를 보강하고 focused tests로 검증한다.
