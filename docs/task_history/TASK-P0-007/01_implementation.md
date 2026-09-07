# Implementation — TASK-P0-007

## 1. 작업 정보

- TASK: `TASK-P0-007`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: 2026-09-04
- 시작 시 Repository 상태: clean
- 선행 조건: authoritative `tasks/TASK-P0-007.md`에 따라 `TASK-P0-005 = ACCEPTED`, `TASK-P0-006 = ACCEPTED`, P0-006 physical outcome `DEVICE_IO_BLOCKED`
- 선행 Evidence SHA-256:
  - `results/phase0/P0-005_vla_runtime.json`: `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae`
  - `results/phase0/P0-006_robot_io_readiness.json`: `486d76218ea326b279f9780320d081e7435a6a781194c9a6c4efa4a4bef31506`

## 2. 작업 목적

향후 SmolVLA fine-tuning을 실행하지 않은 상태에서 local compute, storage,
training execution path, budget policy, fallback, reproduction readiness를
측정·분류하는 fail-closed verifier를 구현했다. 구현 완료와 실제
training-resource outcome을 분리해, 외부 resource/budget evidence가 없는
현재 환경을 `TRAINING_RESOURCE_BLOCKED`로 정직하게 판정했다.

## 3. 구현 범위

### 구현한 내용

- bounded local GPU/VRAM, PyTorch CUDA metadata, host RAM, filesystem, VLA environment footprint 측정
- P0-005/P0-006 accepted evidence hash binding과 P0-006 `DEVICE_IO_BLOCKED` 보존
- `TRAINING_NOT_VERIFIED`, `UNRESOLVED`, `UNRESOLVED` budget, `NOT_VERIFIED` feasibility/fallback의 canonical fail-closed 판정
- C01-C20 exact identity/order/mandatory/status/provenance 및 material/check/blocker/decision projection 검증
- atomic JSON evidence 생성 및 content/source/predecessor hash binding
- valid synthetic hybrid READY 경로와 required negative/boundary/tamper regression tests
- human-readable readiness, compute/budget plan, risk register 작성

### 명시적으로 구현하지 않은 내용

- actual SmolVLA fine-tuning, training epoch, optimizer update, hyperparameter search
- Dataset V1, model evaluation, model load/inference
- physical teleoperation, robot/camera remediation, P0-006R
- cloud/paid compute purchase, provisioning, activation, billing/credential/token 생성
- P0-004R, TASK-W1-001 또는 다른 Week 1 task
- Independent Read-only Review

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `scripts/verify_training_resource_readiness.py` | bounded resource measurement, fail-closed aggregation, atomic evidence, invariant validation |
| `tests/test_verify_training_resource_readiness.py` | positive/negative/boundary/tamper/resource-integrity tests 24건 |
| `results/phase0/P0-007_training_resource_readiness.json` | canonical machine-readable measured evidence |
| `docs/vla/training_compute_readiness_v1.md` | local role, resource/storage/budget/fallback/reproduction decision 설명 |
| `plans/vla_training_compute_budget_plan.md` | compute/budget policy, stop condition, future ownership 계획 |
| `plans/vla_training_resource_risks.md` | `RESOLVED`/`DEFERRED`/`BLOCKING`/`OUT_OF_SCOPE` risk register |
| `docs/task_history/TASK-P0-007/01_implementation.md` | 현재 implementation 감사 기록 |
| `docs/task_history/TASK-P0-007/README.md` | TASK별 workflow 요약 |
| `docs/task_history/README.md` | global TASK history index 갱신 |

## 5. 주요 구현 내용

Canonical verifier는 accepted P0-005 environment에서 PyTorch/torchvision과
CUDA device metadata만 bounded subprocess로 확인한다. SmolVLA weights,
dataset, optimizer, training tensor를 만들지 않는다. GPU identity와 free
VRAM, CUDA/import success는 local training proof로 승격되지 않으며
`TRAINING_VERIFIED` claim은 P0-007 scope에서 항상 거부된다.

Canonical resource plan은 다음과 같다.

