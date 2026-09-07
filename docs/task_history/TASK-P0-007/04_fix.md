# Fix — TASK-P0-007

## 1. 수정 정보

- TASK: `TASK-P0-007`
- 작업 유형: Review Finding Fix
- 실행 순번: `04`
- 일자: 2026-09-05
- 기준 Review: `03_review.md` (`REJECT TASK-P0-007`)
- 수정 대상 Severity: `BLOCKER`, `HIGH`, acceptance-blocking `MEDIUM`
- `GIT_HISTORY_STATUS`: `NO HISTORY ACTION REQUIRED`

## 2. 수정 대상 Findings

| Finding ID | Severity | 처리 결과 | 핵심 교정 |
|---|---|---|---|
| `TASK-P0-007-REV-B02` | `BLOCKER` | `FIXED` | placeholder identity, mode role, primary-budget linkage, fallback identity, field별 provenance를 material predicate에서 검증한다. |
| `TASK-P0-007-REV-B03` | `BLOCKER` | `FIXED` | generation/runtime/scope의 training 및 optimizer flag를 C18과 structural validator에서 교차 검증한다. |
| `TASK-P0-007-REV-H01` | `HIGH` | `FIXED` | 변경 금지된 과거 `02_fix.md` 대신 이 기록을 authoritative superseding fix record로 지정하고 단일 evidence hash를 기록한다. |
| `TASK-P0-007-REV-M02` | `MEDIUM` | `FIXED` | `/proc/meminfo` 읽기를 terminate/reap 가능한 timeout worker로 이동하고 보수적 실패 전파를 검증한다. |

## 3. 주요 수정 내용

- `LOCAL_TRAINING`은 exact role pair, `TRAINING_VERIFIED`, authorized model-specific evidence, local capacity, compatible primary, local-only budget이 모두 충족되어야 READY가 된다.
- `REMOTE_TRAINING` / `HYBRID_TRAINING`은 exact local/training role, concrete non-placeholder primary identity/provider/class/VRAM, availability, runtime compatibility, source와 충분한 provenance를 요구한다.
- `APPROVED_NUMERIC_BUDGET_CEILING`은 selected primary와 `applies_to_resource_id`를 결합하고 finite non-negative 입력 및 `unit_price * estimated_training_hours`를 독립 재계산한다. P0-007에서 training duration은 `MEASURED`로 승격할 수 없다.
- `EXISTING_PREPAID_RESOURCE`는 prepaid entitlement가 selected primary와 동일해야 하며 concrete quota/source를 요구한다.
- READY fallback은 primary와 다른 concrete resource identity, availability, compatibility, source를 요구한다. 이 TASK에는 empty fallback을 정당화할 redundancy exception이 없다.
- C08–C15 PASS는 `DERIVED` provenance를 사용하며 어떤 PASS check도 `NOT_VERIFIED`를 사용할 수 없다.
- C01–C20, blocker list, aggregate decision을 재작성하고 payload를 rehash해도 underlying material predicate failure가 READY를 차단한다.
- accepted P0-005/P0-006 evidence와 P0-006 verifier는 수정하지 않았다. P0-006 physical outcome은 `DEVICE_IO_BLOCKED`로 유지된다.

## 4. 추가/강화한 회귀 테스트

- placeholder primary identity 및 alternate placeholder spellings
- HYBRID role split 누락
- primary와 다른 prepaid entitlement
- primary와 동일한 fallback, null fallback, assertion-only no-fallback
- generation/runtime training 또는 optimizer flag 모순
- `PASS` + `NOT_VERIFIED` provenance 및 training-duration `MEASURED` 승격
- zero planned dataset/checkpoint size
- rehashed predecessor fact manipulation
- delayed `/proc/meminfo` read의 automatic termination, C05 및 aggregate BLOCKED 전파

## 5. 검증 결과

| 검증 | 결과 |
|---|---|
| Corrective coordinated/rehashed tampering group | 11 PASS, 0 FAIL |
| Cost arithmetic/provenance group | 7 PASS, 0 FAIL |
| Delayed filesystem/resource metadata group | 4 PASS, 0 FAIL |
| P0-007 focused suite: `python3 -B -m unittest tests.test_verify_training_resource_readiness -v` | 49 PASS, 0 FAIL |
| Full regression: `python3 -B -m unittest discover -s tests -v` | 125 PASS, 0 FAIL |
| Python AST parse | 28 PASS, 0 FAIL |
| Canonical verifier | expected exit `2`; `TRAINING_RESOURCE_BLOCKED` |
| Safe validator reruns | expected exit `2`, `2`; 동일 decision/blocker |
| Evidence invariant/source/predecessor validation | PASS |
| `git diff --check` | PASS |
| P0-005 evidence | SHA-256 `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`, byte-identical |
| P0-006 evidence | SHA-256 `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`, byte-identical; `DEVICE_IO_BLOCKED` preserved |

## 6. Evidence

- Evidence: `../../../results/phase0/P0-007_training_resource_readiness.json`
- Artifact SHA-256: `eda1a2549d038f5ccc3604bec00632def122f9676ad8636b1a0bbeff8a1d41b8`
- Evidence payload SHA-256: `07aeec9a4ac444ebcf618f89c9a02a681b980791601c35618544bbc56ac75ad8`
- Generation mode: `PRE_COMMIT_WORKTREE`
- Local GPU observation: RTX 2060 Max-Q, 6144 MiB, CUDA available (`MEASURED` host metadata only)
- Local training classification: `TRAINING_NOT_VERIFIED`
- Training execution mode: `UNRESOLVED`
- Primary compute path: `UNRESOLVED`
- Storage readiness: `STORAGE_NOT_VERIFIED`
- Budget policy: `UNRESOLVED`
- Budget feasibility: `NOT_VERIFIED`
- Fallback resource: `NOT_VERIFIED`
- Final task-specific outcome: `TRAINING_RESOURCE_BLOCKED`
- `TASK-W1-001 authorized: false`
- `TASK-P0-004R required: true`

## 7. H01 Audit Correction

`02_fix.md`는 이미 생성된 immutable audit record이므로 conflict marker와 복수 hash를 제거하기 위해 과거 기록을 덮어쓰지 않았다. 이 `04_fix.md`가 `02_fix.md`의 evidence/hash 및 fix-completion 주장을 명시적으로 supersede한다. 위 단일 artifact/payload hash 쌍이 현재 corrective implementation의 authoritative value다.

Git commit history rewrite는 필요하지 않다.

`GIT_HISTORY_STATUS: NO HISTORY ACTION REQUIRED`

## 8. 수정 결과

Implementation/evidence correction과 resource readiness는 별개다. Acceptance-blocking findings는 교정되었지만 실제 compute/storage/budget/fallback 입력은 여전히 없으므로 resource outcome은 의도대로 `TRAINING_RESOURCE_BLOCKED`다.

```text
Technical corrective status: READY FOR INDEPENDENT RE-REVIEW
Task-specific outcome: TRAINING_RESOURCE_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

Actual training/fine-tuning, Dataset V1, procurement, physical teleoperation, robot/camera remediation, `TASK-P0-007R`, `TASK-P0-006R`, `TASK-P0-004R`, Week 1 및 downstream integration은 시작하지 않았다.
