# TASK-MVP-007 — Canonical Single-Failure Recovery End-to-End

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Execute the same canonical mission with the **single frozen failure** enabled and prove one bounded recovery.

Do not introduce inventory mismatch, PHM, navigation blockage, VLA grasp failure, or other additional failure scenarios.

## 2. Required E2E failure sequence

```text
Mission starts
  ↓
WMS Fake success
  ↓
Robot Skill attempt #1
  ↓
TIMEOUT
  ↓
UNKNOWN
  ↓
RECONCILING
  ↓
typed action status = FAILED / retryable
  ↓
RECOVERING
  ↓
Robot Skill attempt #2
  ↓
SUCCEEDED
  ↓
COMPLETED
```

## 3. Required evidence assertions

- timeout_detected = true;
- reconciliation_performed = true;
- retry_budget = 1;
- retry_count = 1;
- recovery_result = success;
- mission_result = completed;
- action IDs and logical operation are correlated;
- no extra execution occurs;
- all transitions are persisted.

## 4. Regression

Run all MVP-001~006 tests plus this E2E recovery scenario.

## 5. Output

Create:

`results/mvp/failure_recovery/latest.json`

and:

`results/mvp/MVP-007.json`

## 6. Exit Criteria

- [ ] exactly one failure injected;
- [ ] exactly one recovery attempt;
- [ ] reconciliation precedes retry;
- [ ] final mission completes;
- [ ] evidence proves the sequence;
- [ ] all previous regression tests pass.

## 7. Commit

`test(mvp): validate single-failure recovery end to end`

Do not start MVP-008.
