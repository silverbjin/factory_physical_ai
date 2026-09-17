# Review — TASK-SIM-006

- Recommendation: REJECT
- Failed Gates: Requirements, Contract, Invariants, Tests, Evidence
- Validation: focused PASS (40 passed); `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — accepted source provenance가 해당 normalized record에 결속된다는 주장을 현재 구현/검증이 뒷받침하지 못함

## Blocking Findings

### SIM006-REREV-002 — HIGH

- Requirement / Contract: R1, R6, R7; `simulation_execution_contract_v1.md` §11
- File / Symbol: `src/simulation_runtime/verification_backend.py` / `_validate_simulator_source_identity`
- Issue: `source_identity`가 원래 adapter input record가 아니라 accepted artifact 내의 임의 identity 중 하나와만 일치하면 통과한다. 실제 SIM-004 success observation의 identity를 accepted `invalid_goal` record identity로 교체해도 `success` / `uncertain` / `RECONCILE`이 반환된다.
- Why it blocks acceptance: source provenance가 normalized reference의 action/record와 독립적으로 결속·검증되지 않아, 유효하지만 다른 upstream identity로의 provenance substitution이 fail closed되지 않는다.
- Recommended remediation: source identity와 verified upstream record identity를 action/record binding으로 보존하고, `_validate_evidence`에서 normalized reference/payload가 동일 verified record에서 유도됐음을 검증한다. 유효한 다른 accepted identity로의 대체도 실패하는 Gazebo 및 MuJoCo 회귀 테스트를 추가한다.
