# Single TASK Workflow Orchestrator v2

## Purpose

Run one TASK lifecycle while keeping Implementation, Review, Fix, Re-review,
and Acceptance recording in separate Codex contexts.

Typical command:

```text
Run TASK-SIM-002
```

This prompt is an orchestration dispatcher only.

Do not implement, review, fix, record acceptance, or inspect TASK sources in
the current context.

---

## 1. Execution

Extract exactly one `TASK_ID`.

Run:

```bash
python3 scripts/codex/run_task_orchestrator.py task <TASK_ID>
```

The external runner launches fresh Codex contexts for:

```text
Implement <TASK_ID>
<TASK_ID>
Fix <TASK_ID>
<TASK_ID>
Record <TASK_ID> acceptance for commit <ACCEPTED_COMMIT>
```

---

## 2. State Machine

```text
IMPLEMENT
  COMPLETE   -> REVIEW
  INCOMPLETE -> STOP

REVIEW
  workflow_complete=false -> STOP
  ACCEPT/REJECT -> COMMIT_IMPLEMENTATION_REVIEW

COMMIT_IMPLEMENTATION_REVIEW
  failure -> STOP
  REJECT  -> FIX
  ACCEPT  -> RECORD_ACCEPTANCE

FIX
  workflow_complete=false       -> STOP
  READY_FOR_RE_REVIEW           -> RE_REVIEW
  NOT_READY_FOR_RE_REVIEW       -> STOP

RE_REVIEW
  workflow_complete=false -> STOP
  ACCEPT/REJECT -> COMMIT_FIX_RE_REVIEW

COMMIT_FIX_RE_REVIEW
  failure -> STOP
  REJECT  -> STOP by default
  ACCEPT  -> RECORD_ACCEPTANCE

RECORD_ACCEPTANCE
  workflow_complete=false -> STOP
  RECORDED -> COMMIT_ACCEPTANCE

COMMIT_ACCEPTANCE
  failure -> STOP
  success -> ACCEPTED
```

Default maximum Fix cycles:

```text
1
```

Do not continue indefinitely after repeated REJECT results.

---

## 3. Git / Acceptance Boundary

Git staging and commits are owned exclusively by:

```text
scripts/codex/run_task_orchestrator.py
```

Child Codex contexts must never commit.

The accepted Review snapshot is committed BEFORE acceptance recording.

Therefore the acceptance JSON records a stable `accepted_commit` rather than an
uncommitted or moving worktree.

For an accepted TASK the normal Git sequence is:

```text
reviewed implementation/fix snapshot commit
→ acceptance JSON generation
→ acceptance JSON commit
```

---

## 4. Context Boundary

The current orchestration context must not load:

- `tasks/<TASK_ID>.md`;
- Required Sources;
- Conditional Sources;
- implementation files;
- tests;
- Evidence;
- TASK history;
- Review findings;
- acceptance JSON contents.

Those belong only to fresh child contexts started by the runner.

---

## 5. Completion Safety

A child stage may advance only when its final machine-readable marker contains:

```json
{"workflow_complete": true}
```

If it is false, stop without starting the next stage.

Acceptance recording must also prove:

```text
accepted_commit == current HEAD at recording start
```

and must create exactly one acceptance JSON.

---

## 6. Result

Return only the runner's concise TASK result.

Do not reconstruct child reports in this context.
