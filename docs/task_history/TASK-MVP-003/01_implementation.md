# Implementation — TASK-MVP-003

## 1. 작업 정보

- TASK: `TASK-MVP-003`
- 작업 유형: Implementation history backfill
- 실행 순번: `04` (기존 `01_review.md` → `02_fix.md` → `03_review.md` 뒤의 다음 유효 순번)
- 원 구현 및 acceptance 일자: `2026-08-28`
- 이력 보강 일자: `2026-08-29`
- 시작 시 Repository 상태: implementation/test/evidence와 review/fix/re-review 기록은 존재했으나 Implementation 기록만 누락되어 있었다.
- 선행 조건: `TASK-P0-002 = GO`, `TASK-MVP-002` state model
- implementation commit: `2c0270cf51805f1d91673b8794a03cc4c8ebb84d` (`feat(mvp): add deterministic factory tool gateway and skill fakes`)
- evidence base commit: `ce828f1bf50feaf5a704f80fda603d397bffa552`; evidence 생성 시점에는 MVP-003 changes가 uncommitted였으며 base commit이 MVP-003 source를 포함한다고 해석하면 안 된다.

## 2. 작업 목적

canonical line-side mission에 필요한 최소 factory boundary를 한 in-process deterministic gateway로 제공한다. gateway는 WMS inventory query, high-level Robot Skill transfer, future reconciliation을 위한 action-status query만 expose하며, Agent/LLM가 raw execution surface에 접근하지 못하게 한다.

## 3. 구현 범위

### 구현한 내용

- `FactoryToolGateway`의 typed `query_inventory`, `transfer_part`, `get_action_status` entry point
- `DeterministicInventoryFake`: `Brake ECU Type-B`에 대해 `Rack A19`, quantity `1`을 반환하는 canonical WMS fixture
- `DeterministicRobotSkillFake`: typed transfer result, action query, same `action_id` idempotent result, constructor-controlled failure fixture
- strict `InventoryQuery`, `TransferPartRequest`, `ActionStatusQuery` request validation
- `InventoryResult`, `TransferResult`, `ActionStatusResult`, `ToolError`, `ToolResultKind`, `ToolErrorCategory` typed envelope
- unknown action typed failure에도 `schema_version`, `mission_id`, `request_id`, `action_id`, UTC `timestamp`를 보존하는 reconciliation observation boundary

### 명시적으로 구현하지 않은 내용

- Agent-to-gateway integration, robot dispatch, actual WMS/Fleet/PHM service, external process/network
- timeout classification, reconciliation policy, retry, mission-state recovery (TASK-MVP-004 scope)
- persistence/SQLite, ROS 2, Nav2, MoveIt, `ros2_control`, VLA, physical robot/camera, hosted LLM SDK, Docker, PostgreSQL, Grafana, multi-agent

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/factory_tools/__init__.py` | typed gateway/fixture/query/result public exports |
| `src/factory_tools/gateway.py` | strict schemas, deterministic WMS/Robot Skill fakes, action-status reconciliation boundary |
| `tests/test_factory_tools.py` | canonical fixture, typed failure, validation, idempotency, action query, raw execution absence regression |
| `results/mvp/MVP-003.json` | machine-readable evidence와 H01 resolution provenance |

## 5. 주요 구현 내용

`FactoryToolGateway`는 untrusted request를 strict typed request model로 먼저 검증한 뒤 in-process fake로 전달한다. missing/extra field, non-string key, invalid UUID, non-UTC timestamp, blank string, invalid positive integer는 `ToolValidationError`로 fail-closed 처리된다.

`DeterministicInventoryFake`는 canonical part에만 `Rack A19`/available quantity `1`을 반환하며 unavailable SKU는 typed `RESOURCE_UNAVAILABLE` failure로 반환한다. `DeterministicRobotSkillFake`는 high-level `transfer_part` observation만 제공하고 raw ROS/Nav2/MoveIt command, pose, trajectory를 제공하지 않는다.

초기 independent review에서 action-status failure result에 correlation/version/timestamp envelope이 누락된 `TASK-MVP-003-REV-H01`을 발견했다. `02_fix.md`에서 `ActionStatusQuery`와 non-null `ActionStatusResult` envelope을 추가했고, `03_review.md`가 이를 ACCEPT했다. 이 backfill은 그 최종 accepted implementation을 기록한다.

## 6. 주요 설계 판단

- gateway는 WMS/Robot Skill을 separate service로 만들지 않고 deterministic in-process fixture로 한정했다.
- side-effecting transfer request에는 `mission_id`, `request_id`, `action_id`, `idempotency_key`, timestamp/deadline correlation을 요구한다.
- action-status query도 success와 failure 모두 full typed envelope을 반환해야 MVP-004 reconciliation이 audit 가능한 same-action observation을 받을 수 있다.
- timeout/retry decision은 runtime policy의 책임이므로 gateway/fixture가 그 policy를 먼저 구현하지 않는다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| 당시 focused test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_factory_tools.py -v` | 8 PASS (`MVP-003.json` measured result) |
| 당시 full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 36 PASS (`MVP-003.json` measured result) |
| 당시 syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS (`MVP-003.json` measured result) |
| 당시 intended-file whitespace | intended source/test/evidence마다 `git diff --no-index --check /dev/null` | PASS (`MVP-003.json` measured result) |
| 이력 보강 시 focused recheck | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_factory_tools.py -v` | 8 PASS |

## 8. Exit Criteria

- one factory-tool gateway exists — PASS
- WMS fake supports canonical mission — PASS
- Robot Skill fake supports canonical mission — PASS
- action status can be reconciled — PASS
- typed errors exist — PASS
- deterministic tests pass — PASS

## 9. Evidence

- 경로: `../../../results/mvp/MVP-003.json`
- SHA-256: `cb020b51e00fc56beccb7c9bd9be6a65309c67d7eb35654b6bc02a2c21aef89b`
- 상태: PASS
- evidence snapshot: `src/factory_tools/__init__.py` `7bdaa8d3f083195485b94e3c143286763c883be5c180142e94df527a911a340e`, `src/factory_tools/gateway.py` `ea3186ac80ac37570d2ddf48e1394f4d69338bd718ba0008a3809c44e6000351`, `tests/test_factory_tools.py` `3a872eb2f92850b11165925ec1b52e5c8a0cbdb1c203cefeb10da7c8e6bd7827`
- 현재 `tests/test_factory_tools.py`는 evidence hash와 일치한다. `src/factory_tools/__init__.py`와 `src/factory_tools/gateway.py`의 현재 hash는 후속 accepted `TASK-MVP-004` timeout fixture 확장으로 달라졌으며, MVP-003 evidence의 historical snapshot claim을 변경하지 않는다.

## 10. 구현 결과

`TASK-MVP-003 is complete.`

## 11. 다음 단계

Independent review/fix/re-review는 이미 `01_review.md`, `02_fix.md`, `03_review.md`에 기록되어 있으며 최종 결과는 `ACCEPT TASK-MVP-003`이다.
