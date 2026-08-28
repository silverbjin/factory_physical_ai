# TASK-MVP-006 — Canonical Normal End-to-End Mission

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Execute the **single canonical mission** end-to-end with no injected failure.

Mission:

> `Line B에 Brake ECU Type-B 1개를 공급해줘.`

## 2. Required E2E path

```text
Operator text
  ↓
Factory Agent
  ↓
Structured Mission
  ↓
Deterministic Runtime
  ↓
WMS Fake → Rack A19
  ↓
Robot Skill Fake
  ↓
Mission COMPLETED
  ↓
SQLite + Evidence
```

## 3. Required assertions

- parsed part = Brake ECU Type-B;
- quantity = 1;
- destination = Line B;
- inventory source = Rack A19;
- exactly one logical transfer executes;
- mission ends COMPLETED;
- timeout_detected = false;
- retry_count = 0;
- evidence can reconstruct the run.

## 4. Output

Create:

`results/mvp/normal_e2e/latest.json`

and task evidence:

`results/mvp/MVP-006.json`

Never hard-code fabricated performance statistics into documentation.

## 5. Exit Criteria

- [ ] normal mission passes from text input through evidence output;
- [ ] no failure fixture is enabled;
- [ ] one transfer only;
- [ ] final state COMPLETED;
- [ ] regression tests from MVP-001~005 pass.

## 6. Commit

`test(mvp): validate canonical normal end-to-end mission`

Do not start MVP-007.
