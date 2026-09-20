# Review — TASK-SIM-009

- Stage: independent re-review
- Task: `TASK-SIM-009`
- Recommendation: `REJECT`
- Validation: focused validation `72 passed`; `git diff --check` = `PASS`
- Evidence: distinct live fault signatures are proven, but scenario-local Evidence remains incomplete

## Blocking Findings

### SIM009-REREV-001 — HIGH — RETAINED

- Requirement / Contract: R3 L1-NAV must independently prove live `BLOCKED`, `ABORTED`, and `TF-UNAVAILABLE` fault classes with scenario-local Evidence.
- File / Symbol: `scripts/sim009_goal_tracked_navigation.py::GoalTrackedGazeboNav2Runtime._server_log_tail`; `src/simulation_runtime/failure_recovery.py` Navigation scenario Evidence/counters.
- Issue: distinct destinations/injections and unique Nav2 goal UUIDs are now proven, but `_server_log_tail()` attaches the last 4000 bytes of the cumulative process log to each later goal attempt. Observed live artifacts show `BLOCKED` with its own log, `ABORTED` also containing the prior BLOCKED outside-bounds log, `TIMEOUT-RETRY` containing prior BLOCKED and behavior-tree logs, and `TF-UNAVAILABLE` containing all preceding fault logs. This violates `no cumulative Evidence reuse`; it is material because ABORTED and TF action results expose native error code `0`, making server-log attribution authoritative.
- Issue: `runtime_calls` is cumulative (`BLOCKED 1`, `ABORTED 2`, `TIMEOUT-RETRY 4`, `TF-UNAVAILABLE 5`) instead of scenario-local (`1`, `1`, `2`, `1`).
- Why it blocks acceptance: later rows can inherit prior-scenario fault proof and counters, so scenario-local provenance is not authoritative.
- Recommended remediation: keep the fix additive and SIM-009-owned; capture server output from a scenario/goal-specific log offset and bind it to `scenario_execution_id`; derive `runtime_calls` and logical side-effect counts from scenario-filtered attempts; add regressions rejecting prior-scenario log markers and cumulative counters; regenerate `SIM-009_failure_recovery_run1.json`, `SIM-009_failure_recovery_run2.json`, and `SIM-009_repeatability.json`; leave accepted predecessor implementations unchanged.

## Independently verified

- BLOCKED routing, native error `204`, terminal `ABORTED`, and 7000ms bounded budget: `PASS`
- ABORTED missing behavior-tree injection and unique behavior-tree server error: `PASS`
- TF baseline probe, injected-frame missing TF probe, and native missing-frame server error: `PASS`
- TIMEOUT reconciliation, bounded retry, identity preservation, and one logical side effect: `PASS`
- Repeatability identities/signatures: `PASS`
- SIM-004/005/006/008 accepted hashes: `PASS`
- Protected predecessor source diff: none
- Review modified no files; Review created no commit

```json
{"v":1,"task_id":"TASK-SIM-009","stage":"review","status":"REJECT","workflow_complete":true}
```
