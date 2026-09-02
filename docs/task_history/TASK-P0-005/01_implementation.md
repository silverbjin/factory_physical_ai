# Implementation — TASK-P0-005

## 1. 작업 정보

- TASK: `TASK-P0-005`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: 2026-09-02
- 시작 시 Repository 상태: branch `task/p0-005-vla-runtime`, commit `3c9ed194048a48ada708e9c882ead2925fe78424`, clean
- 선행 조건: `TASK-P0-004 = NO_GO`; software/runtime blocker remediation authorized

## 2. 작업 목적

P0-004에서 차단된 CUDA/LeRobot/SmolVLA software runtime을 project-local 환경에서 재현 가능하게 구성하고, driver 표기나 package 설치 성공이 아니라 실제 CUDA tensor 실행과 독립 import/config 검증으로 runtime 가능 여부를 판정했다.

최종 P0-005 runtime decision은 `RUNTIME_READY`다. 이 결과는 software runtime에만 적용되며 `TASK-W1-001`을 승인하지 않는다. 전체 readiness 결정에는 P0-006/P0-007 이후 `TASK-P0-004R` re-gate가 필요하다.

## 3. 구현 범위

### 구현한 내용

- user-scoped standalone `uv 0.12.9` 설치와 `.venv-vla` 생성
- CPython 3.12.3 선택 및 system Python 비변경 검증
- `torch==2.10.0`, `torchvision==0.25.0`, `lerobot[smolvla]==0.4.4` direct pin 설치
- `cu130` PyTorch runtime, RTX 2060 Max-Q, synchronized CUDA tensor 계산 검증
- LeRobot dataset/SmolVLA policy/model/config/processor import와 non-training config 생성 검증
- atomic JSON evidence writer, bounded command timeout/output, fail-closed decision 구현
- human-readable runtime report와 software/non-software risk 분리

### 명시적으로 구현하지 않은 내용

- manipulator/device I/O, camera, physical teleoperation 또는 robot motion
- model weight download/load, inference, fine-tuning, evaluation
- Dataset V1, VLA Skill Server, ROS 2, Agent/factory integration
- training budget approval, TASK-P0-006, TASK-P0-007, TASK-P0-004R, TASK-W1-001
- system Python, CUDA Toolkit, NVIDIA driver, WSL kernel 변경

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `.gitignore` | `.venv-vla/`를 repository 추적에서 제외 |
| `scripts/verify_vla_runtime.py` | host/Python/uv/NVIDIA/PyTorch/LeRobot/SmolVLA를 비파괴적으로 검증하고 evidence를 atomic write |
| `results/phase0/P0-005_vla_runtime.json` | 실제 측정값, version decision, package snapshot, checks, safety/authorization invariant 기록 |
| `docs/vla/vla_runtime_environment_v1.md` | runtime 구성, 버전 판단, 측정 결과, 재현 명령, limitation 문서화 |
| `plans/vla_runtime_risks.md` | 해결된 runtime blocker와 P0-004R까지 남은 위험/owner/trigger 기록 |

## 5. 주요 구현 내용

### 격리와 dependency 결정

`uv 0.12.9`를 `/home/jinho/.local/bin`에 unmanaged/user-scoped binary로 설치해 system Python과 shell profile을 변경하지 않았다. `.venv-vla`는 `/usr/bin/python3.12`를 base로 생성했으며 `include-system-site-packages = false`다. 공식 evidence 실행에서는 기존 ROS workspace의 ambient `PYTHONPATH`를 비워 115개 package snapshot이 `.venv-vla`만 반영하도록 했다.

ADR-004/P0-004 baseline인 LeRobot `0.4.4`를 명시적으로 유지했다. upstream `0.6.1`도 확인했지만, current task에서 최신 버전으로 자동 migration하지 않았다. LeRobot 0.4.4 metadata 범위 안에서 PyTorch `2.10.0+cu130`, torchvision `0.25.0+cu130`, Python 3.12.3을 선택했다.

### CUDA와 SmolVLA 검증

