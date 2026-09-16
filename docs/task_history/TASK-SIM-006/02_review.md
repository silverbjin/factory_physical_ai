# Review — TASK-SIM-006

- Recommendation: REJECT
- Failed Gates: Requirements, Tests, Evidence
- Validation: focused 31 PASS; `git diff --check` PASS; regression NOT REQUIRED
- Evidence: FAIL — `SIM_VERIFICATION_BACKEND_READY` 주장이 R1/R7 검증 결과와 불일치

## Blocking Findings

### SIM006-REV-001 — HIGH

- Requirement / Contract: R1, Scope 1
- File / Symbol: `src/simulation_runtime/verification_backend.py` / `normalize_gazebo_observation`, `normalize_mujoco_observation`
- Issue: 두 어댑터가 accepted SIM-004 Navigation/system 관측과 SIM-005 manipulation 관측 구조를 변환하지 않고, 이미 정규화된 `{quality, part_id, location_id}`를 받아 source 문자열만 붙인다. 테스트도 accepted backend 출력 대신 동일한 수제 payload만 사용한다.
- Why it blocks acceptance: accepted cross-simulator evidence 모델에 대한 실제 adapter 경계와 traceability가 없어 simulator-neutral Verification input 구현을 입증할 수 없다.
- Recommended remediation: SIM-004/SIM-005의 accepted 관측 구조를 명시적으로 받아 contract payload/identity/provenance로 변환하는 adapter와 backend-shape 테스트를 추가한다.

### SIM006-REV-002 — HIGH

- Requirement / Contract: R7, R8
- File / Symbol: `src/simulation_runtime/verification_backend.py` / `NormalizedObservation`, `VerificationBackend._validate_evidence`
- Issue: `@dataclass(frozen=True)` 내부의 `reference`, `payload`, `provenance`가 mutable `dict`이며, `backend_id`는 임의 문자열이고 Verification에서 검증되지 않는다. identity/provenance를 변조한 후 request ref를 맞추면 `pass`가 반환된다.
- Why it blocks acceptance: immutable observation identity/version/hash 및 accepted backend provenance 보존·검증 요구를 위반하고, caller-controlled provenance가 검증 결과에서 무시된다.
- Recommended remediation: 정규화 결과를 deep-immutable로 만들고 accepted backend identity/revision을 구조화해 참조 및 payload hash와 함께 검증하며, 변조·임의 provenance 케이스를 fail-closed 테스트한다.
