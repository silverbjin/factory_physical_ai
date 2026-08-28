# Common Review-Finding Fix Prompt

## Purpose

This file defines the reusable corrective workflow for a task that failed an independent read-only review.

Typical invocation:

```text
Fix TASK-MVP-002
```

or:

```text
Fix TASK-W2-001
```

Extract the exact task identifier from the current user message and treat it as `TASK_ID`.

The goal is to correct only the findings that prevent `TASK_ID` from being accepted, then rerun the required implementation validation. Do not start the next task.

---

## 1. Resolve the Target and Findings

1. Extract exactly one `TASK_ID`.
2. If the current Codex conversation contains the latest read-only review for `TASK_ID`, use it as an input.
3. Regardless of conversation history, independently inspect the current repository and frozen requirements to verify that each reported finding still exists.
4. If the prior review is not available in the current conversation, reconstruct the acceptance-blocking findings by applying `prompts/codex/read_only_review.md` as a diagnostic procedure before modifying files.
5. Do not ask the user to paste file paths or task requirements that can be discovered from the repository.
6. Also read `prompts/codex/task_history_recording.md`.

Never blindly fix a stale review finding that is no longer reproducible.

---

## 2. Findings to Fix by Default

Fix:

- all `BLOCKER` findings;
- all `HIGH` findings;
- any `MEDIUM` finding that directly causes an Acceptance Gate to remain `FAIL`, including scope, contract, regression, or evidence-integrity failures.

Do not fix `LOW` findings by default.

Do not fix non-blocking `MEDIUM` findings unless they are necessary for the target task to pass its Acceptance Gates.

If a finding requires scope expansion into a later task, do not implement that later-task functionality. Find the smallest target-task-local correction instead, or report the conflict.

---

## 3. Strict Scope

Modify only what is necessary to repair `TASK_ID`.

You MUST NOT:

- implement the next task;
- expand the MVP / phase / week scope;
- perform unrelated refactors;
- modify frozen contracts merely to make tests pass;
- weaken tests;
- suppress failures instead of fixing their cause;
- stage or commit changes unless explicitly requested;
- rewrite Git history unless the user explicitly authorizes history rewriting.

Preserve unrelated user changes.

---

## 4. Pre-fix Inspection

Before modifying files:

1. Read applicable `AGENTS.md`.
2. Read `prompts/codex/read_only_review.md`.
3. Read the exact task specification.
4. Read relevant context, plan, frozen contracts, architecture, ADRs, and prior-task prerequisites.
5. Inspect:

```bash
git status --short
git diff --stat
git diff
```

6. Reproduce or statically verify each acceptance-blocking finding.
7. Briefly report:
   - findings confirmed;
   - findings no longer reproducible;
   - files expected to change;
   - tests expected to change/add;
   - any finding that may require Git-history correction.

Then proceed with the smallest safe correction.

---

## 5. Invariant-Fix Rules

When a review finding says an invariant can be bypassed, fix the invariant at the domain boundary, not only at one call site.

Examples:

### Caller-configurable safety bound

Bad pattern:

```text
caller selects retry_limit
```

Preferred correction:

```text
runtime invariant owns the fixed bound
```

Do not rely only on a test or default argument when callers can override the value.

### Constructor bypass

If callers can directly construct an impossible terminal or intermediate state:

- restrict externally valid initial construction;
- ensure all state advancement goes through validated domain logic;
- ensure alternate construction paths such as copy/replace/deserialization cannot bypass the invariant when applicable;
- add regression tests for the bypass itself.

### Invalid transition bypass

Do not merely patch the specific failing example. Verify every public path that can change or manufacture lifecycle state.

### Evidence mismatch

Evidence must reflect the repository and validation actually performed after the fix.

Never change evidence solely to hide an implementation or scope defect.

---

## 6. Git-History Safety

Some review findings may concern an already-created commit, such as:

- unrelated file included in the task commit;
- evidence referring to the wrong committed snapshot;
- commit provenance mismatch.

By default:

- do not amend;
- do not rebase;
- do not reset;
- do not force-push;
- do not rewrite history.

First determine whether the problem can be corrected safely with source/test/evidence changes in the current working tree.

If acceptance requires historical commit rewriting, stop that part and report:

```text
HISTORY ACTION REQUIRED
```

Include:

- exact commit involved;
- why normal source/evidence correction is insufficient;
- whether the commit appears local or already shared, if this can be determined safely;
- the minimal history operation that would be required.

Continue fixing independent source/test issues that do not require history rewriting.

---

## 7. Tests

For every corrected finding, add or strengthen a regression test that would have failed before the fix when practical.

At minimum cover:

- the exact bypass reported;
- nearby equivalent bypass paths;
- frozen contract behavior;
- boundary values;
- invalid paths;
- existing happy paths.

Do not only test the public method that previously passed if the review found another public construction or mutation path.

Run:

1. focused tests for the corrected task;
2. full regression suite;
3. repository-defined syntax/static checks;
4. `git diff --check`.

Do not claim a finding fixed if its regression test still fails.

---

## 8. Evidence

If task evidence exists:

- update/regenerate it according to repository conventions;
- include the actual changed files;
- include actual test commands and results;
- update hashes for modified sources;
- correct stale claims;
- preserve truthful provenance.

If an evidence defect depends on immutable Git history that cannot be corrected without authorization, report it instead of fabricating clean provenance.

---

## 9. Final Self-check

Before reporting completion, verify:

- all BLOCKER findings are resolved;
- all HIGH findings are resolved;
- all MEDIUM findings that block Acceptance Gates are resolved or explicitly identified as requiring authorization;
- LOW findings were not expanded into unnecessary work;
- no next-task functionality was implemented;
- frozen contracts remain intact;
- focused tests pass;
- full regression passes;
- evidence matches current implementation;
- unrelated user changes remain untouched.

---

## 10. Required Final Report

Return:

# Fix Result — `TASK_ID`

## Findings Addressed

For each prior finding:

- Finding ID
- Severity
- Status: FIXED / NOT REPRODUCIBLE / BLOCKED
- Files changed
- Regression test

## Files Changed

List files and purpose.

## Tests Run

List command and pass/fail counts.

## Evidence

- Evidence updated: YES/NO/NOT APPLICABLE
- Evidence path
- Hash verification

## Remaining Findings

List only findings still relevant.

## History Status

Return one:

```text
No history action required.
```

or:

```text
HISTORY ACTION REQUIRED
```

with the required explanation.

## Final Status

Return exactly one:

```text
TASK_ID fixes are ready for independent re-review.
```

or:

```text
TASK_ID fixes are NOT ready for independent re-review.
```

If ready, do not perform the independent review in this workflow.

The next user command should be the bare task ID so that the separate read-only review workflow runs independently.

---

## 11. Final Constraints

- Fix the cause, not the symptom.
- Fix only acceptance-blocking findings by default.
- Do not start the next task.
- Do not weaken frozen contracts.
- Do not rewrite Git history without explicit permission.
- Do not stage or commit unless explicitly requested.
- Do not declare acceptance yourself.
- Finish by handing the task back to the independent read-only review workflow.

## 12. Documentation

Persist the corrective work using the TASK history policy.

Create the next sequential:

docs/task_history/<TASK_ID>/<SEQ>_fix.md

Update:

docs/task_history/<TASK_ID>/README.md
docs/task_history/README.md

Record:
- findings addressed;
- root cause;
- changed files;
- regression tests added/strengthened;
- evidence updates;
- remaining findings;
- history-action requirement;
- readiness for independent re-review.