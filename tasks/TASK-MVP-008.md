# TASK-MVP-008 — Day-10 Portfolio Release

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Package the frozen Day-10 MVP into a reproducible portfolio release without expanding feature scope.

The release message is:

> One manufacturing mission, one ambiguous robot-skill failure, one deterministic recovery, and machine-readable evidence.

## 2. Required deliverables

Create/update only the minimum documentation/scripts required for a reviewer to reproduce:

1. normal mission;
2. single-failure recovery mission;
3. evidence inspection.

Recommended:

```text
README.md
docs/mvp/day10_mvp.md
scripts/run_mvp_normal.*
scripts/run_mvp_failure.*
scripts/verify_mvp_evidence.*
results/mvp/release/
```

Use existing project conventions.

## 3. README / demo content

Must explain:

- automotive line-side logistics business scenario;
- architecture boundary:
  Agent → Deterministic Runtime → typed fake tools;
- why Nav2/MoveIt/VLA are intentionally mocked for Day-10;
- canonical mission;
- canonical timeout/reconciliation/recovery;
- evidence files;
- limitations;
- next steps: VLA readiness/fine-tuning and later ROS integration.

Do not claim:

- physical robot validation;
- VLA fine-tuning;
- real WMS/MES/PHM;
- production deployment;
- multi-day soak;
- real hosted Agent behavior unless its separate gate passed.

## 4. Release verification

Run:

- full MVP test suite;
- normal E2E;
- single failure E2E;
- evidence parser/validator;
- `git diff --check`.

Create:

`results/mvp/release/day10_release.json`

At minimum include:

```text
release_status
canonical_mission_passed
single_failure_passed
recovery_passed
evidence_valid
test_count
test_passed
test_failed
git_commit
known_limitations
```

Populate only measured values.

## 5. Exit Criteria

- [ ] normal path reproducible;
- [ ] failure/recovery reproducible;
- [ ] evidence validator passes;
- [ ] README clearly states scope and limitations;
- [ ] no out-of-scope feature was added;
- [ ] full regression passes;
- [ ] release evidence exists.

## 6. Commit

`docs(mvp): publish day-10 physical AI portfolio release`

Optional tag after commit and clean verification:

`day10-mvp-v0.1.0`

Do not begin VLA or ROS integration work in this task.
