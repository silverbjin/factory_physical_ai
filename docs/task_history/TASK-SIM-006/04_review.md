# Review — TASK-SIM-006

- Recommendation: REJECT
- Failed Gates: Requirements, Tests, Evidence
- Validation: focused 33 PASS; `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — `SIM_VERIFICATION_BACKEND_READY` 주장이 R1, R2, R7, R8 검증 결과와 불일치

## Blocking Findings

### SIM006-REREV-001 — HIGH

- Requirement / Contract: R1, R2, R7, R8; `verification.verify` exact-match semantics
- File / Symbol: `src/simulation_runtime/verification_backend.py` / `normalize_gazebo_observation`, `normalize_mujoco_observation`
- Issue: Gazebo adapter의 `part_id`와 MuJoCo adapter의 `part_id`, `location_id`가 accepted backend observation이 아닌 caller 인자에서 생성된다. 또한 MuJoCo의 accepted `observation_identity.content_sha256`를 보존·검증하지 않고 생성한 payload hash로 교체한다.
- Why it blocks acceptance: caller가 expected state와 같은 값을 전달하면 accepted simulator evidence가 그 state를 관측하지 않았어도 `pass`/`CONFIRMED`가 되므로 exact-match, immutable identity/hash, no-bypass 요구를 충족하지 못한다.
- Recommended remediation: accepted observation에서 `part_id`/`location_id`를 직접 도출·검증할 수 없는 backend은 `insufficient`/`uncertain`으로 fail closed하고, 상태와 identity/hash가 accepted evidence에서 나오는 실제 shape에 대해서만 `pass`를 허용하며 caller-supplied assertion이 `pass`를 만들지 못하는 test를 추가한다.
