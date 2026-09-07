# Read-only Review — TASK-P0-007

## 1. 검토 정보

- TASK: `TASK-P0-007`
- 작업 유형: Independent Read-only Re-review
- 실행 순번: `05`
- 검토 대상 Git HEAD: `fb41269a3438dd344a87ab591a8c679bf4b1842b`
- 검토 시작 시 Git 상태: clean
- 구현/source/evidence 변경: 없음
- Focused tests: 49 PASS, 0 FAIL
- Full regression: 125 PASS, 0 FAIL

## 2. 검토 결론

- Recommendation: `REJECT TASK-P0-007`
- BLOCKER: 2
- HIGH: 0
- MEDIUM: 1
- LOW: 0

Canonical resource outcome 자체는 정확하다.

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

Reject 사유는 BLOCKED 결과가 아니라, 다른 입력으로 구성한 rehashed READY artifact에 대한 material relationship validation과 verifier boundedness가 아직 불완전하기 때문이다.

## 3. Requirement Traceability

| Requirement | Implementation | Test / independent reconstruction | Evidence | Status |
|---|---|---|---|---|
| P0-005/P0-006 및 `DEVICE_IO_BLOCKED` 보존 | predecessor fixed hash binding / C01 | canonical validator + direct SHA-256 | accepted hashes 일치 | PASS |
| Local measurement와 6 GiB false-fit 방지 | `_nvidia`, `_torch_probe`, `_local_training_verified` | unsupported/local-mode tests | `TRAINING_NOT_VERIFIED` | PASS |
| Mode별 concrete primary compute | `_execution_mode_valid`, `_primary_resource_valid` | role/identity tests + 1-byte VRAM reconstruction | canonical은 blocked | FAIL — positive VRAM만으로 compute sufficiency 통과 |
| Storage material consistency | `_storage_valid` | storage tests + component/required mismatch reconstruction | canonical `STORAGE_NOT_VERIFIED` | FAIL — required bytes가 components보다 작아도 READY |
| Budget policy/feasibility | `_numeric_budget_valid`, `_budget_material` | arithmetic tests + tiny prepaid quota reconstruction | canonical `UNRESOLVED` | FAIL — prepaid sufficiency가 required usage와 비교되지 않음 |
| Fallback material/policy | `_fallback_valid` | null/same-resource tests + CPU-only/no-capacity reconstruction | canonical `NOT_VERIFIED` | FAIL — capacity와 budget applicability 없음 |
| No actual training | C18 + structural validation | true-flag tests + missing runtime flag reconstruction | canonical flags false | FAIL — missing runtime training fields default to false |
| Mandatory check/blocker/decision projection | `_checks_from_material`, `decide_readiness`, `_blockers` | demotion/manipulation tests | canonical blockers 일치 | PASS |
| Bounded verifier | `_run`, `_bounded_filesystem_metadata` | delayed disk/path/meminfo tests + delayed read/which reconstruction | canonical timeout metadata | FAIL — `_json`, `_sha256`, `shutil.which` unbounded |
| No training/procurement/scope leakage | implementation diff/static inspection | full regression and Git scope | no prohibited artifacts/actions | PASS |
| Final decision/authorization consistency | C20 / validator | canonical validation | BLOCKED, W1 false, P0-004R true | PASS |

## 4. 주요 Findings

### BLOCKER

#### `TASK-P0-007-REV-B04`

- File / Symbol: `scripts/verify_training_resource_readiness.py::_primary_resource_valid`, `_storage_valid`, `_budget_material`, `_fallback_valid`
- Issue: READY를 구성하는 compute/storage/prepaid/fallback 값 사이의 최소 물질적 관계를 독립 검증하지 않는다.
- Independent rehashed reproductions (`verify_bound_files=true`):
  - dataset 70 GB + checkpoint 70 GB, available 80 GB인데 `required_capacity_bytes=10 MB`로 두면 `TRAINING_RESOURCE_READY`, errors `[]`.
  - remote primary VRAM을 `1` byte로 두어도 READY, errors `[]`.
  - fallback을 `CPU-only fallback`으로 표시하고 VRAM/capacity 및 applicable budget evidence를 전부 생략해도 READY, errors `[]`.
  - prepaid quota를 `1e-300 bytes`로 두고 required usage/duration과 비교하지 않아도 `WITHIN_POLICY`, READY, errors `[]`.
