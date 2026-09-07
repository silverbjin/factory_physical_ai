# Fix — TASK-P0-007

## 1. 수정 정보

- TASK: `TASK-P0-007`
- 작업 유형: Review Finding Fix
- 실행 순번: `02`
- 일자: 2026-09-05
- 기준 Review: 최신 Independent Review (`REJECT TASK-P0-007`); 사용자 지시에 따라 review-history 파일은 생성되지 않음
- 수정 대상 Severity: `BLOCKER`, acceptance-blocking `MEDIUM`
- `GIT_HISTORY_STATUS`: `NO HISTORY ACTION REQUIRED`

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-P0-007-REV-B01` | `BLOCKER` | material/check/blocker/decision을 함께 바꾸고 payload를 rehash하면 근거 없는 `TRAINING_RESOURCE_READY`를 만들 수 있음 | `FIXED` |
| `TASK-P0-007-REV-M01` | `MEDIUM` | canonical verifier의 disk/path/environment metadata 조회가 timeout worker 밖에서 실행될 수 있음 | `FIXED` |

## 3. 원인 분석

- 기존 validator는 C01–C20 projection과 payload hash는 검사했지만, mode별 compute identity/VRAM/source, aggregate storage readiness, policy별 budget evidence, 독립 cost 산술, fallback identity를 충분히 재구성하지 않았다. 따라서 공격자가 서로 일관된 것처럼 material/check/blocker/decision 전체를 다시 쓰면 unkeyed payload hash도 함께 갱신할 수 있었다.
- `shutil.disk_usage`, `Path.is_dir`, `Path.is_file`는 Python caller에서 직접 실행되어 filesystem metadata 응답이 지연될 때 verifier timeout이 적용되지 않았다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `scripts/verify_training_resource_readiness.py` | `LOCAL_TRAINING`, `REMOTE_TRAINING`, `HYBRID_TRAINING`별 concrete resource/material predicate를 추가하고 provenance/source, identity/provider/class/VRAM, runtime compatibility를 검증 | `B01` |
| `scripts/verify_training_resource_readiness.py` | `STORAGE_READY`와 capacity/size provenance, artifact movement, retention, temporary-space 전략을 aggregate C11에 결합 | `B01` |
| `scripts/verify_training_resource_readiness.py` | numeric/prepaid/local-only budget mode를 분리 검증하고 finite non-negative 값 및 `unit_price * estimated_training_hours`를 `Decimal`로 독립 재계산 | `B01` |
| `scripts/verify_training_resource_readiness.py` | required fallback의 strategy/resource/provider/class/availability/compatibility/source를 검증하고 blocker list를 material check에서 재생성 | `B01` |
| `scripts/verify_training_resource_readiness.py` | disk usage와 path-kind 조회를 terminate/reap 가능한 bounded child process로 이동하고 timeout 시 `NOT_VERIFIED`로 보수적 전파 | `M01` |
| `tests/test_verify_training_resource_readiness.py` | coordinated/rehashed READY, insufficient hybrid/local claims, null resource, storage, prepaid, fallback, cost, blocker rewrite, delayed metadata regressions 추가 | `B01`, `M01` |
| `results/phase0/P0-007_training_resource_readiness.json` | verifier v1.1로 canonical non-training evidence 재생성 | 전체 |
| `docs/vla/training_compute_readiness_v1.md`, `plans/vla_training_compute_budget_plan.md`, `plans/vla_training_resource_risks.md` | 강화된 READY 조건, C11 blocker, budget/fallback 검증, R10 remediation 근거 반영 | `B01`, `M01` |

## 5. 추가/강화한 회귀 테스트

- coordinated execution-mode/resource/check/blocker/decision manipulation 후 payload를 rehash해도 material projection mismatch와 aggregate mismatch를 거부한다.
- `HYBRID_TRAINING`의 `NOT_VERIFIED` primary evidence, available primary의 null identity/class, `STORAGE_NOT_VERIFIED`, evidence 없는 prepaid policy, null fallback resource를 각각 fail closed 처리한다.
- unit price `100`, estimated hours `100`, claimed cost `1` 및 NaN/infinity/negative/missing 숫자를 거부한다.
- C01–C20을 모두 PASS로 다시 쓰고 blocker를 비워도 underlying material failure로 READY가 되지 않는다.
- delayed `shutil.disk_usage`, `Path.is_dir`, `Path.is_file`가 자동 종료되고 `NOT_VERIFIED`; disk timeout은 C06과 aggregate `TRAINING_RESOURCE_BLOCKED`로 전파된다.
- synthetic fixture는 domain validation용 test fixture일 뿐 `MEASURED` portfolio evidence가 아니며 training을 실행하지 않는다.

## 6. 검증 결과

| 검증 | 결과 |
|---|---|
| Corrective coordinated/rehashed tampering group | 5 PASS, 0 FAIL |
| Cost arithmetic/boundary group | 6 PASS, 0 FAIL |
| Delayed-filesystem timeout group | 3 PASS, 0 FAIL |
| P0-007 focused suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_verify_training_resource_readiness -q` | 38 PASS, 0 FAIL |
| Full regression: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` | 114 PASS, 0 FAIL |
| Canonical verifier / validator | expected exit `2` / `2`; `TRAINING_RESOURCE_BLOCKED` |
| Safe verifier rerun A/B | expected exit `2`, `2`; decisions and blockers identical |
| AST / JSON / evidence invariant / bound-source validation | PASS |
| `git diff --check` | PASS |
| P0-005 evidence integrity | SHA-256 `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`, byte-identical |
| P0-006 evidence integrity | SHA-256 `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`, byte-identical; `DEVICE_IO_BLOCKED` preserved |

## 7. Evidence 갱신

- Evidence: `../../../results/phase0/P0-007_training_resource_readiness.json`
<<<<<<< ours
- Artifact SHA-256: `219d6783f0d9372e2cac2b03a56ddb6252490c143a370d35e04cec7a25f352c4`
- Evidence payload SHA-256: `4fd4bf656955d5993c30260d0c8bac5346fa6665e0b7955425ac61b2195a72b8`
=======
- Artifact SHA-256: `4f12c66666e916d6b91974320d2050a30ee15752cdaa5e21fe7d714035dcaaf9`
- Evidence payload SHA-256: `4fa1862d910b155a0946338e9cd8d7359c8fc7fadb1bac501b4d7af660ba22cc`
>>>>>>> theirs
- Generation mode: `PRE_COMMIT_WORKTREE`
- Local training: `TRAINING_NOT_VERIFIED`
- Execution mode / primary compute: `UNRESOLVED` / `UNRESOLVED`
- Storage: `STORAGE_NOT_VERIFIED`
- Budget policy / feasibility: `UNRESOLVED` / `NOT_VERIFIED`
- Fallback: `NOT_VERIFIED`
- Final resource outcome: `TRAINING_RESOURCE_BLOCKED`
- `TASK-W1-001 authorized: false`
- `TASK-P0-004R required: true`

## 8. 남은 Findings와 범위

Acceptance-blocking implementation findings `B01`과 `M01`은 모두 `FIXED`다. 실제 compute/storage/budget/fallback 입력은 여전히 미확정이므로 resource outcome은 의도대로 `TRAINING_RESOURCE_BLOCKED`다. 이는 구현 수정 실패가 아니다.

Actual training/fine-tuning, Dataset V1, procurement, physical teleoperation, robot/camera remediation, `TASK-P0-007R`, `TASK-P0-006R`, `TASK-P0-004R`, Week 1 및 downstream integration은 시작하지 않았다.

## 9. History Action

`GIT_HISTORY_STATUS: NO HISTORY ACTION REQUIRED`

<<<<<<< ours
기존 Git history를 수정하거나 재작성할 필요가 없다. 작업 중 외부 repository action으로 HEAD가 `b03316a`로 전진했으며, assistant는 commit/stage를 실행하지 않았다. Evidence는 현재 HEAD와 source hashes 및 accepted predecessor hashes를 결합하므로 정상 후속 commit으로 감사 가능하다.
=======
기존 Git history를 수정하거나 재작성할 필요가 없다. 현재 evidence는 pre-commit source hashes와 accepted predecessor hashes를 결합한다.
>>>>>>> theirs

## 10. 수정 결과

Technical corrective status:

`READY FOR INDEPENDENT RE-REVIEW`

Implementation/evidence correction과 resource-readiness outcome은 별개다.

`TASK-P0-007 fixes are ready for independent re-review.`
