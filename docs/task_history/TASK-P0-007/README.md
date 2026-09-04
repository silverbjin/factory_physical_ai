# TASK-P0-007 작업 이력

## 1. TASK 개요

- TASK: `TASK-P0-007`
- 목표: actual training 없이 future SmolVLA compute/storage/budget readiness를 fail-closed evidence로 판정한다.
- 구현 범위: local resource measurement, training role/mode/resource/storage/budget/fallback/reproduction classification, verifier/tests/evidence/docs/risk.
- 주요 비범위: actual training, Dataset V1, physical teleoperation/remediation, procurement, P0-006R, P0-004R, Week 1.
- 관련 문서: `tasks/TASK-P0-007.md`, accepted P0-005/P0-006 evidence, `docs/architecture/adr/ADR-004-vla-stack.md`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE / `TRAINING_RESOURCE_BLOCKED` | bounded verifier와 tamper tests를 구현하고 unresolved compute/budget/fallback을 mandatory blocker로 보존했다. | `01_implementation.md` |
| 02 | Fix | READY FOR INDEPENDENT RE-REVIEW / `TRAINING_RESOURCE_BLOCKED` | mode-specific material validation, cost recomputation, rehashed-tamper resistance, bounded filesystem metadata를 보강했다. | `02_fix.md` |

## 3. 주요 설계 / 문제 해결 포인트

- Implementation completion과 resource-readiness outcome을 분리했다.
- CUDA/import/free-VRAM/config evidence로 `TRAINING_VERIFIED`를 만들 수 없다.
- C01-C20 mandatory identity와 underlying compute/storage/budget/fallback material에서 재계산한 check/blocker/decision projection을 검증한다.
- Payload를 rehash한 coordinated mutation도 concrete resource, allowed provenance/source, exact cost arithmetic, storage와 fallback 조건을 통과하지 못하면 READY가 될 수 없다.
- P0-005/P0-006 accepted artifacts를 exact SHA-256으로 결합하고 수정하지 않았다.
- 가격, training duration, dataset size, budget ceiling, quota, remote availability를 invent하지 않았다.
- External compute와 approved budget이 없으므로 `UNRESOLVED` / `NOT_VERIFIED`를 유지했다.
- Synthetic READY fixture는 verifier invariant unit test이며 measured portfolio evidence가 아니다.

## 4. 검증 결과

- Focused tests: 38 PASS, 0 FAIL.
- Coordinated/rehashed tamper group: 5 PASS, 0 FAIL.
- Cost arithmetic group: 6 PASS, 0 FAIL.
- Delayed filesystem metadata group: 3 PASS, 0 FAIL.
- Full regression: 114 PASS, 0 FAIL.
- Canonical/safe reruns: expected exit `2`, stable `TRAINING_RESOURCE_BLOCKED`.
- JSON/schema/invariant/source/predecessor hash validation: PASS.
- Evidence: `../../../results/phase0/P0-007_training_resource_readiness.json`, SHA-256 `4f12c66666e916d6b91974320d2050a30ee15752cdaa5e21fe7d714035dcaaf9`.
- Independent review: REJECTED once; corrective implementation is ready for independent re-review.

## 5. 현재 상태

```text
Implementation: FIXED / READY FOR INDEPENDENT RE-REVIEW
Review: RE-REVIEW PENDING
Local training classification: TRAINING_NOT_VERIFIED
Training execution mode: UNRESOLVED
Primary compute path: UNRESOLVED
Storage readiness: STORAGE_NOT_VERIFIED
Budget policy: UNRESOLVED
Budget feasibility: NOT_VERIFIED
Fallback compute: NOT_VERIFIED
Resource readiness: TRAINING_RESOURCE_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

## 6. 포트폴리오 요약

P0-007은 CUDA가 동작하는 6 GiB GPU를 곧바로 training-capable로 포장하지
않고, host facts와 model-specific feasibility를 분리했다. Verifier는 모든
mandatory check와 provenance를 material evidence에서 재구성하고, check
demotion·READY manipulation·blocker mismatch를 거부한다. 실제 외부 resource,
budget, fallback이 없는 현재 상태를 `TRAINING_RESOURCE_BLOCKED`로 남겨
비용과 authorization boundary를 보존했다.
