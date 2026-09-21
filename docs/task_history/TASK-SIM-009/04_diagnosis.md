# Diagnosis — TASK-SIM-009

- Stage: diagnosis
- Status: RESOLVED
- Read-only mode: YES
- Trigger: `SIM009-REV-001`, `SIM009-REV-003`, `SIM009-REV-004` 차단 해소를 위한 두 차례의 READ-ONLY architecture diagnosis
- Triggering lifecycle status: `FIX_NOT_READY`
- Blocking finding IDs: `SIM009-REV-001`, `SIM009-REV-003`, `SIM009-REV-004`
- Diagnosis tier/model: Final `Sol High`; Previous `Sol Medium` (`UNRESOLVED`)

## Root Cause

- L1-NAV가 `_ScriptedNavigationRuntime`을 사용하여 실제 Nav2 goal identity, terminal status, timeout 이후 원래 goal의 완료 여부 및 live idempotency를 증명하지 못했다.
- `VerificationDecision.route`가 accepted `MissionRecord.transition()` lifecycle으로 적용되지 않았고, `EXECUTING → RECOVERING` 직접 전이는 불법이다.

## Violated or Missing Contract

- retry authorization은 동일 `mission_id`, `action_id`, `idempotency_key`와 authoritative failed reconciliation 뒤에만 허용된다.
- Verification route는 Mission completion을 직접 commit하지 않으며, accepted Mission lifecycle의 legal transition을 통해 처리되어야 한다.

## Authoritative Sources

- SIM-004: `BoundedGazeboNav2Runtime`
- SIM-008: `GazeboSystemWorld`
- MVP-004: `MissionRecord`, `SingleFailureRecoveryCoordinator`
- SIM-006: `VerificationDecision.route` routing behavior

## Resolution

- accepted SIM-004 core를 수정하지 않고 `scripts/sim009_goal_tracked_navigation.py`의 `GoalTrackedGazeboNav2Runtime` additive wrapper/subclass를 사용한다.
- binding은 `navigation request → accepted Nav2 ClientGoalHandle → Nav2 goal UUID → same UUID terminal GetResult → reconciliation → retry authorization`이다.
- logical navigation effect는 `(mission_id, action_id, idempotency_key, destination_id)`이며, 같은 effect에 결속된 모든 Nav2 UUID에서 `count(terminal Nav2 status == SUCCEEDED) == 1`을 증명한다.
- SIM-009-owned adapter가 `VerificationDecision.route`를 accepted `MissionRecord.transition()`으로 적용한다: `RECOVERY`는 `EXECUTING → RECONCILING → RECOVERING`, `RECONCILE`는 `EXECUTING → RECONCILING`, `HITL`은 `EXECUTING → ESCALATED`이다.

## Modification Scope

- Add: `scripts/sim009_goal_tracked_navigation.py` — `GoalTrackedGazeboNav2Runtime`, `GoalAttemptRecord`, `navigate()`, `reconcile()`, `close()`, runtime-derived goal/cleanup evidence accessor.
- Modify during subsequent Fix: `src/simulation_runtime/failure_recovery.py`, `scripts/run_simulation_failure_recovery.py`, `configs/simulation/sim009_failure_scenarios.json`, `tests/test_simulation_failure_recovery.py`.
- Regenerate after live validation: `results/simulation/SIM-009_failure_recovery.json`.

## Protected Scope

- Do not modify: `scripts/run_simulation_navigation.py`, `src/simulation_runtime/navigation_backend.py`, `src/mission_runtime/state.py`, `src/mission_runtime/recovery.py`.

## Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_failure_recovery.py \
  tests/test_simulation_execution_contract.py \
  tests/test_mission_runtime.py \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_mission_integration.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_mujoco_vla_backend.py \
  tests/test_simulation_verification_backend.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_simulation_failure_recovery.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_simulation_failure_recovery.py
git diff --check
```

두 live run은 request→Nav2 goal UUID binding, terminal reconciliation 전 retry 금지, reconciled success/unknown retry suppression, logical effect당 정확히 하나의 successful Nav2 goal, actual Mission lifecycle transition, cleanup bound 내 PID/PGID 종료 및 두 번째 run의 독립성을 증명해야 한다.

## Handoff / Next Action

- Next action: IMPLEMENT_RESOLVED_FIX
- Architecture diagnosis는 완료되었으나 TASK acceptance 및 independent Re-review는 승인되지 않았다.
