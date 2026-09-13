# Implementation — TASK-SIM-001

## 1. 작업 정보

- TASK: `TASK-SIM-001`
- 작업 유형: Implementation re-evaluation
- 실행 순번: `03`
- 일자: `2026-09-13`
- 시작 시 Repository 상태: `716f8d89d298155975b750ce538e506354026cc0`, clean worktree
- 선행 조건: independently accepted `TASK-SIM-C01`, current immutable contract/schema/C01 bindings, frozen Simulation Lane authority, historical `P0-004R = NO_GO`

## 2. 작업 목적

`TASK-SIM-C01`에서 해소되고 독립 수락된 여섯 executable-contract gap을 현재 authoritative source로 재검증하여, `TASK-SIM-002`가 새 public API를 발명하지 않고 bounded deterministic smoke runtime을 구현할 수 있는지 `TASK-SIM-001` profile과 evidence를 재생성하는 작업이다.

## 3. 구현 범위

### 구현한 내용

- `SIM-C01_acceptance.json`의 reviewed commit, evidence payload, contract, schema, contract plan, task specification, review record binding을 재검증했다.
- Mission Executor, Navigation Skill, VLA Skill, Verification 경계를 Simulation Lane v1 한정 `EXECUTABLE_CONTRACT_AVAILABLE`로 분류했다.
- `mission.execute`, `navigation.execute`, `vla.execute`, `action_status.get`, `verification.verify`의 protocol-neutral semantics를 profile했다.
- 여섯 historical gap의 ID와 원문을 보존하고 accepted contract/schema의 해소 위치에 연결했다.
- timeout-to-`unknown`, status lookup, immutable reconciliation evidence, direct `unknown -> succeeded` 금지, bounded retry, deterministic verification을 profile했다.
- 모든 Required Context와 profile을 SHA-256으로 결속하고 C01–C20을 재평가했다.

### 명시적으로 구현하지 않은 내용

- `TASK-SIM-002`, fixtures, smoke runtime, simulator 또는 physical adapter
- Python/ROS/HTTP/gRPC runtime binding 또는 새 public port
- physical robot/camera/gripper/teleoperation/E-stop 동작
- Dataset V1, training/fine-tuning, paid compute 또는 hardware target freeze
- `TASK-W*` authorization 변경, `P0-004R` 변경 또는 `SIM_GO`
- independent review 또는 post-review `SIM-001_acceptance.json`

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `docs/simulation/simulation_contract_profile_v1.md` | accepted C01 authority에 따른 executable boundary/fixture profile과 READY decision 재평가 |
| `results/simulation/SIM-001_contract_profile.json` | current source/profile hashes, gap disposition, C01–C20, authorization snapshot 기록 |
| `docs/task_history/TASK-SIM-001/03_implementation.md` | 이번 re-evaluation Implementation 기록 |
| `docs/task_history/TASK-SIM-001/README.md` | historical blocked 결과를 보존하며 workflow 요약 갱신 |
| `docs/task_history/README.md` | global TASK 상태를 새 review pending 상태로 갱신 |

## 5. 주요 구현 내용

프로젝트 전체 `contract_plan.md`의 planning-only 상태는 그대로 유지했다. 다만 이 문서가 명시적으로 위임하고 `TASK-SIM-C01` review/acceptance가 immutable hash로 결속한 Simulation Lane v1 contract와 closed JSON Schema만 executable authority로 사용했다. 따라서 네 boundary의 분류를 `EXECUTABLE_CONTRACT_AVAILABLE`로 바꾸면서도 physical/native/Week 범위로 authority가 확장되지 않는다.

과거 `SIM_CONTRACT_PROFILE_BLOCKED` profile/evidence hash와 `ACCEPT` review는 삭제하거나 재해석하지 않았다. 새 canonical profile/evidence는 새 hash를 가지므로 과거 review는 현 revision의 acceptance가 아니며, 새로운 independent review와 post-review acceptance record 전까지 `TASK-SIM-002 authorized=false`이다.

## 6. 주요 설계 판단

- logical operation identifier는 transport/runtime API가 아니므로 protocol-neutral contract 이름 그대로 기록했다.
- timeout은 `pending/unknown`이며 `unknown -> succeeded` 직접 전이는 금지했다. 성공은 matching `action_status.get` evidence와 durable reconciliation 뒤에만 처리할 수 있다.
- `SIM_FIXTURE_SET_V1`은 schema-bound synthetic contract fixture이며 Dataset V1과 별개다.
- `SIM_CONTRACT_PROFILE_READY`는 contract sufficiency만 뜻하며 implementation completion, independent acceptance, downstream authorization, `SIM_GO`와 분리했다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused contract tests | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_simulation_execution_contract.py -q -p no:cacheprovider` | `26 passed` — PASS |
| Evidence/profile/source/authorization validator | inline read-only Python validator | Required Context/hash/payload/C01 acceptance/P0 authorization/schema semantics — PASS |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` | `158 passed` — PASS |
| Repository whitespace | `git diff --check` | PASS |

## 8. Exit Criteria

- mandatory profile/evidence artifact 존재 — PASS
- exact Required Context 13개 binding — PASS
- delegated semantic contract와 JSON Schema 직접 검증 — PASS
- 네 boundary executable classification — PASS
- 여섯 gap 해소 및 historical wording 보존 — PASS
- C01–C20 평가 — PASS
- physical/dataset/training/Week boundary 보존 — PASS
- prior blocked evidence/review recoverability 보존 — PASS
- downstream implementation 미착수 — PASS

## 9. Evidence

- 경로: `../../../results/simulation/SIM-001_contract_profile.json`
- Evidence SHA-256: `c7ea4be8b6e34bc5eff3ef15c728ac76cb34d280d5def3a73fdabb52c6ad642d`
- Payload SHA-256: `2d00ad019c33a53e4b3bf83cc0217666ca5efb89196a386645ff36c4c6a58b4e`
- Profile SHA-256: `24e9dbdbccb34e4799a43a7a3bbef5f5ebbb84d211aa9506cdae567c238645e1`
- 상태: `SIM_CONTRACT_PROFILE_READY`

## 10. 구현 결과

`TASK-SIM-001 is complete.`

```text
Task-specific decision: SIM_CONTRACT_PROFILE_READY
Independent acceptance: PENDING
TASK-SIM-002 authorized: false
```

## 11. 다음 단계

새 canonical profile/evidence에 대한 독립 READ-ONLY review가 필요하다. Review가 `ACCEPT`하더라도 별도 post-review acceptance artifact가 current profile/evidence hashes에 결속되기 전까지 `TASK-SIM-002`는 authorized되지 않는다.
