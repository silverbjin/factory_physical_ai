# Codex TASK Orchestrator — Quiet Console + Persistent Run Reports

## 1. Canonical execution model

Run the orchestrator from a normal VS Code/WSL terminal, **not from inside a Codex chat session**.

```text
Host terminal
  → Python orchestrator
      → fresh Terra Implementation worker
      → fresh Sol Review worker
      → Git checkpoint
      → optional Terra Fix
      → optional Sol Re-review
      → Git checkpoint
      → Luna Acceptance worker
      → acceptance commit
```

This avoids nested-Codex `$CODEX_HOME` write restrictions and keeps every worker context isolated.

## 2. Install

Copy the bundle contents to repository root and make wrappers executable:

```bash
chmod +x scripts/codex/run_task_orchestrator.py \
  scripts/codex/run-task \
  scripts/codex/run-task-range \
  scripts/codex/show-last-run
```

Verify:

```bash
which codex
codex --version
git status --short
```

Use a dedicated branch/worktree. The worktree must be clean before a new automated run.

## 3. Single TASK

Recommended short command:

```bash
scripts/codex/run-task TASK-SIM-004
```

Equivalent:

```bash
python3 scripts/codex/run_task_orchestrator.py task TASK-SIM-004
```

Default console output is compact, for example:

```text
[15:31:02] RUN     TASK-SIM-004
[15:31:02] CHECK   branch=task/sim-004, worktree=CLEAN
[15:31:03] START   TASK-SIM-004 IMPLEMENTATION — gpt-5.6-terra / medium
[15:31:33] WAIT    TASK-SIM-004 IMPLEMENTATION still running (30s)
[15:34:19] STOP    TASK-SIM-004 IMPLEMENTATION — INCOMPLETE
[15:34:19] STOP    TASK-SIM-004 — INCOMPLETE
```

Full child output is **not** streamed by default.

## 4. Persistent reports

Every run writes outside the repository:

```text
${XDG_STATE_HOME:-~/.local/state}/codex-task-orchestrator/
└── <repo-name>/
    └── <timestamp>_<target>/
        ├── 01_TASK-SIM-004_implementation.log
        ├── 01_TASK-SIM-004_implementation_final.txt
        ├── ...
        ├── summary.md
        └── run_report.json
```

Therefore reporting itself never dirties the Git worktree.

Show the latest human-readable report:

```bash
scripts/codex/show-last-run
```

## 5. Failure report

At the end of a failed run the terminal prints:

```text
Errors:
  - [TECHNICAL] TASK-SIM-004:implementation: ...
  - [CHILD_PROTOCOL] ...   # when applicable

Next action: RESOLVE_IMPLEMENTATION_BLOCKER
  1. Inspect the failing Implementation final response and full log.
  2. Resolve the blocker and re-run focused validation.
  3. Reconcile the dirty worktree before a new automated run.

Summary: ~/.local/state/.../summary.md
Report:  ~/.local/state/.../run_report.json
```

`summary.md` separates technical failure from protocol/process/Git failure, so a passing test count cannot hide a task-specific blocker.

## 6. Useful options

Full child stream for debugging only. The wrapper accepts only the TASK ID, so for options use Python directly:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --verbose \
  task TASK-SIM-004
```

Change failure-tail lines:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --show-tail 30 \
  task TASK-SIM-004
```

Disable failure tail:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --show-tail 0 \
  task TASK-SIM-004
```

Heartbeat every 15 seconds:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --heartbeat-seconds 15 \
  task TASK-SIM-004
```

Custom report base:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --report-dir ~/codex-run-reports \
  task TASK-SIM-004
```

## 7. Range

```bash
scripts/codex/run-task-range TASK-SIM-002 TASK-SIM-004
```

The range stops at the first non-ACCEPTED TASK. Downstream TASKs are not started.

## 8. What to do after an INCOMPLETE/BLOCKED Implementation

Do **not** proceed to Review simply because focused tests passed.

Read:

```bash
scripts/codex/show-last-run

git status --short
```

Resolve the blocker identified under `Errors` / `Next Action`. The current runner intentionally does not auto-resume a dirty, incomplete worktree; reconcile/complete that implementation boundary first.

## 9. Unit tests

```bash
cd scripts/codex
python3 test_run_task_orchestrator.py
```
