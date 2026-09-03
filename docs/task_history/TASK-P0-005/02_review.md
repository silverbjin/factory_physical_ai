# Read-only Review — TASK-P0-005

## 1. 검토 정보

- TASK: `TASK-P0-005`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 일자: 2026-09-03
- 검토 대상: commit `0f73687d688c72c3d9aaf5b10afad8cfa735825a`
- 검토 시점 Git 상태: branch `task/p0-005-vla-runtime`, clean

## 2. 검토 결론

- Recommendation: `ACCEPT`
- BLOCKER: 0
- HIGH: 0
- MEDIUM: 1
- LOW: 1

Canonical evidence와 `/tmp`에 생성한 독립 재실행 결과 모두 11개 runtime check, 실제 CUDA tensor 계산, LeRobot/SmolVLA import/config discovery, dependency consistency, authorization invariant를 통과했다. 아래 MEDIUM/LOW finding은 현재 측정 결과를 무효화하지 않으며 P0-006/P0-007 진행을 막지 않지만, P0-004R에서 verifier를 재사용하기 전 보강하는 것이 권장된다.

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| EC-01 Repository context | expected worktree/branch 및 pre-change 상태 기록 | Git branch/status/log 독립 확인 | `git` | PASS |
| EC-02 Isolation | `.venv-vla`, `uv`, system-site 비활성화, `.gitignore` | `pyvenv.cfg`, prefix/base-prefix, system import probe | `environment`, `uv` | PASS |
| EC-03 Python decision | CPython 3.12.3 선택과 대안/근거 기록 | installed metadata와 interpreter 독립 확인 | `python_decision` | PASS |
| EC-04 Dependency decision | LeRobot 0.4.4 baseline 유지, PyTorch/torchvision direct pin | installed metadata와 `uv pip check` | `lerobot_version_decision`, package snapshot | PASS |
| EC-05 NVIDIA facts | WSL, `/dev/dxg`, GPU/driver/CUDA header/VRAM/process 측정 | host-access verifier 재실행 | `host`, `nvidia` | PASS |
| EC-06 CUDA distinction | driver, Toolkit, PyTorch runtime, execution 분리 | JSON invariant 및 verifier 재실행 | `nvidia`, `cuda_toolkit`, `torch`, `cuda_tensor_test` | PASS |
| EC-07 PyTorch CUDA | `torch 2.10.0+cu130`, CUDA 13.0, device/capability/memory | host-access verifier 재실행 | `torch` | PASS |
| EC-08 Tensor execution | synchronized 2x2 CUDA matmul 및 CPU numerical assertion | actual `[[19,22],[43,50]]` 독립 재확인 | `cuda_tensor_test` | PASS |
| EC-09 LeRobot imports | 0.4.4 및 6개 module 독립 import | verifier 재실행, `uv pip check` | `lerobot` | PASS |
| EC-10 SmolVLA discovery | policy/model/config/processor와 non-training config | verifier 재실행 | `smolvla` | PASS |
| EC-11 6 GB classification | model load/inference/training 미실행, fit `NOT_VERIFIED` | JSON invariant 검증 | `gpu_capability_classification` | PASS |
| EC-12 Required outputs | report, JSON, verifier, risk plan | 파일 존재/상호 일치 검토 | 4개 required artifact | PASS |
| EC-13 Evidence integrity | provenance, bounded diagnostics, safety flags, package snapshot | SHA-256와 canonical/rerun 핵심 invariant 비교 | SHA-256 `aafe0273...46aae` | PASS |
| EC-14 Safe verifier | timeout, bounded output, atomic write, blocking exit code | 정상 재실행 exit 0; invalid `PYTHONPATH` exit 2 | `/tmp` review evidence | PASS |
| EC-15 Scope control | 설치/runtime 검증만 수행 | commit changed-file 및 forbidden-operation inspection | safety/deferred fields | PASS |
| EC-16 Validation | syntax/JSON/dependency/regression/whitespace | 53 tests PASS, AST/JSON PASS, `uv pip check` PASS | implementation claims independently verified | PASS |
| EC-17 Single decision | allowed enum 기반 결정 | ready/blocked/conditional decision scenarios 확인 | `runtime_decision=RUNTIME_READY` | PASS |
| EC-18 Authorization boundary | W1 미승인, P0-004R 필수 | report/JSON/risk plan 대조 | `false` / `true` invariant | PASS |

