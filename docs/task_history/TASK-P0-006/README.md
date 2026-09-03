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

## 3. 주요 설계 / 문제 해결 포인트

- 구현 완료와 physical readiness outcome을 분리했다.
- Device path를 bounded fixed pattern/root로 제한하고 timeout/atomic-write/fail-closed aggregation을 적용했다.
- Operator가 제공한 interface/document reference는 검증 전까지 `DECLARED_INPUT`으로 유지했다.
- Synthetic ready path는 unit test로만 검증했고 canonical evidence에는 실제 host 결과만 기록했다.
- Mandatory check 하나라도 unresolved이면 `DEVICE_IO_READY`가 되지 않는다.

## 4. 검증 결과

- Canonical safe rerun: 2회 모두 expected exit `2`, `DEVICE_IO_BLOCKED`.
- Focused tests: 15 PASS, 0 FAIL.
- Full regression: 68 PASS, 0 FAIL.
- Syntax/JSON/whitespace/P0-005 hash/process-leak checks: PASS.
- Evidence: `../../../results/phase0/P0-006_robot_io_readiness.json`, SHA-256 `84d627dd2b12896e5f94ee27b5617e9dff1c37642a605c6774e7c74f2a1a1749`.
- Independent review: NOT YET ACCEPTED.

## 5. 현재 상태

```text
Implementation: COMPLETE
Review: NOT YET ACCEPTED
Device I/O: DEVICE_IO_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

## 6. 미해결 blocker와 deferred item

- Blocker: selected robot/camera, stable device/access, state/control/gripper path, camera frame/configuration, workspace constraints, abort/E-stop strategy, teleoperation prerequisites.
- Deferred: physical teleoperation (`TASK-W1-002`), Dataset V1 (`TASK-W1-003`), fine-tuning (`TASK-W1-004`), training resource/budget (`TASK-P0-007`), final Phase 0 authorization (`TASK-P0-004R`).

## 7. 포트폴리오 요약

P0-006은 hardware가 없는 환경에서 성공을 꾸미는 대신 non-motion verifier를 완성하고 `DEVICE_IO_BLOCKED`를 재현 가능하게 증명했다. Device enumeration, state snapshot, camera capture를 각각 explicit bound로 격리하고 partial diagnostic 또는 mandatory failure가 aggregate success로 바뀌지 않도록 했다. 특히 operator declaration과 documented evidence를 분리해 provenance 과장을 막았다. 결과적으로 implementation은 complete지만 실제 target/device/safety prerequisite가 해결될 때까지 Week 1은 승인되지 않는다.
