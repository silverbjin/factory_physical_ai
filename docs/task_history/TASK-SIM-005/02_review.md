# Review — TASK-SIM-005

- Recommendation: REJECT
- Failed Gates: Requirements, Contract, Invariants, Tests, Evidence
- Validation: focused pytest 42 PASS; `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — 측정된 manipulation 상태 전이와 invalid observation 시나리오가 증명되지 않음

## Blocking Findings

### SIM-005-REV-001 — HIGH

- Requirement / Contract: R1, R9; `action_status.get` identity/reconciliation semantics
- File / Symbol: `src/simulation_runtime/mujoco_vla_backend.py` / `MuJoCoVLABackend.records`, `action_status_get`
- Issue: 상태 레코드가 `action_id`에만 바인딩되어 다른 `mission_id`의 조회도 성공 결과를 반환함.
- Why it blocks acceptance: authoritative reconciliation이 원래 실행의 mission/action identity를 보존하지 않아 잘못된 작업을 성공으로 확정할 수 있음.
- Recommended remediation: 실행 레코드에 `mission_id`, `action_id`와 불변 evidence를 함께 저장하고 조회 identity 불일치를 fail closed로 처리하는 테스트를 추가할 것.

### SIM-005-REV-002 — HIGH

- Requirement / Contract: R4, R5, R6; measured MuJoCo manipulation and failure semantics
- File / Symbol: `src/simulation_runtime/mujoco_vla_backend.py` / `execute`, `_step_physics`
- Issue: nominal, grasp-miss, contact-loss가 동일한 MuJoCo 초기 상태와 제어 시퀀스를 실행하며, 실패 분류는 측정된 contact/slip 상태가 아니라 요청 `task_id`로 결정됨.
- Why it blocks acceptance: grasp miss와 contact loss가 MuJoCo physics로 감지되었다는 TASK 핵심 요구를 증명하지 못함.
- Recommended remediation: 시나리오별 물리 초기조건/제어와 contact/object-state 측정을 구현하고 결과 분류 및 테스트를 해당 측정값에 연결할 것.

### SIM-005-REV-003 — HIGH

- Requirement / Contract: R4, R6, R8, R10; required machine-readable Evidence
- File / Symbol: `scripts/run_simulation_mujoco_vla.py`, `results/simulation/SIM-005_mujoco_vla_backend.json`
- Issue: Evidence에는 nominal 상태 전이 측정값, grasp/contact 측정값, invalid/ambiguous observation 시나리오, observation/policy identity가 없고 비-nominal PASS는 단순히 `result != success`로 판정됨.
- Why it blocks acceptance: 필수 시나리오와 provenance가 독립적으로 검증 가능한 형태로 증명되지 않아 `SIM_MANIPULATION_BACKEND_READY`를 신뢰할 수 없음.
- Recommended remediation: 각 시나리오의 기대 error/status와 측정 전후 상태를 엄격히 검증하고 required identities 및 invalid-observation 결과를 Evidence에 기록할 것.
