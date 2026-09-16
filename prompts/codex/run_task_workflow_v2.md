# Single TASK Orchestration — Host-side Entry Point

## Purpose

The complete TASK lifecycle is executed by the **host-side Python orchestrator**.
This file documents the canonical entry point; it must not start nested Codex
workers from inside an existing Codex-managed session.

For:

```text
Run TASK-SIM-004
```

run from a normal VS Code/WSL terminal:

```bash
python3 scripts/codex/run_task_orchestrator.py task TASK-SIM-004
```

or:

```bash
scripts/codex/run-task TASK-SIM-004
```

## Lifecycle

```text
IMPLEMENT
  COMPLETE   -> REVIEW
  INCOMPLETE -> STOP + final report

REVIEW
  ACCEPT/REJECT -> review-boundary commit
  REJECT        -> FIX
  ACCEPT        -> RECORD_ACCEPTANCE

FIX
  READY_FOR_RE_REVIEW     -> RE_REVIEW
  NOT_READY_FOR_RE_REVIEW -> STOP + final report

RE_REVIEW
  ACCEPT/REJECT -> fix/re-review commit
  REJECT        -> STOP + final report
  ACCEPT        -> RECORD_ACCEPTANCE

RECORD_ACCEPTANCE
  RECORDED -> acceptance commit -> ACCEPTED
  FAILED   -> STOP + final report
```

## Console / Logs

Default terminal output is intentionally compact:

```text
START / WAIT / PASS / REJECT / COMMIT / FAIL / STOP / DONE
```

Full child output is stored outside the repository under:

```text
${XDG_STATE_HOME:-~/.local/state}/codex-task-orchestrator/
```

Every run writes:

```text
summary.md
run_report.json
<stage>.log
<stage>_final.txt
```

Use `--verbose` only when the full child stream is needed.