```text
Local training classification: TRAINING_NOT_VERIFIED
Training execution mode: UNRESOLVED
Primary compute path: UNRESOLVED
Storage readiness: STORAGE_NOT_VERIFIED
Budget policy: UNRESOLVED
Budget feasibility: NOT_VERIFIED
Fallback compute: NOT_VERIFIED
Training-resource outcome: TRAINING_RESOURCE_BLOCKED
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

Storage path는 계획만 기록했고 Dataset V1/checkpoint/cache를 만들지 않았다.
Filesystem free capacity가 충분해 보여도 dataset/model/checkpoint/temp size가
`NOT_VERIFIED`이므로 storage fit을 주장하지 않았다. 비용 입력이 없으므로
가격/시간/비용 계산도 수행하지 않았다.

## 6. 주요 설계 판단

- C01-C20은 모두 producer와 validator에서 `mandatory=true`로 고정하며 caller가 demotion할 수 없다.
- READY 판단은 check field만 신뢰하지 않고 material facts에서 checks를 재생성하여 비교한다.
- `unresolved_blockers`는 mandatory non-`PASS` checks의 exact projection이다.
- `TRAINING_VERIFIED`는 caller-controlled `available=true` 같은 값으로 만들 수 없고, 이 readiness-only task에서는 unsupported claim으로 거부된다.
- synthetic READY는 test fixture에만 존재하며 canonical measured evidence나 portfolio training result가 아니다.
- available fallback GPU가 없으므로 documented stop/escalation rule을 fallback resource로 오인하지 않는다.
- P0-005 direct dependency baseline을 그대로 기록하고 install/upgrade를 수행하지 않는다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Canonical verifier | `python3 -B scripts/verify_training_resource_readiness.py --output results/phase0/P0-007_training_resource_readiness.json` | PASS; expected exit `2`, `TRAINING_RESOURCE_BLOCKED` |
| Canonical invariant validation | `python3 -B scripts/verify_training_resource_readiness.py --validate results/phase0/P0-007_training_resource_readiness.json` | PASS; structurally valid blocked artifact, expected exit `2` |
| Safe rerun A/B | canonical verifier to two `/tmp` outputs + semantic comparison | PASS; both exit `2`, decisions/checks/blockers match |
| Focused tests | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 180s python3 -B -m unittest tests.test_verify_training_resource_readiness -v` | 24 PASS, 0 FAIL |
| Required tamper tests | six named mandatory-demotion/local-claim/provenance/budget/READY/blocker tests | 6 PASS, 0 FAIL |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 300s python3 -B -m unittest discover -s tests -v` | 100 PASS, 0 FAIL |
| JSON / AST / bound-hash validation | `python3 -m json.tool ...`, AST parse, verifier `--validate` | PASS |
| `git diff --check` | `git diff --check` | PASS |
| P0-005/P0-006 preservation | `sha256sum` accepted evidence and verifier sources | PASS; hashes unchanged |

## 8. Exit Criteria

- EC-01 Correct Context — `PASS`
- EC-02 Runtime Preservation — `PASS`
- EC-03 Local Hardware Measurement — `PASS`
- EC-04 Local Training Classification — `PASS`
- EC-05 No False 6 GB Claim — `PASS`
- EC-06 Execution Mode — `PASS` (`UNRESOLVED`, explicit blocked selection)
- EC-07 Primary Resource — `PASS` (explicitly blocked, no resource invented)
- EC-08 Runtime Compatibility — `PASS` (accepted baseline documented; primary compatibility remains `NOT_VERIFIED`)
- EC-09 Storage Readiness — `PASS` (strategy documented; size-dependent requirements `NOT_VERIFIED`)
- EC-10 Budget Policy — `PASS` (`UNRESOLVED`; no numeric budget invented)
- EC-11 Cost Provenance — `PASS` (calculation not performed because inputs are absent)
- EC-12 Budget Feasibility — `PASS` (`NOT_VERIFIED`)
- EC-13 Fallback — `PASS` (absence explicitly blocking; stop/escalation rule documented)
- EC-14 Reproducibility — `PASS`
- EC-15 No Procurement — `PASS`
- EC-16 No Training — `PASS`
- EC-17 Scope Preservation — `PASS`
- EC-18 Validation — `PASS`
- EC-19 Evidence Integrity — `PASS`
- EC-20 Final Decision — `PASS`

## 9. Evidence

- 경로: `../../../results/phase0/P0-007_training_resource_readiness.json`
- Artifact SHA-256: `510384719264b3b0f66846fcbdd360321abc965a7444b743a822dcc89e2d766d`
- Evidence payload SHA-256: `1e709cf55a589cf1ecdf21815b44381e0200d94141f44338927d8055881e66dc`
- 상태: structurally valid `TRAINING_RESOURCE_BLOCKED`
- Mandatory blockers: `C08`, `C09`, `C10`, `C12`, `C14`, `C15`
- Generation mode: `PRE_COMMIT_WORKTREE`; source hashes bind the uncommitted implementation content

## 10. 구현 결과

Technical implementation: `COMPLETE`

Resource readiness: `TRAINING_RESOURCE_BLOCKED`

`TASK-P0-007 is complete.`

## 11. 다음 단계

다음 절차는 bare `TASK-P0-007`을 통한 별도 Independent Read-only Review다.
이 implementation은 acceptance를 주장하지 않으며 P0-004R 또는 Week 1을
시작하지 않았다.

