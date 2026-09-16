# TASK Range Orchestrator v2

## Purpose

Run a sequential TASK range using one isolated lifecycle per TASK.

Typical command:

```text
Run TASK-SIM-002..TASK-SIM-004
```

This prompt manages TASK ordering and stop conditions only.

Do not implement, review, fix, record acceptance, inspect TASK specifications,
or inspect project sources in the current context.

---

## 1. Execution

Extract:

```text
START_TASK_ID
END_TASK_ID
```

The range must:

- use the same TASK prefix;
- use numeric suffixes;
- be ascending.

Run:

```bash
python3 scripts/codex/run_task_orchestrator.py range <START_TASK_ID> <END_TASK_ID>
```

Example:

```bash
python3 scripts/codex/run_task_orchestrator.py range TASK-SIM-002 TASK-SIM-004
```

---

## 2. Upper State Machine

For each TASK in order:

```text
RUN TASK
   |
   +-- ACCEPTED
   |   + accepted snapshot commit
   |   + acceptance JSON recorded
   |   + acceptance commit succeeded
   |   + clean worktree
   |      -> next TASK
   |
   +-- any other terminal result
          -> STOP RANGE
```

A downstream TASK must never run before the immediately preceding TASK reaches
the complete `ACCEPTED` state.

---

## 3. Commit Barrier

Before the next TASK starts, all conditions must be true:

```text
1. preceding TASK Review == ACCEPT
2. reviewed snapshot commit succeeded
3. acceptance JSON was recorded for that exact accepted commit
4. acceptance-record commit succeeded
5. Git worktree == clean
```

If any condition fails, stop the range.

---

## 4. Context Isolation

Each TASK lifecycle must be independent.

Do not pass the previous TASK's:

- TASK specification;
- source context;
- test output;
- Review report;
- Evidence;
- History;
- acceptance JSON body

into the next TASK context.

Only compact terminal state and commit IDs may cross the TASK boundary.

---

## 5. Project-management Context

Do not load by default:

```text
context/current_project_state.md
context/task_mapping.md
```

The explicit range supplied by the user is the execution plan.

Project-state synchronization should occur separately after the range completes
or stops.

---

## 6. Failure / Stop Rule

Stop immediately when a TASK returns anything other than:

```text
ACCEPTED
```

Do not skip failed TASKs.

Do not execute downstream TASKs speculatively.

---

## 7. Result

Return a concise range summary:

- accepted TASKs;
- reviewed snapshot commits;
- acceptance record commits;
- stopping TASK, if any;
- terminal status;
- next unexecuted TASK, if any.

Do not reproduce child workflow reports.
