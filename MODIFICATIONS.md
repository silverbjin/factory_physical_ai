# Updated Files

This bundle is a complete replacement/update set for the quiet-reporting architecture.

## Replace/update

```text
AGENTS.md
config/codex_model_policy.json
prompts/codex/implement_task_v2.md
prompts/codex/read_only_review_v2.md
prompts/codex/fix_review_findings_v2.md
prompts/codex/record_task_acceptance_v2.md
prompts/codex/run_task_workflow_v2.md
prompts/codex/run_task_range_v2.md
scripts/codex/run_task_orchestrator.py
scripts/codex/test_run_task_orchestrator.py
```

## New convenience commands

```text
scripts/codex/run-task
scripts/codex/run-task-range
scripts/codex/show-last-run
```

## Important behavior change

`Run TASK-*` is no longer executed from inside a Codex chat session. The canonical entry point is a normal host/WSL terminal because the orchestrator launches nested `codex exec` workers and requires normal writable Codex state.

Default child stdout/stderr is redirected to persistent logs outside the repository. The terminal shows only compact progress/heartbeat/final summary output.


# Child Dispatch Protocol Changes

Updated files:

```text
AGENTS.md
scripts/codex/run_task_orchestrator.py
scripts/codex/test_run_task_orchestrator.py
prompts/codex/implement_task_v2.md
prompts/codex/read_only_review_v2.md
prompts/codex/fix_review_findings_v2.md
prompts/codex/record_task_acceptance_v2.md
prompts/codex/run_task_workflow_v2.md
prompts/codex/run_task_range_v2.md
USAGE.md
```

Unchanged because no protocol change is required:

```text
config/codex_model_policy.json
scripts/codex/run-task
scripts/codex/run-task-range
scripts/codex/show-last-run
```

The runner now saves every exact child prompt to the external run-report directory.


# Resume / Restart Support

Added:

```text
prompts/codex/resume_task_workflow_v2.md
scripts/codex/resume-task
```

Updated:

```text
AGENTS.md
scripts/codex/run_task_orchestrator.py
scripts/codex/test_run_task_orchestrator.py
prompts/codex/implement_task_v2.md
prompts/codex/read_only_review_v2.md
prompts/codex/fix_review_findings_v2.md
prompts/codex/record_task_acceptance_v2.md
prompts/codex/run_task_workflow_v2.md
prompts/codex/run_task_range_v2.md
USAGE.md
```

The runner now persists a per-TASK resume checkpoint outside the repository and
supports:

```bash
python3 scripts/codex/run_task_orchestrator.py resume <TASK_ID>
```

# First-run / KeyboardInterrupt Fix

Updated:

```text
scripts/codex/run_task_orchestrator.py
scripts/codex/test_run_task_orchestrator.py
USAGE.md
```

Changes:

- child Codex processes now run in their own process session;
- runner prints child PID, first-output activity, and a 10-second default heartbeat;
- `Ctrl+C` is converted into a structured `INTERRUPTED` result instead of a traceback;
- child process groups are cleaned up with SIGINT -> SIGTERM -> SIGKILL escalation;
- the active TASK checkpoint is marked interrupted even during range execution;
- final reports point to `scripts/codex/resume-task <TASK_ID>`;
- removed a stale unused acceptance helper that contained an incorrectly placed KeyboardInterrupt handler.


# Canonical Acceptance Path Fix

Acceptance manifests are now canonicalized to:

```text
results/reviews/<TASK_SHORT>_acceptance.json
```

Updated:

```text
prompts/codex/record_task_acceptance_v2.md
scripts/codex/run_task_orchestrator.py
scripts/codex/test_run_task_orchestrator.py
AGENTS.md
USAGE.md
```

Added:

```text
scripts/codex/migrate_acceptance_records.py
```
