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


# Child Dispatch Protocol Update

## Why this update exists

A host-run child must never interpret itself as the parent `Run TASK-*` session.
Every child is now explicitly marked with:

```text
ORCHESTRATOR_CHILD
protocol_version=1
worker_role=...
task_id=...
```

This fixes the failure mode where a child returned:

```text
Run this from a normal terminal:
python3 scripts/codex/run_task_orchestrator.py task TASK-SIM-004
```

instead of executing its worker stage.

## Verify installation

From repository root:

```bash
grep -n "ORCHESTRATOR_CHILD" \
  AGENTS.md \
  scripts/codex/run_task_orchestrator.py \
  prompts/codex/implement_task_v2.md \
  prompts/codex/read_only_review_v2.md \
  prompts/codex/fix_review_findings_v2.md \
  prompts/codex/record_task_acceptance_v2.md
```

All files should return matches.

Run tests:

```bash
cd scripts/codex
python3 test_run_task_orchestrator.py
```

## Normal execution

Use the host terminal only:

```bash
python3 scripts/codex/run_task_orchestrator.py task TASK-SIM-004
```

or:

```bash
scripts/codex/run-task TASK-SIM-004
```

Do not type `Run TASK-SIM-004` inside a Codex chat for lifecycle automation.

## Dispatch audit

For every child stage the runner now saves the exact child prompt:

```text
~/.local/state/codex-task-orchestrator/<repo>/<run>/
  01_TASK-SIM-004_implementation_prompt.txt
  01_TASK-SIM-004_implementation.log
  01_TASK-SIM-004_implementation_final.txt
```

If a child routes incorrectly, inspect the `_prompt.txt` file first.


# Checkpointed Resume

## Normal interruption recovery

If a child stops because of token/context/runtime limits, do **not** delete the
dirty worktree and do not restart the full TASK.

Inspect the latest report:

```bash
scripts/codex/show-last-run
```

Then resume:

```bash
scripts/codex/resume-task TASK-SIM-004
```

Equivalent:

```bash
python3 scripts/codex/run_task_orchestrator.py resume TASK-SIM-004
```

The runner loads:

```text
~/.local/state/codex-task-orchestrator/<repo>/resume_TASK-SIM-004.json
```

and continues exactly the checkpointed phase.

Examples:

```text
interrupted during Implementation -> resume Implementation only
Implementation complete, Review interrupted -> resume Review
REJECT committed, Fix interrupted -> resume Fix
Fix complete, Re-review interrupted -> resume Re-review
ACCEPT snapshot committed, Acceptance interrupted -> resume Acceptance
```

A fresh child Codex context is used on resume, so the exhausted token context is
not reused.

## Manual fresh-session prompt

Every nonterminal report also attempts to write:

```text
resume_prompt.txt
```

inside the external run directory. It is a ready-to-paste
`ORCHESTRATOR_CHILD ... resume=true` prompt for the interrupted worker stage.

Use this only as a fallback when host-side resume is unavailable.

## Older runs without checkpoint support

After verifying branch/HEAD/worktree provenance:

```bash
python3 scripts/codex/run_task_orchestrator.py resume TASK-SIM-004 \
  --from-stage implementation
```

Allowed stages:

```text
implementation
review
fix
rereview
acceptance
```

`--force` bypasses branch/HEAD mismatch protection and should be used only after
manual provenance verification.


## `resume-task` wrapper options

The wrapper accepts resume-subcommand options:

```bash
scripts/codex/resume-task TASK-SIM-004 --from-stage implementation
scripts/codex/resume-task TASK-SIM-004 --force
```

For global orchestrator options such as `--report-dir` or `--max-fix-cycles`,
use the Python entry point directly and place global options before `resume`:

```bash
python3 scripts/codex/run_task_orchestrator.py \
  --max-fix-cycles 2 \
  resume TASK-SIM-004
```