## 4. 주요 Findings

### BLOCKER

없음.

### HIGH

없음.

### MEDIUM

- **ID:** `TASK-P0-005-REV-M01`
- **File / Symbol:** `scripts/verify_vla_runtime.py::_nvidia`
- **Issue:** NVIDIA aggregate `PASS` 조건이 full/query command와 GPU name만 확인한다. NVIDIA-SMI header parsing이 실패하거나 compute-process query가 실패해도 `nvidia.status`는 `PASS`가 될 수 있다.
- **Why it matters:** 향후 P0-004R 재실행에서 driver-reported CUDA 또는 process-state가 누락됐는데도 C6가 PASS가 되는 내부 불일치가 생길 수 있다.
- **Requirement / Contract affected:** IR-08, Validation Plan required check 4, Evidence Rule 12, EC-05/EC-14.
- **Evidence:** 독립 mock scenario에서 header fields가 `None`, process query return code가 1인데도 `nvidia.status = PASS`를 재현했다. 현재 canonical/독립 host run에서는 모든 값과 process query가 정상 측정되므로 현재 `RUNTIME_READY` claim에는 영향이 없다.
- **Recommended remediation:** C6 PASS에 parsed header 필수 필드, GPU driver/VRAM 필드, compute-process query 성공을 포함하고 partial diagnostic failure regression test를 추가한다. P0-004R에서 verifier를 재사용하기 전에 처리하는 것이 권장된다.

### LOW

- **ID:** `TASK-P0-005-REV-L01`
- **File / Symbol:** `scripts/verify_vla_runtime.py::collect_evidence`, `input_observations.evidence_kind`
- **Issue:** 사용자 제공 input observation을 `INFERRED`로 표시한다. 별도 `classification`은 정확히 input임을 밝히지만, input과 engineering inference의 taxonomy가 한 필드에서 섞인다.
- **Why it matters:** 자동 evidence consumer가 `INFERRED`를 계산/판단 결과로 오해할 수 있다.
- **Requirement / Contract affected:** Evidence Rules 1, 2, 11.
- **Evidence:** canonical JSON의 `input_observations.evidence_kind = INFERRED`와 `classification = USER_SUPPLIED_INPUT_NOT_MEASURED_BY_P0_005_UNTIL_RECHECK`.
- **Recommended remediation:** input provenance를 별도 `source_kind`/`observation_role`로 표현하고 `evidence_kind`는 measured recheck와 혼동되지 않도록 명시한다.

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: PASS
Contract compliance: PASS
State / invariant safety: PASS
Test adequacy: PASS
Regression safety: PASS
Evidence integrity: PASS
```

## 6. 검토에서 확인한 핵심 위험

- `RUNTIME_READY`는 실제 CUDA runtime과 installed SmolVLA code surface만 의미하며 6 GB에서 model load/inference/training 가능함을 뜻하지 않는다.
- LeRobot 0.4.4 유지 판단은 명시적이고 재현 가능하지만, upstream migration은 ADR-004/P0-004R 검토 없이는 수행하면 안 된다.
- NVIDIA partial diagnostic failure가 aggregate PASS로 남을 수 있으므로 최종 re-gate 전 fail-closed 조건을 강화하는 것이 바람직하다.
- manipulator/camera/teleoperation/budget blocker는 P0-006/P0-007에 남아 있고 `TASK-W1-001`은 계속 금지된다.

## 7. 최종 Recommendation

`ACCEPT TASK-P0-005`

현재 runtime evidence는 독립 재실행으로 재현됐고 frozen architecture/scope/authorization boundary를 보존한다. MEDIUM 1건과 LOW 1건은 명시적으로 defer 가능하며 P0-006/P0-007 진행을 위험하게 만들지 않는다.
