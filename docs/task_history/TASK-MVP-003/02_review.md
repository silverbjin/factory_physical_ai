# Read-only Review — TASK-MVP-003

## 1. 검토 정보

- TASK: `TASK-MVP-003`
- 작업 유형: Independent Read-only Review
- 실행 순번: `01`
- 검토 대상: `src/factory_tools/`, `tests/test_factory_tools.py`, `results/mvp/MVP-003.json`
- 검토 시점 Git 상태: MVP-003 구현 파일이 untracked 상태이며, 다른 변경 사항은 확인되지 않음

## 2. 검토 결론

- Recommendation: `REJECT`
- BLOCKER: 0
- HIGH: 1
- MEDIUM: 0
- LOW: 0

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| 하나의 in-process factory-tool gateway | `FactoryToolGateway` | `test_canonical_inventory_lookup_returns_rack_a19` | `validated_capabilities.typed_gateway_operations` | PASS |
| WMS fake canonical fixture | `DeterministicInventoryFake` | `test_canonical_inventory_lookup_returns_rack_a19` | `validated_capabilities.inventory_fixture` | PASS |
| typed Robot Skill fake | `DeterministicRobotSkillFake` | `test_transfer_success_returns_typed_result_and_queryable_action_status` | `exit_criteria.robot_skill_fake_supports_canonical_mission` | PASS |
| `get_action_status(action_id)` typed reconciliation boundary | `ActionStatusResult` | `test_unknown_or_malformed_action_status_query_fails_typed` | `exit_criteria.action_status_can_be_reconciled` | FAIL |
| malformed request fail-closed | `InventoryQuery.from_mapping`, `TransferPartRequest.from_mapping` | `test_malformed_requests_fail_closed` | `validated_capabilities.malformed_requests_fail_closed` | PASS |
| deterministic and fault-injectable fixtures | `DeterministicRobotSkillFake` | `test_same_fixture_inputs_produce_same_results`, `test_configured_failure_fixture_is_deterministic_and_queryable` | `skill_fixture_is_deterministic_and_fault_injectable` | PASS |
| raw ROS/Nav2/MoveIt access absent | `FactoryToolGateway` public surface | `test_no_raw_execution_layer_access_is_exposed` | `raw_ros_nav2_moveit_access_absent` | PASS |

## 4. 주요 Findings

### BLOCKER

없음

### HIGH

- **ID:** `TASK-MVP-003-REV-H01`
- **File / Symbol:** `src/factory_tools/gateway.py` — `ActionStatusResult`, `DeterministicRobotSkillFake.get_action_status`
- **Issue:** `ActionStatusResult`에는 frozen `docs/contracts/contract_plan.md`의 cross-cutting `schema_version`가 없고, `mission_id`, `request_id`, `timestamp`가 `None`일 수 있다. 특히 unknown `action_id`의 typed failure는 `timestamp=None`으로 반환된다.
- **Why it matters:** `get_action_status(action_id)`는 MVP-004 reconciliation의 관찰 boundary다. 실패 관찰이 version/correlation/timestamp 없이 반환되면 same-action reconciliation, audit, evidence correlation을 신뢰성 있게 수행할 수 없다.
- **Requirement / Contract affected:** `docs/contracts/contract_plan.md` cross-cutting envelope 및 Day-10 MVP contract profile의 `schema_version`, correlation, UTC `timestamp`, typed error/result 요구사항.
- **Evidence:** dataclass field inspection에서 `ActionStatusResult`는 `schema_version`을 갖지 않았고 nullable `mission_id`, `request_id`, `timestamp`를 확인했다. 현재 focused test는 successful status query만 correlation을 검사하며 failure envelope은 검사하지 않는다.
- **Recommended remediation:** action-status query에도 strict typed query envelope 또는 동등한 deterministic metadata source를 도입하고, 모든 success/failure `ActionStatusResult`에 non-null `schema_version`, mission/request correlation, UTC `timestamp`, `source_kind`, `component_version`을 제공한다. unknown action failure와 malformed status query의 full-envelope regression test를 추가하고 `results/mvp/MVP-003.json` hash/claim을 갱신한다.

### MEDIUM

없음

### LOW

없음

## 5. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: FAIL
Contract compliance: FAIL
State / invariant safety: NOT APPLICABLE
Test adequacy: FAIL
Regression safety: PASS
Evidence integrity: FAIL
```

## 6. 검토에서 확인한 핵심 위험

- MVP-003의 fake는 deterministic하고 physical execution을 포함하지 않지만, MVP-004가 의존하는 status-query failure 관찰에는 correlation envelope이 없다.
- focused/full regression은 모두 PASS했지만 unknown action typed failure의 `schema_version` 및 UTC `timestamp`를 검증하지 않아 frozen contract 위반을 발견하지 못했다.
- `results/mvp/MVP-003.json`의 `action_status_can_be_reconciled: PASS`는 이 contract gap 때문에 현재 repository 상태를 과장한다.

## 7. 최종 Recommendation

`REJECT TASK-MVP-003`
