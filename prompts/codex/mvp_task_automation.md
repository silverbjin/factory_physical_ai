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

The workflow must process these tasks in numeric order and must not advance to the next task until the current task has been independently accepted and its accepted snapshot has been committed.

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

The automation is complete only when every task from `TASK-MVP-001` through `TASK-MVP-008` has an independent final `ACCEPT` result and a verified normal Git commit.

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
ACCEPTED / COMMIT PENDING
COMMITTED
BLOCKED
```

Do not trust only the global history index.

Confirm important status from:

- the latest per-task history record;
- current repository state;
- task Evidence where relevant;
- Git history.

### Commit-state verification for resume

If the latest independent Review for a task is `ACCEPT`, determine whether that accepted snapshot has actually been committed.

Identify the latest accepted review history file, for example:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
```

Then inspect:

```bash
git status --short -- docs/task_history/<TASK_ID> docs/task_history/README.md
git log -1 --format=%H -- docs/task_history/<TASK_ID>/<SEQ>_review.md
```

Classify:

```text
ACCEPTED / COMMIT PENDING
```

when the accepted review/history or other task-owned accepted changes are still untracked, modified, staged but uncommitted, or otherwise not represented by the accepted task commit.

Classify:

```text
COMMITTED
```

only when:

1. the latest accepted review history file is tracked in Git history;
2. the accepted task-owned implementation/test/Evidence/history snapshot has no remaining uncommitted task-owned changes;
3. the corresponding commit can be identified and verified.

Do not classify a task as `COMMITTED` merely because the working tree is clean if the latest accepted review record is not present in Git history.

### Resume rule

Start from the earliest task in numeric order whose state is not `COMMITTED`.

Examples:

```text
001 COMMITTED
002 COMMITTED
003 IMPLEMENTED / REVIEW PENDING
```

Start with review of `TASK-MVP-003`.

```text
001 COMMITTED
002 REJECTED / FIX REQUIRED
```

Start with Fix for `TASK-MVP-002`.

```text
001 COMMITTED
002 FIXED / RE-REVIEW PENDING
```

Start with re-review of `TASK-MVP-002`.

```text
001 COMMITTED
002 COMMITTED
003 NOT STARTED
```

Start with implementation of `TASK-MVP-003`.

Never re-implement an already accepted or committed task merely because this automation is restarted.

If a task is already independently `ACCEPTED` but its accepted task changes have not yet been committed, classify it as:

```text
ACCEPTED / COMMIT PENDING
```

and perform only the commit phase before advancing.

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
            ├── ACCEPT → ACCEPTED / COMMIT PENDING
            └── REJECT → FIX again
                         ↓
                 TASK COMMIT
                         ↓
                    COMMITTED
                         ↓
                    NEXT TASK
```

The current task must reach:

```text
COMMITTED
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
3. verify `docs/task_history/README.md` reflects the accepted review state;
4. mark the task as `ACCEPTED / COMMIT PENDING`;
5. execute the Task Commit Phase defined below;
6. advance to the next numeric MVP task only after the commit succeeds.

Do not run Fix for an accepted task.

For `TASK-MVP-008`, an `ACCEPT` result does not by itself complete the MVP automation.
The final accepted TASK must also be committed successfully.

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

This MVP automation is explicitly authorized to create **one normal commit per successfully accepted TASK** using the Task Commit Phase below.

It is not authorized to amend, squash, rebase, reset, force-push, or otherwise rewrite existing history.

---

## 10.1 Task Commit Phase — Mandatory After ACCEPT

After an independent Review returns:

```text
ACCEPT <TASK_ID>
```

the task enters:

```text
ACCEPTED / COMMIT PENDING
```

Before starting the next task, create one normal Git commit for the accepted task.

### 10.1.1 Determine task-owned changes

Inspect:

```bash
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
```

Include tracked, staged, and untracked task-owned files in the ownership analysis.

Determine exactly which current working-tree changes belong to the accepted `TASK_ID`.

Use the Implementation / Fix reports, latest Review, Evidence, and TASK history to reconstruct the exact task-owned path set.

Task-owned changes normally include only:

