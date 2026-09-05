# Read-only Review — TASK-P0-007

## 1. 검토 정보

- TASK: `TASK-P0-007`
- 작업 유형: Independent Read-only Re-review
- 실행 순번: `03`
- 검토 대상 Git HEAD: `3d125c1a8b8b9c8522db3811b017d2f7741c89df`
- 검토 시작 시 Git 상태: clean
- 구현/source/evidence 변경: 없음
- Focused tests: 38 PASS, 0 FAIL
- Full regression: 114 PASS, 0 FAIL

## 2. 검토 결론

- Recommendation: `REJECT TASK-P0-007`
- BLOCKER: 2
- HIGH: 1
- MEDIUM: 1
- LOW: 0

Canonical resource 사실은 다음과 같이 일관된다.

```text
Local training classification: TRAINING_NOT_VERIFIED
Training execution mode: UNRESOLVED
Primary compute path: UNRESOLVED
Storage readiness: STORAGE_NOT_VERIFIED
Budget policy: UNRESOLVED
Budget feasibility: NOT_VERIFIED
Fallback compute: NOT_VERIFIED
Task-specific outcome: TRAINING_RESOURCE_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

`TRAINING_RESOURCE_BLOCKED`이므로 reject한 것이 아니다. Canonical artifact는 정직하게 blocked 상태를 보고한다. Reject 사유는 validator가 material/provenance/scope invariant가 깨진 rehashed READY artifact를 여전히 허용하고, bounded resource-metadata 요구가 완전하게 구현되지 않았기 때문이다.

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| P0-005/P0-006 context와 `DEVICE_IO_BLOCKED` 보존 | predecessor hash binding / C01 | predecessor/source hash test | accepted SHA-256 및 canonical predecessor fields | PASS |
| Local resource 측정과 6 GiB false-fit 방지 | `_nvidia`, `_torch_probe`, `_memory`, `_local_training_verified` | local classification/unsupported claim tests | `TRAINING_NOT_VERIFIED` | PASS |
| Execution mode별 concrete primary resource | `_primary_resource_valid`, `_material_predicates` | hybrid/local/resource negative tests | canonical `UNRESOLVED` blocker | FAIL — placeholder와 mode-role 누락 READY bypass |
| Storage readiness가 aggregate에 포함 | `_storage_valid`, C11 | `STORAGE_NOT_VERIFIED` negative test | C11 `BLOCKED` | PASS |
| Budget policy와 cost 산술 | `_numeric_budget_valid`, `_budget_material` | arithmetic/non-finite/prepaid tests | canonical `UNRESOLVED` | FAIL — prepaid entitlement가 primary resource와 연결되지 않음 |
| Fallback material validation | `_fallback_valid` | null fallback test | canonical fallback `NOT_VERIFIED` | FAIL — no-fallback rule token만으로 redundancy proof 없이 C15 PASS |
| Provenance가 READY predicate를 지배 | `_evidenced`, `_checks_from_material`, `validate_evidence` | invalid provenance/tamper tests | canonical provenance fields | FAIL — READY C08/C09/C10/C12/C14/C15가 `NOT_VERIFIED` provenance로 PASS 가능 |
| No actual training / scope preservation | C18/C19와 `scope_safety` | CLI scope assertions | canonical flags false | FAIL — generation/runtime training flags와 scope를 cross-check하지 않음 |
| Metadata operation boundedness | `_bounded_filesystem_metadata`, `_run` | delayed disk/is_dir/is_file tests | canonical timeout metadata | FAIL — `_memory`의 `/proc/meminfo` read가 unbounded |
| Canonical decision/auth consistency | check/blocker/decision projection | canonical and blocker tests | blocked + authorization fields | PASS |
| No training/procurement/downstream implementation | verifier/static scope | repository diff + regression | canonical scope flags | PASS |

## 4. 주요 Findings

### BLOCKER

#### `TASK-P0-007-REV-B02`

- File / Symbol: `scripts/verify_training_resource_readiness.py::_material_text`, `_evidenced`, `_budget_material`, `_fallback_valid`, `_checks_from_material`, `validate_evidence`
- Issue: mode/resource/budget/fallback/provenance domain validation이 여전히 coordinated/rehashed false READY를 허용한다.
- Independent reproduction:
  - primary `resource_id="unknown resource"`, `resource_class="unresolved resource"` → `TRAINING_RESOURCE_READY`, validation errors `[]`.
  - `EXISTING_PREPAID_RESOURCE.prepaid_resource_id`를 primary와 다른 resource로 지정 → `TRAINING_RESOURCE_READY`, errors `[]`.
  - `HYBRID_TRAINING`에서 local/training role split을 제거 → `TRAINING_RESOURCE_READY`, errors `[]`.
  - `fallback.required=false`와 constant rule/source assertion만 넣고 실제 fallback/redundancy evidence를 모두 비움 → C15 `PASS`, aggregate READY, errors `[]`.
  - valid READY fixture의 C08/C09/C10/C12/C14/C15는 모두 status `PASS`이면서 provenance `NOT_VERIFIED`; validator가 이를 허용한다.
- Why it matters: payload를 다시 hash하고 bound source verification까지 활성화해도 unsupported READY가 승인된다. 이는 B01의 핵심 위험이 완전히 제거되지 않았음을 뜻한다.
- Requirement affected: fail-closed principle, mode-specific validation, per-material provenance, primary-path budget feasibility, fallback proof, mandatory checks C08–C15, Decision Rules.
- Recommended remediation: placeholder taxonomy를 canonical enum/validated identity로 바꾸고, PASS check에 sufficient provenance를 강제하며, HYBRID role split을 material field로 검증한다. Budget evidence를 primary resource identity/class와 연결하고 fallback-not-required는 실제 redundancy/policy evidence를 검증해야 한다.

#### `TASK-P0-007-REV-B03`

- File / Symbol: `scripts/verify_training_resource_readiness.py::_material_predicates`, `validate_evidence`
- Issue: C18/C19는 `scope_safety`만 신뢰하고 `generation.training_executed` 및 `local_resources.torch_cuda.training_executed`와 cross-check하지 않는다.
- Independent reproduction: 각각의 training flag를 `true`로 바꾸고 checks/blockers/decision/payload hash를 재계산한 artifact가 `TRAINING_RESOURCE_READY`, validation errors `[]`로 승인됐다. `verify_bound_files=true`에서도 동일했다.
- Why it matters: 이 TASK는 actual training을 명시적으로 금지하며 C18은 그 invariant를 증명해야 한다. 서로 모순된 evidence sections 중 한 곳만 신뢰하면 false no-training claim이 가능하다.
- Requirement affected: C18, EC-15, EC-16, EC-19, no-training/procurement boundary.
- Recommended remediation: generation, probe/runtime, scope-safety의 모든 training/model-load/optimizer/provisioning facts를 하나의 material predicate에서 cross-check하고, 모순은 structural validation error 및 blocker로 전파한다.

### HIGH

#### `TASK-P0-007-REV-H01`

- File: `docs/task_history/TASK-P0-007/02_fix.md`, `docs/task_history/TASK-P0-007/README.md`
- Issue: committed `02_fix.md`에 unresolved `<<<<<<<` / `=======` / `>>>>>>>` conflict markers가 있고, 두 artifact/payload hash 쌍을 동시에 주장한다. TASK README도 actual artifact SHA-256 `219d6783...`가 아닌 stale `4f12c666...`를 기록한다.
- Why it matters: EC-19가 요구하는 verifier/evidence/docs/task-history consistency와 auditability를 훼손한다.
- Requirement affected: EC-19 Evidence Integrity, task-history recording policy.
- Recommended remediation: 기존 history를 임의 삭제하지 말고 repository policy에 맞는 corrective history/audit entry로 authoritative hash를 단일화하고 conflict 상태를 명시적으로 해소한다.

### MEDIUM

#### `TASK-P0-007-REV-M02`

- File / Symbol: `scripts/verify_training_resource_readiness.py::_memory` lines 229–247
- Issue: `/proc/meminfo`의 `Path.read_text()`가 timeout-controlled worker 밖에서 실행된다. Injected 0.25 s delay가 약 0.251 s 그대로 caller를 block했고 `timed_out` 정보도 없었다.
- Why it matters: M01의 “all potentially blocking filesystem/resource metadata operations” 및 automatic termination 요구가 완전히 충족되지 않았다.
- Requirement affected: canonical verifier boundedness, `TASK-P0-007-REV-M01` remediation contract.
- Recommended remediation: RAM/resource metadata read도 동일한 bounded worker 또는 bounded subprocess 뒤로 이동하고 delay/termination/conservative C05 propagation test를 추가한다.

### LOW

No LOW findings.

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: FAIL
Contract compliance: FAIL
State / invariant safety: FAIL
Test adequacy: FAIL
Regression safety: PASS
Evidence integrity: FAIL
```