`nvidia-smi`는 NVIDIA-SMI `580.102.01`, driver `581.57`, driver-reported CUDA `13.0`, `NVIDIA GeForce RTX 2060 with Max-Q Design`, 6144 MiB, compute capability 7.5를 측정했다. 별도 PyTorch 검증에서 `torch.version.cuda == "13.0"`, `torch.cuda.is_available() == true`를 확인하고 2×2 matrix multiplication을 `cuda:0`에서 실행·동기화·CPU 복사한 뒤 `[[19,22],[43,50]]`을 검증했다.

LeRobot와 SmolVLA module 6개 import, `uv pip check`, `SmolVLAConfig(device="cuda")`가 모두 PASS했다. model loading/inference/training은 실행하지 않았으므로 6 GB training fit은 `NOT_VERIFIED`로 고정했다.

## 6. 주요 설계 판단

1. `nvidia-smi`의 CUDA header, system Toolkit, PyTorch packaged runtime, tensor execution을 서로 다른 evidence field로 분리했다.
2. current upstream으로 silent upgrade하지 않고 repository baseline을 검증해 ADR 변경 없는 최소 remediation을 선택했다.
3. verifier는 install 기능이 없고 timeout/bounded output/atomic replacement를 사용한다. core check 실패 시 evidence를 남긴 뒤 exit code 2와 `RUNTIME_BLOCKED`로 fail closed한다.
4. 6 GB GPU는 `CUDA_RUNTIME_AND_SMOLVLA_CODE_READY_TRAINING_UNVERIFIED`로만 분류해 model/training capability 과장을 방지했다.
5. restricted sandbox NVML과 host GPU 상태를 구분하고, portfolio evidence는 host GPU access가 있는 실행 경계를 명시했다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Runtime verifier | `PYTHONPATH= .venv-vla/bin/python scripts/verify_vla_runtime.py` (host GPU access) | 11 checks PASS, `RUNTIME_READY` |
| Safe rerun | `PYTHONPATH= .venv-vla/bin/python scripts/verify_vla_runtime.py --output /tmp/P0-005_vla_runtime_rerun.json` | PASS, same decision/invariants |
| Dependency consistency | `uv pip check --python .venv-vla/bin/python` | 115 packages compatible |
| System Python isolation | `/usr/bin/python3` import-spec check for `torch`, `lerobot` | both absent, PASS |
| Focused regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_verify_vla_readiness -v` | 3 PASS, 0 FAIL |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 53 PASS, 0 FAIL |
| Syntax | `PYTHONPATH= .venv-vla/bin/python -m compileall -q scripts/verify_vla_runtime.py` | PASS |
| JSON parse/invariants | `.venv-vla/bin/python -m json.tool ...` + required-field/assertion check | PASS |
| Whitespace | `git diff --check` + untracked-file trailing-whitespace search | PASS |

## 8. Exit Criteria

- EC-01 Repository context — PASS
- EC-02 Isolation — PASS
- EC-03 Python decision — PASS
- EC-04 Dependency decision — PASS
- EC-05 NVIDIA facts — PASS
- EC-06 CUDA distinction — PASS
- EC-07 PyTorch CUDA — PASS
- EC-08 Tensor execution — PASS
- EC-09 LeRobot imports — PASS
- EC-10 SmolVLA discovery — PASS
- EC-11 6 GB classification — PASS
- EC-12 Required outputs — PASS
- EC-13 Evidence integrity — PASS
- EC-14 Safe verifier — PASS
- EC-15 Scope control — PASS
- EC-16 Validation — PASS
- EC-17 Single decision — PASS
- EC-18 Authorization boundary — PASS

## 9. Evidence

- 경로: `../../../results/phase0/P0-005_vla_runtime.json`
- SHA-256: `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`
- 상태: `runtime_decision = RUNTIME_READY`, 11 checks PASS, `runtime_blockers = []`
- Authorization: `task_w1_001_authorized = false`, `p0_004r_regate_required = true`

## 10. 구현 결과

`TASK-P0-005 is complete.`

Independent Read-only Review는 아직 수행되지 않았다.

## 11. 다음 단계

다음 권장 절차는 bare `TASK-P0-005` 명령을 통한 independent Read-only Review다. P0-006/P0-007/P0-004R 또는 TASK-W1-001은 시작하지 않았다.
