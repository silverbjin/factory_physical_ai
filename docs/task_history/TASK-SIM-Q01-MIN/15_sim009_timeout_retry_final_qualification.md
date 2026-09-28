# SIM-009 TIMEOUT-RETRY Completion and Final Qualification — TASK-SIM-Q01-MIN

## 1. Accepted TIMEOUT-RETRY contract

Immutable authority was read from accepted SIM-009 commit
`67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be`, including the accepted
`failure_recovery.py`, `navigation_backend.py`, goal-tracked runtime, and
`results/simulation/SIM-009_failure_recovery.json` blob.

The accepted lifecycle is:

1. Create attempt-1 request with retry budget 1 and real mission, request,
   trace, action, and idempotency identities.
2. Dispatch a real NavigateToPose goal and retain its Nav2 UUID.
3. Return `pending/unknown` when the bounded result wait expires.
4. `action_status.get` reconciles the same action and cancels that same goal.
5. Observe the original goal terminal status `5` (canceled).
6. Normalize it as failed and retryable.
7. Read that reconciled terminal observation again as the explicit input to
   `_authorized_retry()`.
8. Authorize only when reconciliation succeeded, observed status is failed,
   the resolved observation is failed and retryable, and budget remains.
9. Allocate attempt 2 with a new request ID and incremented attempt number;
   preserve mission, action, idempotency, trace, and destination according to
   the accepted contract; decrement retry budget to zero.
10. Dispatch a second real NavigateToPose goal with a distinct Nav2 UUID.
11. Retain both attempts under the same scenario execution with independent
    goal-local server-log windows.
12. Require attempt 2 to succeed, exactly one logical side effect, and all
    retry identity assertions before returning decision `RETRY`.

The accepted Evidence contains two real goals: attempt 1 terminal status `5`
and attempt 2 terminal status `4`.

## 2. Accepted/current lifecycle comparison

| Lifecycle stage | Accepted | Current before correction |
| --- | --- | --- |
| attempt #1 | Real request and real goal retained | Same |
| timeout | `pending/unknown`, retryable timeout | Same |
| cancel | Same original goal canceled | Same worker-side cancellation; parent record was not marked |
| reconciliation | Original goal status `5`; repeat reads remain authoritative | First read returns status `5`; worker pending entry is consumed |
| retryability | Failed terminal observation remains retryable | First read is retryable; second read becomes non-retryable unknown |
| retry authorization | `_authorized_retry()` receives the retained failed/retryable observation | Receives `NAVIGATION_RECONCILIATION_PENDING`; returns `None` |
| attempt #2 allocation | New request ID, attempt 2, budget 0 | Not reached |
| retry goal dispatch | Second real goal with a distinct UUID | Not reached |
| attempt #2 terminal result | Status `4`, success | Not reached |
| final semantic decision | `RETRY`, pass | `FAIL_CLOSED`, blocked |

The first control-flow divergence was the second same-goal reconciliation
read. The accepted direct runtime retained its completed result future and was
idempotent. The worker bridge used `pending.pop(action_id)`, so only the first
read could return the terminal result.

## 3. Root cause

```yaml
root_cause_class: SIM009_WORKER_RETRY_PROTOCOL_DEFECT
first_failing_invariant: repeated reconciliation of the same completed goal must be idempotent
accepted_behavior: both reconciliation reads return the same failed retryable terminal observation
current_behavior: the first worker reconciliation consumes the pending entry and the second returns missing
causal_evidence: action_status_get performs the first reconcile; accepted retry policy performs a second direct reconcile; the parent retained terminal fields but not the normalized terminal observation
architecture_change_required: NO
```

There is no conflict between the accepted semantic contract and the converged
runtime architecture.

## 4. RED reproduction

Added
`test_worker_timeout_reconciliation_remains_authoritative_for_retry_policy`.
It drives the real `_navigation_scenario()` and
`GoalTrackedGazeboNav2Runtime` control flow through a one-shot worker boundary:
attempt 1 creates a real worker goal identity, times out, reconciles once to
status `5`, and a second worker read returns `missing`.

Before the correction:

```text
FAILED test_worker_timeout_reconciliation_remains_authoritative_for_retry_policy
assert row["pass"] is True
E assert False is True
1 failed, 47 deselected
```

This proves the existing bridge suppressed accepted retry authorization and
left the attempt count at one.

## 5. Bounded correction

Only `scripts/sim009_goal_tracked_navigation.py` changed in production code:

- `GoalAttemptRecord` retains the normalized terminal `RuntimeObservation`.
- `_observation_from_worker()` stores that observation only after validating
  the worker terminal UUID against the recorded goal UUID.
- repeated `reconcile(action_id)` calls return the retained authoritative
  observation without a second destructive worker read;
- timeout reconciliation records `cancellation_requested = true` before the
  worker cancellation/reconciliation operation.

Retry authorization, attempt allocation, request generation, worker goal
dispatch, validators, pre-goal log capture, runtime context, readiness,
cleanup, and canonical routing were not changed.

Focused RED-to-GREEN result:

```text
2 passed, 46 deselected
```

The one-shot worker was reconciled exactly once, while the policy's second
read used the retained observation and then dispatched a real second goal.

## 6. Focused regression

Required four-module command:

```text
114 passed in 4.20s
```

The previous baseline was 113 passing tests. Touched modules passed
`py_compile`, and `git diff --check` passed.