- implementation files changed for `TASK_ID`;
- tests added or changed for `TASK_ID`;
- task Evidence under `results/` or the repository-defined evidence location;
- `docs/task_history/<TASK_ID>/` records generated by Implementation / Review / Fix / Re-review;
- the row or summary changes for `TASK_ID` in `docs/task_history/README.md`;
- other files explicitly required by the frozen task specification.

Do not include unrelated user changes.

Do not automatically include unrelated configuration, editor, cache, temporary, generated, or pre-existing untracked files.

### 10.1.2 Refuse ambiguous staging

If a file contains both:

- accepted `TASK_ID` changes; and
- unrelated user changes

and the task-owned hunks cannot be safely isolated without altering user work, stop and report:

```text
TASK COMMIT BLOCKED
```

Do not stage the whole file merely for convenience.

Do not use destructive commands to separate the changes.

### 10.1.3 Select the commit message

Use the recommended commit message produced by the accepted task workflow when it accurately represents the final accepted state.

Preference order:

1. the latest valid recommended commit message from the Implementation/Fix workflow that matches the final accepted changes;
2. if later Fix work materially changed the implementation and the earlier recommendation is stale, generate one concise Conventional Commit-style message from the final accepted task state;
3. do not use a review-only documentation message as the main task commit message when source/test changes are included.

Examples:

```text
feat(mvp): define durable mission and action state model
fix(mvp): enforce mission runtime invariants
feat(mvp): add deterministic mission gateway
```

The commit message must describe the final accepted TASK, not merely the latest Review action.

### 10.1.4 Stage only task-owned files

Before staging, inspect whether unrelated files are already staged.

If unrelated changes are already staged, do not commit them as part of the current TASK.

Safely unstage only unrelated staged paths with an index-only operation when doing so does not alter their working-tree contents, or stop with `TASK COMMIT BLOCKED` if ownership is ambiguous.

Do **not** use:

```bash
git add -A
git add .
```

unless the repository is proven to contain no unrelated changes and explicit repository policy requires it.

Prefer explicit path staging:

```bash
git add -- <task-owned-path-1> <task-owned-path-2> ...
```

When only selected hunks of a mixed file belong to the task, do not attempt interactive/destructive staging automatically unless the environment provides a safe non-destructive mechanism and the ownership is unambiguous.

### 10.1.5 Verify staged contents before commit

Run:

```bash
git diff --cached --stat
git diff --cached
git diff --cached --check
git status --short
```

Verify:

1. every staged change belongs to `TASK_ID`;
2. required implementation/test/Evidence/history files are included;
3. no unrelated user file is staged;
4. no later-task implementation is staged;
5. `git diff --cached --check` passes;
6. the latest accepted Review history file is staged;
7. the per-TASK history README and global history index changes for this TASK are staged when modified by this workflow;
8. no task-owned accepted change remains unstaged unless explicitly excluded by repository policy.

If verification fails, unstage only the incorrectly staged paths using a non-destructive index-only operation when safe, then re-evaluate.

Never discard working-tree changes.

### 10.1.6 Create the commit

If staged verification passes, first verify that the staged diff is non-empty:

```bash
git diff --cached --quiet
```

If there is no staged diff, do not create an empty commit.

Instead, determine whether the accepted task snapshot was already committed:

- if yes, identify that commit and mark the task `COMMITTED`;
- if no, stop with `TASK COMMIT BLOCKED`.

If a staged diff exists, run:

```bash
git commit -m "<RECOMMENDED_COMMIT_MESSAGE>"
```

Do not amend an existing commit.

If the commit fails, stop the automation and report the exact failure.

Do not start the next TASK.

### 10.1.7 Verify the commit

After commit, inspect:

```bash
git log -1 --oneline
git show --stat --oneline --summary HEAD
git status --short
```

Verify:

- a new commit was created, or an already-existing valid task commit was positively identified in the no-op case;
- its message matches the selected recommended message when a new commit was created;
- the commit contains only accepted task-owned changes;
- the latest accepted Review history file is included in that commit;
- unrelated user changes, if any, remain uncommitted and preserved.

Record:

