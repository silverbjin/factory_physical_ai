# TASK-MVP-004 — Single Failure and Bounded Recovery

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Implement exactly **one** MVP failure scenario:

> Robot Skill execution times out, leaving the physical result ambiguous.

Then prove deterministic reconciliation and bounded recovery.

Do not add additional portfolio failure scenarios in this task.

## 2. Canonical failure path

```text
Robot Skill request
      ↓
TIMEOUT
      ↓
Action = UNKNOWN
      ↓
Mission = RECONCILING
      ↓
get_action_status(action_id)
      ↓
FAILED + retryable=true
      ↓
Mission = RECOVERING
      ↓
one bounded retry
      ↓
SUCCEEDED
      ↓
Mission = COMPLETED
```

The fixture must deterministically inject timeout on the first attempt and success after the approved recovery path.

## 3. Policy constraints

- retry budget = 1 for the MVP scenario;
- LLM must not choose the physical outcome;
- timeout must never be treated as immediate failure or success;
- reconciliation is mandatory before retry;
- retry must be traceable to the same mission/logical operation;
- no unbounded loops;
- if recovery budget is exhausted, escalate/fail deterministically.

## 4. Tests

At minimum:

1. timeout creates UNKNOWN action state;
2. mission enters RECONCILING;
3. status query occurs before retry;
4. retryability is read from typed result;
5. exactly one retry occurs;
6. retry succeeds and mission completes;
7. retry budget cannot exceed one;
8. non-retryable reconciliation result escalates;
9. Agent cannot override runtime policy.

## 5. Evidence

Create:

`results/mvp/MVP-004.json`

Evidence must include state sequence and measured retry count from the test run.

## 6. Exit Criteria

- [ ] one failure only is implemented;
- [ ] UNKNOWN/reconciliation is observable;
- [ ] retry is bounded;
- [ ] final result is deterministic;
- [ ] no duplicate/unbounded execution;
- [ ] tests pass.

## 7. Commit

`feat(mvp): implement timeout reconciliation and bounded recovery`

Do not start MVP-005.
