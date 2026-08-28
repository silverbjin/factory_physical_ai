# MVP Task Automation Prompt

## Purpose

This file defines the automated orchestration workflow for the Day-10 MVP task sequence.

The MVP task range is fixed to:

```text
TASK-MVP-001
TASK-MVP-002
TASK-MVP-003
TASK-MVP-004
TASK-MVP-005
TASK-MVP-006
TASK-MVP-007
TASK-MVP-008
```

The workflow must process these tasks in numeric order and must not advance to the next task until the current task has been independently accepted.

Typical invocation:

```text
Run MVP
```

---

## 1. Required Workflow Files

Before doing anything else, read:

```text
AGENTS.md
prompts/codex/implement_task.md
prompts/codex/read_only_review.md
prompts/codex/fix_review_findings.md
prompts/codex/task_history_recording.md
```

Also discover and read any more specific `AGENTS.md` files that apply to the repository paths involved.

If any required workflow file is missing or unreadable, stop immediately and report:

```text
MVP AUTOMATION BLOCKED
```

Do not improvise missing workflow rules.

---

## 2. MVP Task Set

The only tasks controlled by this automation are:

```text
TASK-MVP-001
TASK-MVP-002
TASK-MVP-003
TASK-MVP-004
TASK-MVP-005
TASK-MVP-006
TASK-MVP-007
TASK-MVP-008
```

Do not start:

- TASK-MVP-009 or later;
- Week tasks;
- unrelated backlog work;
- future-phase implementation.

The automation is complete only when every task from `TASK-MVP-001` through `TASK-MVP-008` has an independent final `ACCEPT` result.

---

## 3. Resume-first Behavior

This workflow must be resumable.

Before implementing or reviewing anything, inspect:

```text
docs/task_history/README.md
docs/task_history/TASK-MVP-001/
...
docs/task_history/TASK-MVP-008/
```

Also inspect actual task evidence, Git state, and task specifications as needed.

For each MVP task, determine one workflow state:

```text
NOT STARTED
IMPLEMENTED / REVIEW PENDING
REJECTED / FIX REQUIRED
FIXED / RE-REVIEW PENDING
ACCEPTED
BLOCKED
```

Do not trust only the global history index.

Confirm important status from the latest per-task history record and current repository state.

### Resume rule

Start from the earliest task in numeric order whose state is not `ACCEPTED`.

Examples:

```text
001 ACCEPTED
002 ACCEPTED
003 IMPLEMENTED / REVIEW PENDING
```

Start with review of `TASK-MVP-003`.

```text
001 ACCEPTED
002 REJECTED / FIX REQUIRED
```

Start with Fix for `TASK-MVP-002`.

```text
001 ACCEPTED
002 FIXED / RE-REVIEW PENDING
```

Start with re-review of `TASK-MVP-002`.

```text
001 ACCEPTED
002 ACCEPTED
003 NOT STARTED
```

Start with implementation of `TASK-MVP-003`.

Never re-implement an already accepted task merely because this automation is restarted.

---

## 4. Core State Machine

For every `TASK_ID`, use this workflow:

```text
NOT STARTED
    ↓
IMPLEMENT
    ↓
IMPLEMENTED / REVIEW PENDING
    ↓
INDEPENDENT READ-ONLY REVIEW
    ├── ACCEPT → ACCEPTED → NEXT TASK
    └── REJECT
            ↓
       FIX REQUIRED
            ↓
           FIX
            ↓
       RE-REVIEW PENDING
            ↓
       INDEPENDENT READ-ONLY RE-REVIEW
            ├── ACCEPT → ACCEPTED → NEXT TASK
            └── REJECT → FIX again
```

The current task must reach:

```text
ACCEPTED
```

before the next numeric MVP task is started.

---

## 5. Implementation Phase

When the current task state is `NOT STARTED`, execute the behavior defined by:

```text
prompts/codex/implement_task.md
```

as though the user had issued:

```text
Implement <TASK_ID>
```

Requirements:

- follow the implementation prompt in full;
- verify prerequisites;
- implement only the current `TASK_ID`;
- run focused tests and required regression;
- evaluate Exit Criteria;
- generate/update Evidence;
- create and verify TASK history;
- do not commit or stage unless explicitly authorized elsewhere;
- do not start the next task inside the implementation phase.

