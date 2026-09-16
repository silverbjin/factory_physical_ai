# Resume Interrupted TASK Workflow v2

## Purpose

Describe the safe continuation contract for a TASK whose host-side orchestration
was interrupted by token/context/runtime limits.

This is a **host-side resume workflow**. Do not launch the Python orchestrator
from inside a Codex-managed chat.

Canonical command:

```bash
scripts/codex/resume-task <TASK_ID>
```

Equivalent:

```bash
python3 scripts/codex/run_task_orchestrator.py resume <TASK_ID>
```

The runner reads the persistent external checkpoint and restarts exactly the
interrupted phase in a fresh bounded child context.

## Manual fresh-session fallback

The latest run directory may contain:

```text
resume_prompt.txt
```

That file is a ready-to-paste `ORCHESTRATOR_CHILD` prompt for the interrupted
worker stage. Use it only when host-side `resume` cannot be used.

Manual worker continuation does not by itself complete the full lifecycle.
After the worker finishes, return to host-side orchestration so Review/commit/
Acceptance boundaries remain authoritative.

## Older runs without a checkpoint

After manually verifying the current branch, HEAD, worktree, history, and TASK
state, bootstrap a resume stage:

```bash
python3 scripts/codex/run_task_orchestrator.py resume <TASK_ID> \
  --from-stage implementation
```

Allowed manual stages:

```text
implementation
review
fix
rereview
acceptance
```

Never discard target-task work merely to obtain a clean worktree.
