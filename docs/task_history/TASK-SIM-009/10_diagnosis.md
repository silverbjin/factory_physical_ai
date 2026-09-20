# Diagnosis — TASK-SIM-009

- Stage: diagnosis
- Status: RESOLVED
- Read-only mode: YES
- Trigger: latest independent Re-review `09_review.md`
- Triggering lifecycle status: REJECT
- Triggering finding: `SIM009-REREV-001` — HIGH
- Diagnosis tier/model: Sol Medium

## Root Cause

세 L1-NAV 시나리오가 SIM-009의 dispatch와 Evidence attribution에서 붕괴한다. `_action_request()`가 Navigation 목적지를 `blocked-bay`로 기본 설정하므로 BLOCKED와 ABORTED가 동일한 live Nav2 요청을 실행한다. TF-unavailable는 live Gazebo/Nav2/TF fault가 아니라 `_ScriptedNavigationRuntime(ready=False)`를 사용한다. 또한 `run_failure_suite()`가 Navigation 행에 누적 `live_runtime.evidence()`를 복사하여 scenario-local provenance를 잃는다.

## Violated or Missing Contract

R3가 요구하는 blocked path, navigation abort, TF/dependency unavailable의 독립적인 live Gazebo/Nav2 관찰과 scenario-local Evidence가 입증되지 않았다. 문제는 accepted SIM-004/SIM-008 predecessor boundary가 아니라 SIM-009 fault dispatch와 Evidence binding이다.

## Authoritative Sources

- `docs/task_history/TASK-SIM-009/09_review.md`
- `tasks/TASK-SIM-009.md`
- `results/reviews/SIM-004_acceptance.json`
- `results/reviews/SIM-008_acceptance.json`
- `src/simulation_runtime/navigation_backend.py`
- `scripts/run_simulation_navigation.py`
- `scripts/run_simulation_normal_system_e2e.py`
- `scripts/sim009_goal_tracked_navigation.py`
- `src/simulation_runtime/failure_recovery.py`
- `configs/simulation/sim009_failure_scenarios.json`
- `tests/test_simulation_failure_recovery.py`

## Resolution

accepted runtime chain을 보존하고 SIM-009-owned adapter/injection만 추가한다:

```text
NavigationBackend
→ NavigationRuntime protocol
→ SIM-009 GoalTrackedGazeboNav2Runtime
→ accepted SIM-004 BoundedGazeboNav2Runtime
→ live Gazebo + ROS 2 + Nav2
```

- `SIM009-NAV-BLOCKED`: `blocked-bay`, 정상 `map` frame, 기본 behavior tree; accepted goal UUID와 native outside-map/no-valid-path 결과를 기록한다.
- `SIM009-NAV-ABORTED`: reachable `line-b-drop`, 정상 `map` frame, private `NavigateToPose.Goal.behavior_tree`에 고유한 nonexistent SIM-009 path를 one-shot 주입한다. Nav2 goal acceptance, 동일 UUID, terminal `ABORTED`, native behavior-tree load/execution error를 요구한다.
- `SIM009-NAV-TF-UNAVAILABLE`: reachable `line-b-drop`, 기본 behavior tree, 고유 nonexistent frame을 goal에 one-shot 주입한다. 정상 `map → base_link`와 주입 frame의 bounded TF probe를 먼저 기록하고, live Nav2의 terminal `ABORTED` 및 native TF error code/message를 요구한다.

이 설계는 public contract state를 추가하지 않으며 accepted predecessor implementation을 수정하지 않는다.

## Modification Scope

- `scripts/sim009_goal_tracked_navigation.py`: `GoalAttemptRecord`, `GoalTrackedGazeboNav2Runtime.__init__`, `navigate`, `_observation_from_result`, `evidence`; one-shot scenario fault-arm 및 scenario-filtered Evidence 추가.
- `src/simulation_runtime/failure_recovery.py`: `_action_request`, `_navigation_scenario`, `run_failure_suite`; distinct live routing 및 scenario-local Evidence validation 추가.
- `configs/simulation/sim009_failure_scenarios.json`: precise injection descriptions와 bounded live budgets.
- `tests/test_simulation_failure_recovery.py`: routing, injection signature, native classification, UUID/Evidence isolation 및 reuse rejection 회귀 검증.
- 성공적인 host live validation 후 SIM-009 Evidence 결과 파일 4개를 재생성한다.

## Protected Scope

수정 금지:

- `src/simulation_runtime/navigation_backend.py`
- `scripts/run_simulation_navigation.py`
- `src/simulation_runtime/normal_system_e2e.py`
- `scripts/run_simulation_normal_system_e2e.py`

Acceptance JSON, `acceptance_handoff`, predecessor contract/schema, implementation/source/test 외의 승인 기록은 생성하거나 변경하지 않는다.

## Verification Plan

독립 Re-review 전에 다음을 입증해야 한다:

- BLOCKED/ABORTED/TF-unavailable가 각각 `blocked-bay`, `line-b-drop`, `line-b-drop`으로 route된다.
- 세 fault injection signature가 pairwise distinct하고 native result classification이 서로의 성공 조건을 충족하지 못하게 한다.
- 각 행의 request/action/goal UUID, scenario execution ID, frame, behavior tree, native error가 scenario-local이며 세 goal UUID 집합이 서로 겹치지 않는다.
- 누적 Evidence 복사, scenario execution ID/frame/behavior-tree/native error 불일치가 validation failure가 된다.
- repeatability run1/run2 모두 세 distinct live fault signature를 독립적으로 포함한다.

## Handoff / Next Action

- Next action: IMPLEMENT_RESOLVED_FIX
