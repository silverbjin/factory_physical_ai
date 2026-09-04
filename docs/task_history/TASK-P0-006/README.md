# TASK-P0-006 작업 이력

## 1. TASK 개요

- TASK: `TASK-P0-006`
- 목표: physical motion 없이 robot/camera/device I/O foundation을 bounded evidence로 판정한다.
- 구현 범위: device enumeration, stable identity/access, safe state/camera probe boundary, control/gripper discovery classification, workspace/abort/teleoperation prerequisites, evidence/docs/risk.
- 주요 비범위: motion/teleoperation, Dataset V1, SmolVLA load/inference/training, ROS/VLA/Agent integration, `TASK-P0-007`, `TASK-P0-004R`, Week 1.
- 관련 문서: `tasks/TASK-P0-006.md`, `docs/architecture/adr/ADR-001-manipulator.md`, `docs/architecture/adr/ADR-005-camera-observation.md`, accepted `TASK-P0-005` evidence.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE / `DEVICE_IO_BLOCKED` | non-motion verifier와 evidence/docs/risk를 구현했고, 실제 target/device 부재를 mandatory blocker로 보존했다. | `01_implementation.md` |
| 02 | Fix | READY FOR INDEPENDENT RE-REVIEW / `DEVICE_IO_BLOCKED` | timeout 밖 state stat, mandatory demotion, queue race, pre-commit provenance finding을 교정했다. | `02_fix.md` |

Fix의 기준이 된 commit `aa813e6` Independent Review는 사용자 지시에 따라 repository에 `02_review.md`를 생성하지 않고 conversation report로만 반환되었다. 따라서 기존 history file의 다음 번호인 `02_fix.md`를 사용했다.

## 3. 주요 설계 / 문제 해결 포인트

- 구현 완료와 physical readiness outcome을 분리했다.
- Device path를 bounded fixed pattern/root로 제한하고 timeout/atomic-write/fail-closed aggregation을 적용했다.
- Operator가 제공한 interface/document reference는 검증 전까지 `DECLARED_INPUT`으로 유지했다.
- Synthetic ready path는 unit test로만 검증했고 canonical evidence에는 실제 host 결과만 기록했다.
- Mandatory check 하나라도 unresolved이면 `DEVICE_IO_READY`가 되지 않는다.
- State metadata/stat/regular-file 판정/read 전체를 하나의 child-process timeout 안에 배치했다.
- Validator는 C01–C18의 exact identity, mandatory/status/provenance 및 exact blocker projection을 fail-closed로 검증한다.
- State/camera worker 결과는 bounded `Queue.get(timeout=...)`로 회수하고 process/queue 자원을 명시적으로 정리한다.
- Pre-commit evidence는 generation mode, base HEAD, dirty state, bound source hashes, payload hash를 함께 기록한다.

## 4. 검증 결과

- Canonical safe rerun: 2회 모두 expected exit `2`, `DEVICE_IO_BLOCKED`.
- Corrective focused tests: 8 PASS, 0 FAIL.
- P0-006 focused tests: 23 PASS, 0 FAIL.
- Full regression: 76 PASS, 0 FAIL.
- Syntax/JSON/whitespace/P0-005 hash/process-leak checks: PASS.
- Evidence: `../../../results/phase0/P0-006_robot_io_readiness.json`, SHA-256 `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`.
- Independent review: previous result `REJECT`; remediation complete; re-review PENDING.

## 5. 현재 상태

```text
Implementation: COMPLETE
Fix: READY FOR INDEPENDENT RE-REVIEW
Review: RE-REVIEW PENDING
Device I/O: DEVICE_IO_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

## 6. 미해결 blocker와 deferred item

- Blocker: selected robot/camera, stable device/access, state/control/gripper path, camera frame/configuration, workspace constraints, abort/E-stop strategy, teleoperation prerequisites.
- Deferred: physical teleoperation (`TASK-W1-002`), Dataset V1 (`TASK-W1-003`), fine-tuning (`TASK-W1-004`), training resource/budget (`TASK-P0-007`), final Phase 0 authorization (`TASK-P0-004R`).

## 7. 포트폴리오 요약

P0-006은 hardware가 없는 환경에서 성공을 꾸미는 대신 non-motion verifier를 완성하고 `DEVICE_IO_BLOCKED`를 재현 가능하게 증명했다. Independent Review에서 state metadata 조회가 timeout 밖에 있고 mandatory flag를 변조할 수 있으며 `Queue.empty()`가 결과 race를 만들 수 있다는 결함이 확인되었다. Fix는 state path 전체를 bounded worker로 옮기고 C01–C18 및 blocker projection을 domain boundary에서 강제했으며, deterministic queue retrieval과 content-bound provenance를 추가했다. 결과적으로 implementation correction은 re-review 준비를 마쳤지만 실제 target/device/safety prerequisite가 해결될 때까지 Week 1은 승인되지 않는다.
