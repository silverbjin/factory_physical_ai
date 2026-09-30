# SIM-009 Worker Semantic-Provenance Fix — TASK-SIM-Q01-MIN

## Scope and constraints

This was one bounded diagnosis-and-fix cycle for the SIM-009 private-action
worker semantic provenance path.  The frozen MIN-Q01 scope remains one
SIM-008 qualification plus ten SIM-009 scenarios.  No task specification,
accepted predecessor Acceptance/Evidence, frozen SIM-010 artifact, or
protected `results/simulation/SIM-004_navigation_backend.json` was changed.
No orchestrator, resume, reset, clean, stash, restore, stage, or commit
command was used.

## Diagnosis

The worker bridge had a different log-boundary ordering from the direct rclpy
path:

```text
direct client: capture log offsets -> send goal -> observe terminal -> read window
worker path:  worker.execute (send goal + observe terminal) -> capture offsets -> read window
```

The parent is the launch-log owner, and the worker's JSON terminal response
already carries the goal UUID, terminal status, and native error fields.  It
is therefore safe for the parent to snapshot each launch-owned log before
writing the worker `execute` request, retain those offsets on the attempt,
then read only the bytes from those same paths after the terminal observation.
The runtime/session and worker remain unchanged and worker cleanup still
occurs before the shared runtime cleanup.

The accepted `_validate_live_navigation_evidence()` requirements remain
unchanged.  In particular it requires scenario/execution identity, a
goal-local attributed log window for every attempt, action/destination
identity, matching Nav2 request/terminal UUIDs, terminal status `6` for the
fault rows, and scenario-specific abort or TF semantics.

## Minimum correction

In `GoalTrackedGazeboNav2Runtime._navigate_with_worker()` the parent now:

1. captures launch-log offsets immediately before `PrivateActionWorker.execute`;
2. creates the attempt with those offsets and the worker-returned goal UUID;
3. reads only that pre-goal-to-terminal window after a terminal response.

`_observation_from_worker()` also rejects a terminal response whose
`goal_uuid` differs from the recorded dispatched UUID, before log association.
This preserves same-goal correlation rather than accepting a worker-side
terminal observation for a different goal.

## RED -> GREEN coverage

Added `test_worker_goal_captures_its_server_log_boundary_before_dispatch_and_binds_terminal_uuid`.

RED result before the correction:

```text
AssertionError: ['execute', 'capture'] != ['capture', 'execute']
```

GREEN result after the correction:

```text
2 passed, 45 deselected
```

Existing focused coverage also verifies no cumulative/cross-scenario log reuse,
TF-local probes and goal evidence, and timeout reconciliation retaining the
same goal identity.

## Focused tests

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  -m pytest -q -p no:cacheprovider \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_failure_recovery.py \
  tests/test_simulation_provenance_qualification.py
```

Result:

```text
113 passed in 4.26s
```

## Fresh GATE-4 SIM-009 suite

A fresh live suite was executed directly through `run_failure_suite()` with
the repository `src` on the import path.  This intentionally avoided the
standalone evidence writer, so no frozen SIM-009 Evidence was overwritten.
Shared readiness was healthy:

```text
launch                 PASS
clock                  PASS
odom                   PASS
localization           PASS
base action readiness  PASS
private action client  PASS
cleanup                PASS
```

Observed NAV rows:

| Row | Result | Relevant observation |
| --- | --- | --- |
| `SIM009-NAV-BLOCKED` | PASS | Goal-local attributed server window; request UUID equals terminal UUID. |
| `SIM009-NAV-ABORTED` | PASS | Pre-goal boundary `43796`, end `43944`; log contains `Couldn't open input XML file: /tmp/sim009-missing-behavior-tree.xml`; UUIDs match. |
| `SIM009-NAV-TIMEOUT-RETRY` | BLOCKED | Initial same goal has terminal status `5` after cancellation and an attributed window, but no authorized retry was emitted; only one attempt is present. |
| `SIM009-NAV-TF-UNAVAILABLE` | PASS | Own pre-goal window contains the injected missing-frame transform error; baseline/injected TF probes have the same scenario execution ID; UUIDs match. |

The suite result was `SIM_FAILURE_SUITE_BLOCKED` because
`SIM009-NAV-TIMEOUT-RETRY` is false.  This is the first remaining concrete
invariant after the semantic-provenance fix.  Per the requested stop rule, no
additional repair was attempted and GATE-5, canonical 11-subject preflight,
and repeatability were not run.

## Status

```text
GATE-4 SIM009 navigation: BLOCKED
GATE-5 correlation: BLOCKED_BY_GATE_4
GATE-6 canonical 11-subject: BLOCKED_BY_GATE_4
GATE-7 repeatability: BLOCKED_BY_GATE_4
```
