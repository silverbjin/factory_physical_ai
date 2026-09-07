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
| 03 | Review | REJECT / `TRAINING_RESOURCE_BLOCKED` | rehashed false-READY bypass, no-training cross-check 누락, unbounded RAM metadata, fix-history conflict를 확인했다. | `03_review.md` |
| 04 | Fix | READY FOR INDEPENDENT RE-REVIEW / `TRAINING_RESOURCE_BLOCKED` | material/provenance 관계, training flag cross-check, bounded RAM probe를 강화하고 02 기록을 새 audit entry로 supersede했다. | `04_fix.md` |
| 05 | Review | REJECT / `TRAINING_RESOURCE_BLOCKED` | compute/storage/prepaid/fallback 관계의 false-READY, missing no-training field, 남은 unbounded filesystem 경로를 확인했다. | `05_review.md` |
| 06 | Fix | READY FOR INDEPENDENT RE-REVIEW / `TRAINING_RESOURCE_BLOCKED` | workload VRAM/storage/prepaid/fallback 관계를 재계산하고 missing no-training 및 remaining unbounded I/O를 fail closed 처리했다. | `06_fix.md` |
| 07 | Review | ACCEPT / `TRAINING_RESOURCE_BLOCKED` | B04/B05/M03 교정을 독립 재구성하고 모든 Acceptance Gate 통과를 확인했다. | `07_review.md` |

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

- Focused tests: 56 PASS, 0 FAIL.
- Latest corrective B04/B05 group: 5 PASS, 0 FAIL.
- Bounded filesystem/resource I/O group: 6 PASS, 0 FAIL.
- Independent rehashed review attacks: 5/5 BLOCKED.
- Full regression: 132 PASS, 0 FAIL.
- Canonical/safe reruns: expected exit `2`, stable `TRAINING_RESOURCE_BLOCKED`.
- JSON/schema/invariant/source/predecessor hash validation: PASS.
- Evidence: `../../../results/phase0/P0-007_training_resource_readiness.json`, SHA-256 `9f53dcc0de59c6e32f24ef45a9e91fc6a62641d553b93d4b864cc8520fe6a215`.
- Evidence payload SHA-256: `128d0b72373c6605e4157bdbefc8746f1e952506d8dea6d9509d2c4909164325`.
- Independent review: 07 re-review `ACCEPT`; implementation/evidence accepted with truthful resource outcome `TRAINING_RESOURCE_BLOCKED`.

## 5. 현재 상태

```text
Implementation: COMPLETE
Review: ACCEPT TASK-P0-007
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

03 independent re-review에서는 canonical BLOCKED 판단 자체는 정확하다고
확인했지만, placeholder/prepaid/fallback/no-training material을 조작한 rehashed
artifact가 READY로 승인되는 우회와 unbounded RAM metadata 경로를 발견했다.
04 fix는 resource identity 간 관계와 field-specific provenance를 domain boundary에서
검증하고, 모든 training flag를 교차 검증하며, RAM metadata도 bounded worker로
이동했다. 과거 02 audit record는 수정하지 않고 04의 단일 hash 기록으로
supersede하여 audit trail을 보존했다.

05 independent re-review에서는 이 보강을 확인했지만, component 합보다 작은
storage requirement, usable capacity가 없는 primary/fallback, required usage와
비교되지 않은 prepaid quota가 rehashed READY를 만드는 추가 관계 우회를
발견했다. Missing runtime no-training fields의 false default와 일부 unbounded
filesystem read/discovery 경로도 남아 있어 추가 교정이 필요하다.

06 fix는 workload requirement와 available capacity를 primary/fallback에 결합하고,
storage 합계 및 prepaid quota sufficiency를 독립 재계산했다. Missing no-training
fields는 더 이상 false로 승격되지 않으며 JSON/hash/executable discovery도
timeout boundary 안에서 실패를 보수적으로 전파한다.

07 independent re-review는 56개 focused test와 132개 full regression을 통과하고,
coordinated/rehashed READY, storage 축소, insufficient prepaid quota, null fallback,
`100 × 100 = 1` 비용 조작, missing no-training field를 독립 재구성해 모두
차단됨을 확인했다. 구현과 evidence는 수용됐지만 실제 compute/storage/budget/
fallback 사실은 바뀌지 않았으므로 resource outcome은 `TRAINING_RESOURCE_BLOCKED`로
유지되고 Week 1은 승인되지 않는다.