- Why it matters: C09/C11/C14/C15가 credible compute, storage fit, budget feasibility, usable fallback을 증명하지 못한다. 서로 일관된 checks/blockers/decision/payload hash를 다시 만들면 unsupported READY가 가능하다.
- Required remediation: primary에는 selected workload/config의 required compute/VRAM과 available capacity의 비교를 추가한다. Storage required bytes를 known dataset/checkpoint/cache/temp components와 TASK-defined formula로 재계산한다. Prepaid quota는 evidenced required usage와 단위가 일치하고 충분한지 비교한다. Fallback에도 primary와 동등한 compute/runtime/storage 이동 및 applicable budget material을 요구한다.

#### `TASK-P0-007-REV-B05`

- File / Symbol: `scripts/verify_training_resource_readiness.py::_material_predicates` lines 1189–1195, `validate_evidence` lines 1654–1661
- Issue: `torch_cuda.training_executed`와 `optimizer_updates_executed`가 없으면 `.get(..., False)`로 안전한 false로 승격된다.
- Independent reproduction: valid READY artifact에서 두 runtime fields를 삭제하고 checks/blockers/decision/payload를 재생성하면 READY, validation errors `[]` (`verify_bound_files=true`).
- Why it matters: C18의 no-training 증명에 필요한 runtime facts가 absent여도 PASS가 되어 fail-closed 원칙을 위반한다.
- Required remediation: READY/C18 PASS에서 필요한 no-training fields의 명시적 `is False`를 요구하고, canonical probe output에도 모든 required fields를 항상 기록한다. Missing/null은 blocker와 structural error로 전파한다.

### HIGH

No HIGH findings. `04_fix.md`가 immutable legacy `02_fix.md`를 명시적으로 supersede하고 단일 current evidence hash를 기록하므로 이전 H01은 audit policy에 맞게 해소됐다.

### MEDIUM

#### `TASK-P0-007-REV-M03`

- File / Symbol: `scripts/verify_training_resource_readiness.py::_json`, `_sha256`, `_nvidia`
- Issue: canonical verifier가 predecessor/evidence/source read/hash와 executable discovery를 timeout boundary 밖에서 수행한다.
- Independent reproduction: 0.25 s delay injection 시 `_json` 0.251 s, `_sha256` 0.251 s, `shutil.which` 경로 약 0.29 s 동안 그대로 block하며 timeout signal이 없다.
- Why it matters: M01의 모든 potentially blocking filesystem/resource metadata operation bounded 요구가 완결되지 않았다.
- Required remediation: read/hash/executable discovery를 terminate 가능한 bounded worker/subprocess로 이동하고 timeout 시 `NOT_VERIFIED` 및 aggregate blocker/error로 보수적으로 전파하는 지연 회귀를 추가한다.

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

## 6. Evidence 및 선행 TASK 호환성

- Canonical validator: expected exit `2`, `TRAINING_RESOURCE_BLOCKED`
- P0-007 artifact SHA-256: `eda1a2549d038f5ccc3604bec00632def122f9676ad8636b1a0bbeff8a1d41b8`
- P0-007 payload SHA-256: `07aeec9a4ac444ebcf618f89c9a02a681b980791601c35618544bbc56ac75ad8`
- Canonical unresolved blockers: `C08,C09,C10,C11,C12,C14,C15`
- P0-005 evidence SHA-256: `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`, unchanged
- P0-006 evidence SHA-256: `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`, unchanged
- P0-006 verifier SHA-256: `117f7a2ebbc2a79a87fb307675dcdbd3e9a9671265cb727e809eb153a8268364`, unchanged
- P0-006 physical outcome: `DEVICE_IO_BLOCKED`, preserved
- Actual training/fine-tuning, Dataset V1, paid provisioning, physical remediation, P0-004R, Week 1 work: none found

## 7. 최종 Recommendation

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

Canonical blocked evidence는 유지 가능하지만, B04/B05/M03을 수정하고 independent re-review가 다시 필요하다.
