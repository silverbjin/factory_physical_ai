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


## Child Worker Dispatch

The host runner never sends a bare `Implement`, bare TASK ID, or `Fix` command to a
child as the complete child prompt.

Every child begins with the explicit envelope:

```text
ORCHESTRATOR_CHILD
protocol_version=1
worker_role=<implementation|review|rereview|fix|acceptance>
task_id=<TASK_ID>
worker_prompt=<prompt path>
```

Acceptance also includes:

```text
accepted_commit=<COMMIT>
```

This prevents a child from confusing itself with the host-side `Run ...` entry point.

The exact child envelope for every stage is persisted beside its stage log as:

```text
<stage>_prompt.txt
```


## Interruption / Resume

If a child stops because of token/context/runtime limits, preserve the worktree
and use the host-side checkpointed resume command:

```bash
scripts/codex/resume-task <TASK_ID>
```

Do not restart the TASK from Implementation unless the checkpoint phase is
`implementation`.
