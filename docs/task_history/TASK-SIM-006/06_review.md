# Review — TASK-SIM-006

- Recommendation: REJECT
- Failed Gates: Requirements, Contract, Invariants, Tests, Evidence
- Validation: focused PASS (33 passed); `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — `SIM_VERIFICATION_BACKEND_READY`가 frozen observation hash semantics 위반을 반영하지 않음

## Blocking Findings

### SIM006-REREV-002 — HIGH

- Requirement / Contract: R1, R6, R7; `simulation_execution_contract_v1.md` §11
- File / Symbol: `src/simulation_runtime/verification_backend.py` / `_normalized`, `normalize_gazebo_observation`, `normalize_mujoco_observation`, `VerificationBackend._validate_evidence`
- Issue: Gazebo/MuJoCo upstream artifact hash를 normalized `ObservationPayload`의 `content_sha256`로 재사용하고, 두 source의 canonical payload hash 검증을 생략함. `source_identity`도 실제 upstream identity와 분리된 값이 아니라 생성된 reference의 복사본임.
- Why it blocks acceptance: frozen contract는 `content_sha256`를 canonical observation object의 hash로 정의한다. 현재 구현은 normalized content와 identity/hash binding을 검증하지 못하므로 malformed 또는 함께 변조된 reference/source identity를 fail closed하지 못함.
- Recommended remediation: normalized payload의 canonical hash를 contract reference에 사용하고 모든 source에서 재계산 검증한다. upstream evidence/artifact identity는 별도 immutable provenance로 보존·검증하고, 해당 binding 및 동시 변조 실패를 테스트한다.
