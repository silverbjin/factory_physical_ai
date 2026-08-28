# MVP Commit Guide

## Principle

Use **one validated task = one primary commit**.

Commit only after the task Exit Criteria and regression checks pass. Do not create a “progress commit” on the main branch merely because Codex stopped mid-task.

## Recommended commits

| Task | Commit |
|---|---|
| P0-002 | `docs(arch): freeze architecture v1.0 and day-10 MVP scope` |
| MVP-001 | `feat(mvp): establish factory agent vertical slice` |
| MVP-002 | `feat(mvp): define durable mission and action state model` |
| MVP-003 | `feat(mvp): add deterministic factory tool gateway and skill fakes` |
| MVP-004 | `feat(mvp): implement timeout reconciliation and bounded recovery` |
| MVP-005 | `feat(mvp): persist mission lifecycle and structured evidence` |
| MVP-006 | `test(mvp): validate canonical normal end-to-end mission` |
| MVP-007 | `test(mvp): validate single-failure recovery end to end` |
| MVP-008 | `docs(mvp): publish day-10 physical AI portfolio release` |

## Commit types

- `docs(arch)` — architecture/ADR/contract freezes.
- `feat(mvp)` — executable MVP capability.
- `test(mvp)` — E2E validation/evidence rather than a new product feature.
- `fix(mvp)` — a defect discovered after a task commit.
- `refactor(mvp)` — behavior-preserving cleanup only.
- `chore(mvp)` — tooling/configuration with no runtime behavior.
- `docs(mvp)` — portfolio/release documentation.

## Fix commits

If MVP-004 reveals a defect in MVP-002, do not rewrite the historical commit after it is already shared. Use:

`fix(mvp): reject invalid transition after reconciliation timeout`

Then return to the active task and re-run regression.

## Before every primary commit

```bash
git status
git diff
git diff --check
# run task-specific tests
# run required regression tests
```

Then:

```bash
git add <only task-related files>
git commit -m "<task commit message>"
```

Avoid `git add .` if unrelated files are present.

## Tag

Only after MVP-008 and clean release verification:

```bash
git tag -a day10-mvp-v0.1.0 -m "Day-10 MVP: one mission, one failure, one recovery, evidence"
```

Do not tag intermediate tasks.

## Recommended history

```text
docs(arch): freeze architecture v1.0 and day-10 MVP scope
feat(mvp): establish factory agent vertical slice
feat(mvp): define durable mission and action state model
feat(mvp): add deterministic factory tool gateway and skill fakes
feat(mvp): implement timeout reconciliation and bounded recovery
feat(mvp): persist mission lifecycle and structured evidence
test(mvp): validate canonical normal end-to-end mission
test(mvp): validate single-failure recovery end to end
docs(mvp): publish day-10 physical AI portfolio release
```

This history should read like the engineering story of the portfolio.
