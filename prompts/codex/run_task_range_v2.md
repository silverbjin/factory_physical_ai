# TASK Range Orchestration — Host-side Entry Point

## Purpose

Run a sequential TASK range with a fresh bounded Codex context per worker and
stop downstream execution on the first non-ACCEPTED TASK.

Run from a normal VS Code/WSL terminal:

```bash
python3 scripts/codex/run_task_orchestrator.py range TASK-SIM-002 TASK-SIM-004
```

or:

```bash
scripts/codex/run-task-range TASK-SIM-002 TASK-SIM-004
```

## Range Gate

A downstream TASK starts only when the preceding TASK has all of:

```text
Review ACCEPT
+ accepted snapshot commit
+ acceptance JSON for that exact snapshot
+ acceptance-record commit
+ clean worktree
```

Any other terminal state stops the range and creates a final summary/report.

## Context Isolation

Do not pass the previous TASK's source context, tests, Review prose, Evidence body,
or History into the next TASK. Only compact terminal state/commit identifiers cross
the TASK boundary.

## Console / Logs

Default console output is compact. Full worker logs and final responses are stored
under `${XDG_STATE_HOME:-~/.local/state}/codex-task-orchestrator/`.


## Child Worker Dispatch

Each TASK lifecycle uses the same explicit `ORCHESTRATOR_CHILD` protocol as the
single-TASK runner. No previous TASK's worker context is reused.

Each stage prompt is persisted in the external run directory for dispatch auditing.
