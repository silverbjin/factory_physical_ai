# Fix — TASK-P0-006

## 1. 수정 정보

- TASK: `TASK-P0-006`
- 작업 유형: Review Finding Fix
- 실행 순번: `02`
- 일자: 2026-09-04
- 기준 Review: commit `aa813e6115452cc5b92d370d13fd266120ab384e` Independent Review (`REJECT TASK-P0-006`); 사용자 지시에 따라 당시 `02_review.md`는 생성하지 않음
- 수정 대상 Severity: `HIGH`, acceptance-blocking `MEDIUM`, 사용자 지정 `LOW`
- 시작 시 Repository 상태: clean

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| `TASK-P0-006-REV-H01` | `HIGH` | `_bounded_state_probe`가 timeout worker 밖에서 `path.stat()` 실행 | `FIXED` |
| `TASK-P0-006-REV-M01` | `MEDIUM` | mandatory demotion과 불완전한 evidence validation으로 false `DEVICE_IO_READY` 가능 | `FIXED` |
| `TASK-P0-006-REV-L02` | `LOW` | state/camera worker 결과를 `multiprocessing.Queue.empty()`로 판정 | `FIXED` |
| `TASK-P0-006-REV-L01` | `LOW` | pre-commit evidence와 이후 commit 사이 provenance가 불명확 | `FIXED` |

## 3. 원인 분석

- state probe는 regular-file 안전 확인을 worker 시작 전 수행해, filesystem metadata 조회가 지연되면 caller timeout이 적용되지 않았다.
- aggregate producer가 모든 check를 mandatory로 만들었지만 validator는 외부 evidence에서 `mandatory=false`로 바꾼 check를 거부하지 않았다. 또한 status/provenance/identity/blocker projection을 하나의 domain invariant로 검증하지 않았다.
- `Queue.empty()`는 multiprocessing producer와 consumer 사이 동기화 보장을 제공하지 않아 worker가 완료되어도 결과가 없다고 오판할 수 있었다.
- 기존 evidence는 당시 Git HEAD와 dirty 상태를 기록했지만, uncommitted source content를 이후 commit과 구별해 결합하는 명시적 hash scope가 없었다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|
| `scripts/verify_robot_io_readiness.py` | state metadata/stat/regular-file 판정/open/read 전체를 child process로 이동하고 하나의 timeout을 적용 | `TASK-P0-006-REV-H01` |
| `scripts/verify_robot_io_readiness.py` | C01–C18 exact identity/area/order/uniqueness, `mandatory=true`, allowed status/provenance, exact `unresolved_blockers`, fail-closed READY를 검증 | `TASK-P0-006-REV-M01` |
| `scripts/verify_robot_io_readiness.py` | state/camera 결과를 bounded `Queue.get(timeout=...)`로 회수하고 process/queue를 terminate/reap/close/join | `TASK-P0-006-REV-L02` |
| `scripts/verify_robot_io_readiness.py` | `PRE_COMMIT_WORKTREE`/`COMMITTED_TREE`, generation Git HEAD/dirty state, source SHA-256, verifier SHA-256, evidence payload SHA-256 추가 | `TASK-P0-006-REV-L01` |
| `tests/test_verify_robot_io_readiness.py` | delayed-stat, mandatory demotion, status/provenance, identity/uniqueness, exact blocker projection, completed-worker/cleanup, content tampering regression 추가 | 전체 |
| `results/phase0/P0-006_robot_io_readiness.json` | 변경 verifier로 canonical non-motion evidence 재생성 | 전체 |
| `docs/hardware/robot_camera_io_readiness_v1.md` | timeout/queue cleanup 및 pre-commit content-binding 재현 설명 갱신 | `H01`, `L01`, `L02` |
| `plans/robot_camera_io_risks.md` | probe hang/result race와 provenance ambiguity의 해소 근거 갱신 | `H01`, `L01`, `L02` |

## 5. 추가/강화한 테스트

