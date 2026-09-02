# TASK-P0-005 작업 이력

## 1. TASK 개요

- TASK: `TASK-P0-005`
- 목표: project-local PyTorch CUDA + LeRobot + SmolVLA software runtime을 구성하고 실제 실행 evidence로 판정한다.
- 구현 범위: `.venv-vla`, `uv`, pinned Python/PyTorch/LeRobot, CUDA tensor, LeRobot import, SmolVLA config discovery, evidence/report/risk.
- 주요 비범위: device/camera/teleoperation, model load/inference/training/evaluation, Dataset V1, service/ROS/Agent integration, budget approval, downstream tasks.
- 관련 문서: `tasks/TASK-P0-005.md`, `docs/architecture/adr/ADR-004-vla-stack.md`, `docs/vla/vla_readiness_v1.md`, `results/phase0/P0-004_vla_readiness.json`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | isolated CUDA runtime, pinned LeRobot 0.4.4, SmolVLA code/config 검증과 machine-readable evidence를 구현했다. | `01_implementation.md` |

## 3. 주요 설계 / 문제 해결 포인트

- NVIDIA driver header, system Toolkit, PyTorch packaged CUDA runtime, actual tensor execution을 분리했다.
- LeRobot upstream `0.6.1`을 자동 적용하지 않고 ADR-004 baseline `0.4.4`를 명시적으로 유지·검증했다.
- ambient ROS `PYTHONPATH`를 evidence process에서 비워 project-local package isolation을 보장했다.
- RTX 2060 6 GB 결과는 runtime/code readiness로 제한하고 model load/inference/fine-tuning fit은 `NOT_VERIFIED`로 남겼다.
- 모든 결과에서 `task_w1_001_authorized=false`, `p0_004r_regate_required=true`를 유지했다.

## 4. 검증 결과

- Runtime verifier: 11 checks PASS, `RUNTIME_READY`.
- Safe rerun: PASS.
- Dependency check: 115 packages compatible.
- Focused regression: 3 PASS.
- Full regression: 53 PASS.
- Evidence: `../../../results/phase0/P0-005_vla_runtime.json`, SHA-256 `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`.
- Independent review: NOT YET ACCEPTED.

## 5. 최종 상태

`IMPLEMENTED / REVIEW PENDING`

Implementation은 `COMPLETE`지만 independent Read-only Review의 `ACCEPT`는 아직 없다.

## 6. 포트폴리오 요약

P0-004에서 막혔던 VLA software runtime을 system Python 변경 없이 `.venv-vla`에 격리했다. Driver의 CUDA 표기를 capability claim으로 사용하지 않고, pinned PyTorch `2.10.0+cu130`으로 실제 GPU tensor를 실행해 runtime을 증명했다. Repository baseline LeRobot `0.4.4`를 명시적으로 유지하면서 dataset/SmolVLA module과 non-training config를 검증했다. 동시에 6 GB VRAM의 model load와 training fit은 측정하지 않았음을 구조화 evidence에 남겨 과장을 차단했다. 전체 readiness와 `TASK-W1-001` 승인 권한은 후속 P0-004R에 보존했다.
