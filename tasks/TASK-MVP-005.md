# TASK-MVP-005 — SQLite Persistence and Machine-Readable Evidence

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Persist the MVP mission/action lifecycle and emit machine-readable evidence sufficient to reconstruct the canonical run.

Use SQLite + JSONL/JSON only. Do not add PostgreSQL, OpenTelemetry collectors, Prometheus, Grafana, Docker Compose, or cloud infrastructure.

## 2. Required persistence

Persist at minimum:

- mission record;
- action record;
- state transitions;
- idempotency key;
- deadlines/timestamps;
- reconciliation event;
- retry count;
- final mission result.

## 3. Restart requirement

A deterministic test must prove that persisted state can be reloaded without converting `UNKNOWN` into success.

Do not attempt a full production crash-recovery platform.

## 4. Required run evidence fields

At minimum:

```text
run_id
mission_id
action_id(s)
mission_result
tool_call_valid
state_transitions
timeout_detected
reconciliation_performed
retry_budget
retry_count
recovery_result
hitl_escalated
mission_duration_ms
error_category
component_versions
```

## 5. Output

Each run writes under:

```text
results/mvp/runs/<run_id>/
```

with machine-readable JSON/JSONL artifacts.

Create summary:

`results/mvp/MVP-005.json`

## 6. Tests

- SQLite schema creation;
- mission/action persistence;
- transition persistence;
- reload persisted action;
- UNKNOWN remains UNKNOWN after reload;
- JSONL trace is parseable;
- evidence references valid mission/action IDs.

## 7. Exit Criteria

- [ ] SQLite persistence works;
- [ ] evidence is machine-readable;
- [ ] run can be reconstructed from persisted evidence;
- [ ] restart/reload test passes;
- [ ] no production telemetry stack introduced.

## 8. Commit

`feat(mvp): persist mission lifecycle and structured evidence`

Do not start MVP-006.
