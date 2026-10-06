# A1 — actual Gate G contract

STATUS: PASS
FIRST_FAILING_INVARIANT: NONE (contract reconstructed)
EVIDENCE: `demo_3d/tools/verified_normal.py:264–269` constructs G; line 273 formats `Gate G: PASS/FAIL`. Actual boolean:

G = runner_exit_zero AND normal_ready AND canonical_cleanup_true AND no_owned_survivors

| Predicate | Evidence field | PASS condition |
|---|---|---|
| runner_exit_zero | process_lifecycle.json#/runner_exit_code | `rc == 0` |
| normal_ready | normal_e2e_result.json#/task_specific_result | exactly `SIM_NORMAL_E2E_READY` |
| canonical_cleanup_true | normal_e2e_result.json#/execution/lifecycle/cleanup_complete | `is True` |
| no_owned_survivors | process_lifecycle.json#/alive_after_cleanup | empty list |

`SIM_NORMAL_E2E_READY` is derived by `scripts/run_simulation_normal_system_e2e.py:144`: mission.result == success AND lifecycle.cleanup_complete is True AND final step.name == final_verification AND final step.result.verdict == pass. Python AND short-circuits in this order. G adds no independent action acknowledgment/lifecycle activation predicate; those affect the upstream mission result.

NEXT_GATE: A2
