# Fix — TASK-P0-007

## 1. 수정 정보

- TASK: `TASK-P0-007`
- 작업 유형: Review Finding Fix
- 실행 순번: `06`
- 일자: 2026-09-05
- 기준 Review: `05_review.md` (`REJECT TASK-P0-007`)
- 수정 대상: `TASK-P0-007-REV-B04`, `TASK-P0-007-REV-B05`, `TASK-P0-007-REV-M03`
- `GIT_HISTORY_STATUS`: `NO HISTORY ACTION REQUIRED`

## 2. Finding 처리 결과

| Finding | Severity | 결과 | 교정 내용 |
|---|---|---|---|
| `TASK-P0-007-REV-B04` | `BLOCKER` | `FIXED` | primary/fallback workload VRAM 비교, storage component 합계 재계산, prepaid required usage 비교, fallback storage/budget material 검증을 추가했다. |
| `TASK-P0-007-REV-B05` | `BLOCKER` | `FIXED` | generation/runtime의 training·optimizer·hyperparameter fields를 명시적으로 요구하며 missing/null을 C18 blocker로 처리한다. |
| `TASK-P0-007-REV-M03` | `MEDIUM` | `FIXED` | JSON read, SHA-256 read, executable discovery를 timeout-controlled subprocess/worker로 이동했다. |

## 3. 구현 내용

- READY primary는 `NVIDIA_CUDA_GPU`, concrete workload/config reference, evidenced `required_vram_bytes`와 available `vram_bytes`를 가지며 `available >= required`를 만족해야 한다.
- Storage C11은 다음 exact formula를 독립 재계산한다.

```text
required_capacity_bytes = dataset_size_bytes + checkpoint_size_bytes
                        + model_cache_size_bytes + temporary_space_bytes
```

- `required_capacity_bytes`는 `DERIVED`여야 하며 available capacity보다 클 수 없다.
- `EXISTING_PREPAID_RESOURCE`는 remaining/required quota의 unit과 provenance를 검증하고 `remaining_quota >= required_quota`를 요구한다. Numeric-cost fields와 no-calculation claim의 모순도 거부한다.
- READY fallback은 primary와 다른 CUDA GPU identity, workload VRAM fit, runtime compatibility, storage movement reference, fallback resource에 적용되는 numeric/prepaid budget predicate를 모두 요구한다.
- `_torch_probe`와 generation evidence는 training, optimizer update, hyperparameter search를 모두 명시적으로 false로 기록한다. Validator는 missing field에 false default를 사용하지 않는다.
- `_json`과 `_sha256`는 bounded isolated Python subprocess를 사용하고, `shutil.which`는 terminate/reap 가능한 metadata worker에서 실행한다.
- 실제 training/fine-tuning, model allocation, Dataset V1, procurement, physical remediation, P0-004R 또는 Week 1 작업은 수행하지 않았다.

## 4. 추가/강화한 테스트

- dataset/checkpoint component 합보다 작은 storage aggregate를 rehash해도 C11 BLOCKED
- primary available VRAM이 workload required VRAM보다 작으면 C09/C10 BLOCKED
- fallback compute capacity, storage strategy, nested budget 또는 fallback cost arithmetic이 없거나 불일치하면 C15 BLOCKED
- tiny prepaid quota가 evidenced required usage보다 작으면 C12/C13/C14 BLOCKED; exact boundary는 READY fixture PASS
- runtime no-training fields를 각각 삭제하면 C18 BLOCKED 및 structural validation error
- blocking FIFO를 통한 JSON/hash read timeout과 delayed executable discovery automatic termination
- 직전 review의 다섯 rehashed attack을 `verify_bound_files=true`로 재구성하여 모두 BLOCKED 확인

## 5. 검증 결과

| 검증 | 결과 |
|---|---|
| Corrective B04/B05 focused group | 5 PASS, 0 FAIL |
| Bounded filesystem/resource I/O group | 6 PASS, 0 FAIL |
| P0-007 focused suite | 56 PASS, 0 FAIL |
| Full repository regression | 132 PASS, 0 FAIL |
| Independent rehashed review-attack reconstruction | 5/5 BLOCKED |
| Python AST parse | 28 PASS, 0 FAIL |
| Canonical verifier | expected exit `2`; `TRAINING_RESOURCE_BLOCKED` |
| Safe validator reruns | expected exit `2`, `2`; stable decision/blockers |
| Evidence invariants/source/predecessor binding | PASS |
| `git diff --check` | PASS |
| P0-005 evidence integrity | SHA-256 `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`, byte-identical |
| P0-006 evidence integrity | SHA-256 `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`, byte-identical; `DEVICE_IO_BLOCKED` preserved |

## 6. Evidence

- Path: `../../../results/phase0/P0-007_training_resource_readiness.json`
- Artifact SHA-256: `9f53dcc0de59c6e32f24ef45a9e91fc6a62641d553b93d4b864cc8520fe6a215`
- Payload SHA-256: `128d0b72373c6605e4157bdbefc8746f1e952506d8dea6d9509d2c4909164325`
- Verifier version: `1.3.0`

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

## 7. 수정 결과

Acceptance-blocking implementation findings는 모두 교정됐다. Resource facts 자체는 변경하지 않았으므로 truthful task-specific outcome은 계속 `TRAINING_RESOURCE_BLOCKED`다.

`TASK-P0-007 fixes are ready for independent re-review.`
