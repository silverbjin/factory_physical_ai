# TASK-MVP-002 — Mission and Action State Model

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Implement the deliberately small deterministic mission/action state model required by the frozen Architecture v1.0.

Do not add generic workflow-engine functionality.

## 2. Required mission states

Keep the mission state machine finite and explicit. Recommended states:

```text
CREATED
READY
EXECUTING
RECONCILING
RECOVERING
COMPLETED
ESCALATED
FAILED
```

Only add a state if a test demonstrates it is required.

## 3. Required physical-action states

Implement the frozen reconciliation lifecycle:

```text
REQUESTED
EXECUTING
SUCCEEDED
FAILED
UNKNOWN
RECONCILING
```

Minimum action fields:

```text
mission_id
action_id
idempotency_key
schema_version
timestamp
deadline
status
error
retryable
component_version
```

## 4. Required behavior

- valid transitions are explicit;
- invalid transitions fail closed;
- `UNKNOWN` cannot be interpreted as success;
- the Agent cannot directly mutate action outcome;
- one HITL/escalation terminal path exists;
- model is independent of ROS/Nav2/VLA implementations.

## 5. Tests

At minimum:

- CREATED → READY;
- READY → EXECUTING;
- EXECUTING → COMPLETED on successful action;
- EXECUTING → RECONCILING after ambiguous action result;
- RECONCILING → RECOVERING for retryable failure;
- RECOVERING → EXECUTING for bounded retry;
- escalation path;
- invalid transition rejection;
- UNKNOWN != SUCCEEDED.

## 6. Evidence

Create:

`results/mvp/MVP-002.json`

Include transition-test counts and status.

## 7. Exit Criteria

- [ ] finite mission transition table implemented;
- [ ] action lifecycle implemented;
- [ ] reconciliation semantics explicit;
- [ ] invalid transitions rejected;
- [ ] one HITL/escalation state supported;
- [ ] tests pass;
- [ ] evidence generated.

## 8. Commit

`feat(mvp): define durable mission and action state model`

Do not start MVP-003.