## 6. 검토에서 확인한 핵심 위험

- Check/payload hash consistency는 domain truth를 대신하지 않는다. Resource/budget/fallback identity 사이의 관계까지 검증해야 한다.
- `NOT_VERIFIED` provenance가 summary check의 PASS에 남는 구조는 evidence consumer에게 모순된 신호를 준다.
- No-training invariant는 한 section의 boolean이 아니라 generation/runtime/scope 전체의 일관성으로 증명해야 한다.
- Timeout hardening은 명시된 API 세 개에만 적용하지 말고 canonical resource metadata 경로 전체를 inventory해야 한다.

## 7. Evidence 및 이전 TASK 호환성

- Canonical evidence exists: PASS
- Task identity: PASS
- Canonical blocked decision and blockers: PASS
- Artifact SHA-256: `219d6783f0d9372e2cac2b03a56ddb6252490c143a370d35e04cec7a25f352c4`
- Payload/source/predecessor hash verification: PASS
- P0-005 evidence SHA-256: `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`, unchanged
- P0-006 evidence SHA-256: `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`, unchanged
- P0-006 source SHA-256: `117f7a2ebbc2a79a87fb307675dcdbd3e9a9671265cb727e809eb153a8268364`, unchanged
- P0-006 physical outcome: `DEVICE_IO_BLOCKED`, preserved
- Actual fine-tuning/training or paid-resource provisioning found: none

## 8. 최종 Recommendation

```text
Implementation/evidence acceptance:
REJECT TASK-P0-007

Task-specific outcome:
TRAINING_RESOURCE_BLOCKED

TASK-W1-001 authorized:
false

TASK-P0-004R required:
true
```

`TASK-P0-007`은 validator/evidence-integrity findings를 수정한 뒤 다시 independent review가 필요하다.