- `test_delayed_state_stat_is_bounded_and_propagates_to_readiness`: `Path.stat()`을 1초 지연시키고 0.05초 timeout 내 종료, `timed_out=true`, C06 `BLOCKED`, aggregate `DEVICE_IO_BLOCKED`를 확인했다.
- `test_validation_rejects_mandatory_flag_demotion_ready_bypass`: C01 failure를 `mandatory=false`로 숨긴 `DEVICE_IO_READY` evidence를 거부한다.
- `test_validation_rejects_invalid_check_status`: 허용되지 않은 readiness status를 거부한다.
- `test_validation_rejects_invalid_check_and_material_provenance`: check 및 material fact의 허용되지 않은 provenance를 거부한다.
- `test_validation_rejects_duplicate_or_changed_check_identity`: 중복/변경된 C01–C18 identity를 거부한다.
- `test_validation_requires_exact_unresolved_blocker_projection`: mandatory non-PASS check와 다른 blocker 목록을 거부한다.
- `test_completed_state_and_camera_workers_return_diagnostics_and_cleanup`: 완료된 state/camera worker 결과가 안정적으로 회수되고 child process가 남지 않음을 확인한다.
- `test_validation_rejects_content_binding_tampering`: payload 변경 후 stale content hash를 거부한다.

모든 hardware 관련 regression은 temporary regular-file fixture와 fake camera object만 사용했다. Robot/controller/vendor interface를 열거나 motion command를 전송하지 않았다.

## 6. 테스트 결과

| 검증 | 결과 |
|---|---|
| Corrective focused 8 tests | 8 PASS, 0 FAIL |
| P0-006 focused suite: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 90s python3 -B -m unittest tests.test_verify_robot_io_readiness -v` | 23 PASS, 0 FAIL |
| Full regression: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 180s python3 -B -m unittest discover -s tests -v` | 76 PASS, 0 FAIL |
| Safe verifier rerun A/B | expected exit `2`, `2`; semantic result stable; no leaked verifier process |
| Canonical verifier regeneration | expected exit `2`; `DEVICE_IO_BLOCKED` |
| AST / JSON / evidence invariant validation | PASS |
| `git diff --check` | PASS |
| P0-005 evidence integrity | SHA-256 `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`, unchanged |

## 7. Evidence 갱신

- Evidence: `../../../results/phase0/P0-006_robot_io_readiness.json`
- Artifact SHA-256: `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`
- Evidence payload SHA-256: `202b62e7a1cf84cf94dabaedd19c70c02d92923bb38611dc010018c5a9e4c9f2`
- Verifier SHA-256: `117f7a2ebbc2a79a87fb307675dcdbd3e9a9671265cb727e809eb153a8268364`
- Generation mode: `PRE_COMMIT_WORKTREE`
- Git HEAD at generation: `aa813e6115452cc5b92d370d13fd266120ab384e`
- 변경된 claim: Git HEAD는 생성 시 base commit이고, source hashes는 uncommitted remediation content를 결합하며 이후 commit에서 생성되었다고 주장하지 않는다.
- Physical readiness: `DEVICE_IO_BLOCKED`; mandatory non-PASS 15건과 `unresolved_blockers` 15건이 exact match한다.
- `TASK-W1-001 authorized: false`
- `TASK-P0-004R required: true`

## 8. 남은 Findings

Review finding은 모두 `FIXED`다. 실제 target robot/camera, stable identity/access, state/control/gripper path, workspace constraints, abort/E-stop 및 teleoperation prerequisite는 물리 readiness blocker로 남아 있으며 구현 결함과 구분한다.

Deferred item은 physical teleoperation, Dataset V1, fine-tuning, training compute/budget, final `TASK-P0-004R` decision이다. 이 Fix에서 downstream 구현을 시작하지 않았다.

## 9. History Action

`GIT_HISTORY_STATUS: NO HISTORY ACTION REQUIRED`

기존 commit을 수정하거나 재작성할 필요가 없다. 새 evidence가 pre-commit generation을 명시하고 현재 source/content hash로 결합하므로 정상적인 후속 task-focused commit으로 감사 가능하다.

## 10. 수정 결과

Technical corrective status:

`READY FOR INDEPENDENT RE-REVIEW`

Implementation completion과 독립 acceptance는 별개이며, physical readiness outcome도 별개다.

`TASK-P0-006 fixes are ready for independent re-review.`

다음 단계는 bare `TASK-P0-006`을 통한 별도 Independent Read-only Review다.
