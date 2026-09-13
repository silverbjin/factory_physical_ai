# Implementation — TASK-SIM-002

## 1. 작업 정보

- TASK: `TASK-SIM-002`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: `2026-09-13`
- 시작 시 Repository 상태: `087703e437ec3608445a709cbfa435f5823b571c`, clean worktree
- 선행 조건: current `SIM-001_acceptance.json`의 `ACCEPT + SIM_CONTRACT_PROFILE_READY`, exact profile/evidence/payload/reviewed-commit/source bindings, `TASK-SIM-002 authorized=true`

## 2. 작업 목적

Accepted Simulation Contract Profile이 physical hardware 없이 실행 가능함을 입증하는 최소 bounded deterministic smoke runtime을 구현하고, success/failure/timeout/unknown-reconciliation 결과를 machine-readable evidence로 결속하는 작업이다.

## 3. 구현 범위

### 구현한 내용

- accepted closed JSON Schema와 semantic contract를 검사하는 `simulation_runtime.smoke` core
- `mission.execute`, `navigation.execute`, `vla.execute`, `action_status.get`, `verification.verify` logical operation 기반 deterministic scenarios
- deterministic success, typed failure, virtual bounded timeout, authoritative reconciliation 네 scenario
- fixture identity/version/hash/timestamp/source correlation과 deterministic exact-match verification
- standalone smoke CLI, focused tests, human-readable report, machine-readable evidence

### 명시적으로 구현하지 않은 내용

- full simulator, physics engine, Gazebo/Nav2/MoveIt/`ros2_control` integration
- physical robot/camera/gripper/E-stop/teleoperation access 또는 adapter
- Dataset V1, training/fine-tuning, GPU/paid resource provisioning
- Week task, hardware target freeze, new mission-to-actuator public port
- `TASK-SIM-GATE`, `SIM_GO`, independent review 또는 `SIM-002_acceptance.json`

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/simulation_runtime/__init__.py` | bounded smoke API export |
| `src/simulation_runtime/smoke.py` | deterministic contract-valid scenarios와 fail-closed semantic validation |
| `scripts/run_simulation_smoke.py` | executable smoke entry point |
| `tests/test_simulation_smoke.py` | scenario, determinism, timeout, reconciliation, fixture integrity, isolation regression |
| `docs/simulation/simulation_smoke_runtime_v1.md` | human-readable execution/isolation report |
| `results/simulation/SIM-002_smoke_runtime.json` | source/code/report/test/scenario/authorization evidence |
| `docs/task_history/TASK-SIM-002/01_implementation.md` | 이번 workflow 상세 기록 |
| `docs/task_history/TASK-SIM-002/README.md` | TASK workflow 요약 |
| `docs/task_history/README.md` | global TASK history index 갱신 |

## 5. 주요 구현 내용

Runtime은 accepted schema를 직접 읽고 모든 public contract message를 closed-schema validation한다. Request의 RFC 3339 UTC calendar validity와 `deadline_at > timestamp`, request/result identity, navigation destination correlation, fixture reference integrity를 추가 semantic check로 검증한다.

Timeout scenario는 실제 sleep이나 thread/process를 시작하지 않는다. Fixed virtual no-result가 `1000 ms` bound에 도달한 것으로 결정적으로 모델링되어 `result=pending`, `status=unknown`, `MODEL_TIMEOUT`을 반환한다. Reconciliation scenario는 matching `action_status.get` 결과와 immutable evidence를 사용해 `unknown -> reconciling -> reconciled(resolved_status=succeeded)`만 허용한다.

## 6. 주요 설계 판단

- Existing MVP runtime의 planning-era `schema_version=v1` contract를 재해석하지 않고 별도 Simulation Lane package에서 accepted `schema_version=1.0`을 사용했다.
- Wall-clock sleep을 제거해 timeout behavior와 test result를 deterministic하고 빠르게 유지했다.
- Runtime output에는 timestamp 측정값을 넣지 않아 동일 input/fixture/initial state가 canonical byte-equivalent output을 만든다.
- Public operation 이름은 protocol-neutral logical identifiers이며 physical/native transport binding을 만들지 않는다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Predecessor eligibility | inline read-only Python validator | SIM-001 acceptance/profile/evidence/payload/source binding — PASS |
| Smoke CLI | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 scripts/run_simulation_smoke.py` | S01–S04 `PASS` — PASS |
| Focused tests | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest tests/test_simulation_smoke.py -q -p no:cacheprovider` | `11 passed` — PASS |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` | `169 passed` — PASS |
| Static parse/repeatability | inline read-only Python validator | AST parse와 repeated canonical output — PASS |
| Evidence/source/hash | inline read-only Python validator | implementation/report/predecessor/payload/C01–C20 — PASS |
| Repository whitespace | `git diff --check` 및 untracked-file whitespace scan | PASS |

## 8. Exit Criteria

- SIM-001 consumer eligibility가 implementation 전에 유효 — PASS
- executable smoke entry point 존재 — PASS
- deterministic success scenario — PASS
- explicit failure scenario — PASS
- bounded timeout scenario — PASS
- unknown/reconciliation invariant — PASS
- repeated-run determinism — PASS
- bounded process/resource cleanup — PASS
- physical/camera/teleoperation isolation — PASS
- training/Dataset V1/Week/hardware-freeze boundary 보존 — PASS
- report/evidence와 C01–C20 integrity — PASS
- downstream TASK-SIM-GATE 미착수 — PASS

## 9. Evidence

- 경로: `../../../results/simulation/SIM-002_smoke_runtime.json`
- Evidence SHA-256: `0529b8a093426316f41abf0ba2ad0cdfd3400720fe1fdba2129b131f6f4cb9ce`
- Payload SHA-256: `9736283612137e4cc27b86a55b06d32c2d5a4a160e56c3bde828bfa1fe26b22c`
- Report SHA-256: `c4b4d91849883d8f4197d1be0128dc18c81ef2da9bc17197431262e0c738a0f6`
- Canonical smoke output SHA-256: `7a7aff1014a03c02f76cbdd1909ce52e717e096c6128c121ec3dd1bc8518479a`
- 상태: `SIM_SMOKE_READY`

## 10. 구현 결과

`TASK-SIM-002 is complete.`

```text
Task-specific decision: SIM_SMOKE_READY
Independent acceptance: PENDING
TASK-SIM-GATE readiness eligibility: false
```

## 11. 다음 단계

별도 independent READ-ONLY review가 runtime, tests, report, evidence 및 source bindings를 검증해야 한다. 이후 current evidence/report hashes에 결속된 post-review acceptance artifact가 생성되기 전까지 `TASK-SIM-GATE`는 READY predecessor로 소비할 수 없다.