```text
TASK_COMMIT_SHA
TASK_COMMIT_MESSAGE
```

Mark the task:

```text
COMMITTED
```

only after this verification passes.

### 10.1.8 TASK history commit metadata

After the commit is created, do not modify the committed source/test/Evidence merely to inject the new SHA.

If `task_history_recording.md` supports commit metadata that cannot be known until after commit, prefer one of these non-circular approaches:

1. keep the commit SHA in the automation final report and Git history only; or
2. update a later global portfolio summary in a future explicitly authorized documentation commit.

Do not create a second automatic commit for the same TASK solely to backfill its own commit SHA unless repository policy explicitly requires it.

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

Before advancing from a committed task to the next task:

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

3. verify the accepted task has a verified `TASK_COMMIT_SHA`;
4. verify the next task's prerequisites can be evaluated without overwriting unrelated work.

Do not clean, reset, stash, restore, or discard user changes automatically.

If the task has not been committed successfully, or the next task cannot safely proceed because of repository state, stop and report the reason.

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

At each Review result, report one of:

```text
[MVP] TASK-MVP-003 — ACCEPT
```

or:

```text
[MVP] TASK-MVP-003 — REJECT (BLOCKER 1, HIGH 0, MEDIUM 1)
```

After a successful accepted-task commit:

```text
[MVP] TASK-MVP-003 — COMMITTED <short-sha>
```

Do not dump the full history summary between every internal step unless needed.

The detailed reports still follow the underlying workflow prompts and are persisted in `docs/task_history/`.

---

## 14. Automation Summary Table

Maintain an in-memory summary while running.

At completion or stop, report:

| TASK | Final state | Implementation | Reviews | Fixes | Commit | Latest result |
|---|---|---:|---:|---:|---|---|
| TASK-MVP-001 | COMMITTED | ... | ... | ... | `<sha>` | ACCEPT |
| ... | ... | ... | ... | ... | ... |

Use TASK history plus Git history to populate already completed tasks and current-run results for newly processed tasks.

For each `COMMITTED` task, include the verified commit SHA and commit message.

---

## 15. Successful MVP Completion

The MVP automation is successful only when all eight tasks are independently accepted **and committed**:

```text
TASK-MVP-001 — COMMITTED
TASK-MVP-002 — COMMITTED
TASK-MVP-003 — COMMITTED
TASK-MVP-004 — COMMITTED
TASK-MVP-005 — COMMITTED
TASK-MVP-006 — COMMITTED
TASK-MVP-007 — COMMITTED
TASK-MVP-008 — COMMITTED
```

Then report exactly:

```text
MVP TASK AUTOMATION COMPLETE
```

Also report:

- total tasks accepted and committed;
- total review attempts;
- total Fix cycles;
- commit SHA and commit message for each TASK;
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
- last Review/Fix/Commit result;
- unresolved BLOCKER/HIGH/MEDIUM findings;
- whether `HISTORY ACTION REQUIRED`;
- whether `TASK COMMIT BLOCKED`;
- staged/uncommitted task-owned state when commit is the blocker;
- exact user decision or external prerequisite needed;
- confirmation that later MVP tasks were not started.

Do not skip a blocked task.

---

## 17. Final Constraints

Remember:

- process TASK-MVP-001 through TASK-MVP-008 only;
- always use numeric order;
- resume from the earliest non-committed task;
- do not re-implement accepted or committed tasks;
- implementation must complete before review;
- every task requires independent `ACCEPT` before commit;
- every accepted task requires one verified normal commit before advancement;
- `REJECT` always routes to Fix for the same task;
- Fix is followed by independent re-review;
- maximum three Fix cycles per task per automation invocation;
- no next-task implementation while the current task is unresolved or uncommitted;
- no Git-history rewriting without explicit approval;
- never stage unrelated user changes;
- prefer explicit-path staging; do not use `git add -A` or `git add .` by default;
- no Week task implementation;
- preserve unrelated user work;
- persist Implementation / Review / Fix history;
- TASK history is portfolio/audit material, not a substitute for technical Evidence;
- do not claim MVP completion unless all eight tasks are independently accepted and committed.

Begin the resumable MVP automation now.
