# Implementation — TASK-SIM-C01

## 1. 작업 정보

- TASK: `TASK-SIM-C01`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: `2026-09-12`
- 시작 Branch / HEAD: `task/p0-SIM-` / `360c42ef2c61374788dfa0fdc36088305c309960`
- 시작 Worktree: DIRTY — 사용자가 제공한 미추적 active specification `tasks/TASK-SIM-C01.md`만 존재
- 선행 결과: accepted historical `TASK-SIM-001` decision `SIM_CONTRACT_PROFILE_BLOCKED`

## 2. 작업 목적

`TASK-SIM-001`이 기록한 여섯 executable-contract gap을 frozen topology 변경 없이 해소하기 위해, Simulation Lane v1에만 적용되는 최소 protocol-neutral 실행 계약과 JSON Schema를 정의한다.

## 3. 구현 범위

### 구현한 내용

- `mission.execute`, `navigation.execute`, `vla.execute`, `action_status.get`, `verification.verify`의 요청/결과 계약을 정의했다.
- mission/action lifecycle, timeout-to-`unknown`, immutable reconciliation evidence, bounded retry guard를 규범화했다.
- `unknown -> succeeded` 직접 전이를 금지하고 machine-testable transition/reconciliation/retry record를 제공했다.
- operational result와 verification verdict를 분리하고 `sim-exact-match-v1`의 deterministic `pass|fail|uncertain` 규칙을 정의했다.
- `SIM_FIXTURE_SET_V1` observation reference/manifest를 Dataset V1 및 physical camera와 분리했다.
- project-wide `contract_plan.md`의 planning-only 상태를 유지하면서 Simulation Lane v1 범위에만 executable delegation을 추가했다.
- 미래 `TASK-SIM-001` 재평가가 현재 계약/스키마와 독립 C01 acceptance binding을 직접 검증하도록 specification을 갱신했다.

### 명시적으로 구현하지 않은 내용

- `TASK-SIM-002`, smoke runtime, simulator, fixture runtime 또는 production adapter
- ROS/Nav2/MoveIt/`ros2_control` binding 또는 direct actuator public port
- physical robot/camera/gripper/teleoperation 실행
- Dataset V1, training/fine-tuning 또는 candidate hardware freeze
- independent review 또는 `results/reviews/SIM-C01_acceptance.json`

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `docs/contracts/simulation_execution_contract_v1.md` | Simulation Lane v1 전용 normative executable semantics |
| `docs/contracts/schemas/simulation_execution_contract_v1.schema.json` | closed public request/result, lifecycle, reconciliation, retry, fixture schema |
| `docs/contracts/contract_plan.md` | planning-only 상태를 유지하는 bounded delegation |
| `tasks/TASK-SIM-001.md` | 새 authority 및 immutable/independent acceptance binding 요구 |
| `tests/test_simulation_execution_contract.py` | positive, negative, lifecycle, reconciliation, retry, determinism 계약 검증 |
| `results/simulation/SIM-C01_contract_resolution.json` | C01–C40, source hashes, gap disposition, authorization snapshot |
| `docs/task_history/TASK-SIM-C01/01_implementation.md` | 이번 implementation 기록 |
| `docs/task_history/TASK-SIM-C01/README.md` | TASK workflow 요약 |
| `docs/task_history/README.md` | global TASK history index 갱신 |

## 5. 주요 설계 판단

- operation identifier는 transport나 Python API가 아닌 protocol-neutral logical operation으로 고정했다.
- Agent는 semantic proposal만 제공하고 Deterministic Mission Executor가 authorization/lifecycle/business recovery를 소유한다.
- Nav2는 local navigation execution/recovery, MoveIt은 manipulation planning/safety, `ros2_control`은 controller/hardware interface ownership을 유지한다.
- VLA는 approved bounded semantic skill만 소유하며 raw actuator/controller 명령을 받지 않는다.
- timeout은 성공이나 실패가 아닌 `unknown`이며, matching `action_status.get` evidence로 `reconciled`된 이후에만 후속 성공 처리 또는 retry가 가능하다.
- C01 구현 완료와 task-specific decision, independent acceptance, SIM-001 재평가 authorization, SIM-002 authorization을 분리했다.

## 6. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused contract tests | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_simulation_execution_contract.py -q -p no:cacheprovider` | `22 passed` — PASS |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` | `154 passed` — PASS |
| Evidence/schema/source/payload | inline read-only Python validator | JSON Schema meta-validation, current artifact hashes, frozen hashes, exact gaps, C01–C40, canonical payload — PASS |
| Repository whitespace | `git diff --check` plus untracked-file trailing-whitespace scan | PASS |

## 7. Evidence

- 경로: `../../../results/simulation/SIM-C01_contract_resolution.json`
- Evidence SHA-256: `23044f27063dfd3910b098e3fd313eb88e24ab061d986366750676f09ff0561f`
- Payload SHA-256: `4b6565ab289ce7d56f0fa4418ba931a609a001f2cba75c52f2ee0f3dfdac9115`
- Contract SHA-256: `aaa8b8b1a53e460104a5339f10622ec4cb336f3bb0e598991bbd0c1387cde880`
- Schema SHA-256: `25686143b74b0315aa2a0910673c66b74a53d07222ab4898d91676a53b36e975`
- Task-specific decision: `SIM_CONTRACT_GAPS_RESOLVED`

## 8. Frozen Authority 보존

- `ADR-Simulation-Lane-v1`, simulation task mapping, system architecture, ADR-001/002/005/010 해시 불변
- hardware selection status 해시 불변; candidate hardware freeze 없음
- `P0-004R` evidence 해시 불변; historical `NO_GO` 유지
- 기존 `TASK-SIM-001` profile/evidence와 accepted blocked history는 재작성하지 않음
- Week/physical/Dataset/training authorization 변경 없음

## 9. 구현 결과

```text
TASK-SIM-C01 implementation: complete
Task-specific decision: SIM_CONTRACT_GAPS_RESOLVED
Independent acceptance: pending
TASK-SIM-001 re-evaluation authorized: false
TASK-SIM-002 authorized: false
```

## 10. 다음 단계

별도의 READ-ONLY review가 계약, 스키마, 테스트, evidence 및 frozen-source 보존을 검증해야 한다. 이후 별도 recording step이 current hashes와 reviewed commit에 결속된 `SIM-C01_acceptance.json`을 생성하기 전까지 `TASK-SIM-001` 재평가는 authorized되지 않는다.