## 7. Fresh GATE-4 SIM-009 navigation runtime

Exactly one fresh post-correction SIM-009 live suite was run. Shared runtime
readiness reached `READY`, suite cleanup completed, infrastructure classified
`SEMANTIC_READY`, and the task result was `SIM_FAILURE_SUITE_READY`.

| NAV scenario | Result | Decision |
| --- | --- | --- |
| `SIM009-NAV-BLOCKED` | PASS | `FAIL_CLOSED` |
| `SIM009-NAV-ABORTED` | PASS | `FAIL_CLOSED` |
| `SIM009-NAV-TIMEOUT-RETRY` | PASS | `RETRY` |
| `SIM009-NAV-TF-UNAVAILABLE` | PASS | `FAIL_CLOSED` |

All four were within budget, used the live runtime, and cleanup was true.

`GATE-4 = PASS`.

## 8. Complete TIMEOUT-RETRY attempt lifecycle

```text
qualification_run_id:
  q01-sim009-cdeb9b91-a87e-4909-8619-81e79f65f491
scenario_execution_id:
  2b227552-190d-4694-a35d-9b89e48b5840
attempt_count: 2

attempt #1:
  mission_id: b2fc62ea-42f0-4f03-a16d-5b57c2b005da
  request_id: ff72481f-f7ee-4ef2-8a37-46a1ca3b594f
  trace_id: f79d43be-cc14-4202-97f1-00cf5d79fdd0
  action_id: 12ba99ea-de76-458f-948c-25e63aeae2af
  goal_uuid: 2a0675f3-a7eb-495c-8246-0804baf9dd55
  bounded_timeout: true
  cancellation_requested: true
  reconciliation_result: success
  reconciled_observed_status: failed
  terminal_status: 5
  retryable_terminal_failure: true
  server_log_attributed: true

retry authority:
  source: failure_recovery._authorized_retry
  reconciliation_completed: true
  resolved_status: failed
  error_retryable: true
  previous_attempt: 1
  next_attempt: 2
  retry_budget_remaining_before_dispatch: 1

attempt #2:
  request_id: dc83be90-ccde-4b12-b33b-f6b607f337a3
  attempt: 2
  retry_budget_remaining: 0
  mission/action/idempotency/trace: stable per accepted contract
  goal_uuid: 71d0ff77-a7a0-4e54-8506-df0d8049622d
  terminal_status: 4
  terminal_result: success
  server_log_attributed: true

scenario-local provenance:
  both attempts use scenario_execution_id 2b227552-190d-4694-a35d-9b89e48b5840
  goal UUIDs are distinct
  each attempt has a separate post-boundary server-log window
  logical_side_effect_count: 1
  accepted TIMEOUT-RETRY semantic policy: PASS
```

## 9. GATE-5 same-run correlation

The same GATE-4 suite used one qualification run ID and distinct preallocated
scenario execution IDs for all four NAV rows. Each fault row passed its
scenario-local validator, which binds the request action to the attempt,
terminal goal UUID, scenario ID, and scenario execution ID. Public results
were produced directly by `NavigationBackend` from each real request; no
correlation field was backfilled.

For TIMEOUT-RETRY, attempt 2 has a new request ID and a distinct real Nav2 goal
UUID. The accepted logical-action identities remain stable, both attempts are
bound to the same scenario execution, and the suite reports one successful
logical side effect.

`GATE-5 = PASS`.

## 10. GATE-6 canonical 11-subject result

The required canonical command was run with `/tmp` output and report paths.
It completed the live suppliers and entered collection, then failed closed:

```text
ValueError: MISSING_RUN_LOCAL_PROVENANCE
```

No canonical output or Markdown report was written. Deterministic frozen
manifest order establishes the first affected subject as:

```text
q01-sim009-SIM009-NAV-BLOCKED
```

SIM-008 is collected first. `SIM009-NAV-BLOCKED` is the first SIM-009 subject,
and `collect_sim009_execution_result()` rejects its absent/empty
`run_local_provenance` before any later subject is collected. The live supplier
sets that field only from the per-scenario structured Gazebo stats sidecar; no
historical or accepted Evidence backfill is permitted.

This is a new independent canonical run-local measurement fault domain, not a
TIMEOUT-RETRY failure. Per the required stop rule, it was not repaired here.

`GATE-6 = BLOCKED`.

## 11. GATE-7 repeatability

Not run because GATE-6 did not pass.

`GATE-7 = BLOCKED_BY_GATE_6`.

## 12. Protected scope verification

- MIN-Q01 remains exactly one SIM-008 plus ten SIM-009 subjects.
- No task specification was modified.
- No accepted predecessor Acceptance or Evidence was modified.
- Frozen SIM-010 was not modified.
- The protected dirty SIM-004 result was not reset, restored, cleaned,
  rewritten, staged, or committed.
- No validator or accepted semantic decision was weakened.
- No Evidence, retry attempt, request, goal, or identity was fabricated.
- No orchestrator or resume command was run.
- No unrelated process was killed; live runtime cleanup remained owned and
  bounded.

## 13. Final resume decision

```text
GATE-4 PASS
GATE-5 PASS
GATE-6 BLOCKED
GATE-7 BLOCKED_BY_GATE_6
ORCHESTRATOR_RESUME_READY = NO
```

First remaining invariant:

```text
q01-sim009-SIM009-NAV-BLOCKED has no non-empty same-run structured
run_local_provenance at canonical collection.
```