The Implementation phase succeeds only when the workflow result is:

```text
<TASK_ID> is complete.
```

If implementation returns:

```text
<TASK_ID> is NOT complete.
```

stop the MVP automation at that task and report the blockers.

Do not automatically reinterpret an incomplete implementation as a reviewable task.

---

## 6. Independent Read-only Review Phase

After successful implementation, execute:

```text
prompts/codex/read_only_review.md
```

for the same `TASK_ID`.

Treat this as a separate reviewer role.

The reviewer must:

- judge frozen specification against current repository state;
- not reuse the implementer's self-assessment as proof;
- rerun or independently verify required tests/evidence;
- produce Requirement Traceability;
- classify findings;
- evaluate Acceptance Gates;
- persist review history according to the configured audit-log exception.

### Reviewer independence

If the execution environment supports isolated subagents, fresh agent contexts, or separate Codex executions, use a fresh review context.

If true execution isolation is unavailable, enforce logical independence:

1. stop using implementation rationale as evidence;
2. reread frozen task/contract sources;
3. independently inspect current source/tests/evidence;
4. treat implementation history only as an audit record, never as a source of truth.

Do not modify implementation files during Review.

---

## 7. ACCEPT Branch

If Review returns:

```text
ACCEPT <TASK_ID>
```

then:

1. verify the review history file was created;
2. verify the per-TASK README reflects `ACCEPT`;
3. verify `docs/task_history/README.md` reflects `ACCEPTED`;
4. mark the current automation state `ACCEPTED`;
5. advance to the next numeric MVP task.

Do not run Fix for an accepted task.

For `TASK-MVP-008`, an `ACCEPT` result completes the MVP task automation.

---

## 8. REJECT Branch

If Review returns:

```text
REJECT <TASK_ID>
```

do not advance.

Execute:

```text
prompts/codex/fix_review_findings.md
```

as though the user had issued:

```text
Fix <TASK_ID>
```

The Fix phase must:

- independently reproduce relevant findings;
- fix BLOCKER findings;
- fix HIGH findings;
- fix MEDIUM findings that keep Acceptance Gates at FAIL;
- not fix LOW findings by default;
- not expand into later-task scope;
- add/strengthen regression tests;
- rerun required validation;
- update truthful Evidence;
- persist and verify Fix history.

Fix succeeds only when it returns:

```text
<TASK_ID> fixes are ready for independent re-review.
```

Then perform another independent Read-only Review of the same `TASK_ID`.

---

## 9. Fix / Re-review Loop

Repeat:

```text
Review
  ↓ REJECT
Fix
  ↓
Re-review
```

until one of the following occurs.

### Success

```text
ACCEPT <TASK_ID>
```

Then advance.

### Blocking condition

Stop automation if any of these occurs:

- a Fix returns `NOT ready for independent re-review`;
- a mandatory prerequisite cannot be satisfied;
- a frozen requirement conflict cannot be resolved;
- required tests cannot be made to pass within target-task scope;
- evidence cannot be made truthful within target-task scope;
- `HISTORY ACTION REQUIRED` is reported and acceptance depends on user authorization;
- repository state indicates unsafe unrelated user changes would need to be overwritten;
- required workflow/history files cannot be written;
- scope expansion into a later task would be necessary.

### Loop safety

Do not enter an unbounded Fix/Review loop.

Allow at most:

```text
3 Fix cycles per TASK_ID
```

within one `Run MVP` invocation.

A Fix cycle is:

```text
REJECT → Fix → Re-review
```

If the third re-review still returns `REJECT`, stop and report:

```text
MVP AUTOMATION NEEDS MANUAL DECISION
```

Include the remaining findings and do not start the next task.

A later `Run MVP` invocation may resume after the user resolves the issue.

---

## 10. Git-history Actions

Never automatically perform:

```text
git commit --amend
git rebase
git reset
git push --force
```

or other history rewrites.

If a Review/Fix reports:

```text
HISTORY ACTION REQUIRED
```

and acceptance depends on it:

1. stop the current TASK;
2. do not start the next TASK;
3. report the exact commit and required action;
4. wait for explicit user authorization in a later command.

Normal commits are also not created unless explicitly authorized by repository policy or user instruction.

---

## 11. TASK History Requirements

Every executed workflow stage must persist its history through:

```text
prompts/codex/task_history_recording.md
```

Expected pattern:

```text
docs/task_history/<TASK_ID>/
├── README.md
├── 01_implementation.md
├── 02_review.md
├── 03_fix.md
├── 04_review.md
└── ...
```

Exact sequence numbers depend on existing history.

Never overwrite an earlier entry.

For each current TASK, the latest status in:

```text
docs/task_history/<TASK_ID>/README.md
```

and:

```text
docs/task_history/README.md
```

must agree with the actual latest workflow result.

Do not mark a TASK `ACCEPTED` until independent Review returns `ACCEPT`.

---

## 12. Repository Safety Between Tasks

Before advancing from an accepted task to the next task:

1. inspect:

```bash
git status --short
git diff --stat
git diff --check
```

2. distinguish:
   - expected implementation/test/evidence changes;
   - expected `docs/task_history/` audit changes;
   - unrelated user changes.

3. verify the next task's prerequisites can be evaluated without overwriting unrelated work.

Do not clean, reset, stash, restore, or discard user changes automatically.

If the next task cannot safely proceed because of repository state, stop and report the reason.

---

## 13. Progress Updates

At the start of each TASK, report one concise line:

```text
[MVP] TASK-MVP-003 — starting Implementation
```

or:

```text
[MVP] TASK-MVP-003 — starting Read-only Review
```

or:

```text
[MVP] TASK-MVP-003 — starting Fix cycle 1
```

At each Review result:

```text
[MVP] TASK-MVP-003 — ACCEPT
```

or:

```text
[MVP] TASK-MVP-003 — REJECT (BLOCKER 1, HIGH 0, MEDIUM 1)
```

Do not dump the full history summary between every internal step unless needed.

The detailed reports still follow the underlying workflow prompts and are persisted in `docs/task_history/`.

---

## 14. Automation Summary Table

Maintain an in-memory summary while running.

At completion or stop, report:

| TASK | Final state | Implementation | Reviews | Fixes | Latest result |
|---|---|---:|---:|---:|---|
| TASK-MVP-001 | ACCEPTED | ... | ... | ... | ACCEPT |
| ... | ... | ... | ... | ... | ... |

Use repository history to populate already completed tasks and current-run results for newly processed tasks.

---

## 15. Successful MVP Completion

The MVP automation is successful only when all eight tasks are independently accepted:

```text
TASK-MVP-001 — ACCEPTED
TASK-MVP-002 — ACCEPTED
TASK-MVP-003 — ACCEPTED
TASK-MVP-004 — ACCEPTED
TASK-MVP-005 — ACCEPTED
TASK-MVP-006 — ACCEPTED
TASK-MVP-007 — ACCEPTED
TASK-MVP-008 — ACCEPTED
```

Then report exactly:

```text
MVP TASK AUTOMATION COMPLETE
```

Also report:

- total tasks accepted;
- total review attempts;
- total Fix cycles;
- any deferred non-blocking MEDIUM/LOW findings;
- location of the global TASK history index;
- next recommended action, without starting Week tasks.

Do not automatically begin Week 1.

---

## 16. Stopped / Blocked Completion

If automation stops before all eight tasks are accepted, report:

```text
MVP TASK AUTOMATION STOPPED
```

Then include:

- current `TASK_ID`;
- current workflow state;
- last Review/Fix result;
- unresolved BLOCKER/HIGH/MEDIUM findings;
- whether `HISTORY ACTION REQUIRED`;
- exact user decision or external prerequisite needed;
- confirmation that later MVP tasks were not started.

Do not skip a blocked task.

---

## 17. Final Constraints

Remember:

- process TASK-MVP-001 through TASK-MVP-008 only;
- always use numeric order;
- resume from the earliest non-accepted task;
- do not re-implement accepted tasks;
- implementation must complete before review;
- every task requires independent `ACCEPT` before advancement;
- `REJECT` always routes to Fix for the same task;
- Fix is followed by independent re-review;
- maximum three Fix cycles per task per automation invocation;
- no next-task implementation while the current task is unresolved;
- no Git-history rewriting without explicit approval;
- no Week task implementation;
- preserve unrelated user work;
- persist Implementation / Review / Fix history;
- TASK history is portfolio/audit material, not a substitute for technical Evidence;
- do not claim MVP completion unless all eight tasks are independently accepted.

Begin the resumable MVP automation now.
