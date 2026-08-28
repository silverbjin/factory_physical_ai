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

Follow the TASK history recording policy defined there.

`prompts/codex/task_history_recording.md` defines portfolio/audit recording behavior only.
It does not override frozen task requirements, contracts, architecture, acceptance criteria, evidence rules, or the latest independent review findings.

If `prompts/codex/task_history_recording.md` is required by repository workflow but cannot be found or read, stop before modifying files and report the missing workflow dependency.

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

TASK history files under:

```text
docs/task_history/
```

are expected portfolio/audit workflow artifacts when created according to `prompts/codex/task_history_recording.md`.

They are not considered scope expansion or later-task implementation.

---

## 4. Pre-fix Inspection

Before modifying files:

1. Read applicable `AGENTS.md`.
2. Read `prompts/codex/read_only_review.md`.
3. Read `prompts/codex/task_history_recording.md`.
4. Read the exact task specification.
5. Read relevant context, plan, frozen contracts, architecture, ADRs, and prior-task prerequisites.
6. Inspect:

```bash
git status --short
git diff --stat
git diff
```

7. Reproduce or statically verify each acceptance-blocking finding.
8. Determine the current TASK history state under:

```text
docs/task_history/<TASK_ID>/
```

9. Briefly report:

   - findings confirmed;
   - findings no longer reproducible;
   - files expected to change;
   - tests expected to change/add;
   - evidence expected to change;
   - expected TASK history output;
   - any finding that may require Git-history correction.

Then proceed with the smallest safe correction.

---

## 5. Invariant-Fix Rules

When a review finding says an invariant can be bypassed, fix the invariant at the domain boundary, not only at one call site.

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

Store the result of this analysis as:

```text
GIT_HISTORY_STATUS
```

with one of:

```text
NO HISTORY ACTION REQUIRED
HISTORY ACTION REQUIRED
```

This Git-history status is separate from TASK history documentation under `docs/task_history/`.

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

Record actual commands, pass/fail counts, and failures for later Evidence and TASK History recording.

---

## 8. Evidence

If task evidence exists:

- update/regenerate it according to repository conventions;
- include the actual changed implementation/test files required by the evidence schema;
- include actual test commands and results;
- update hashes for modified sources;
- correct stale claims;
- preserve truthful provenance.

If an evidence defect depends on immutable Git history that cannot be corrected without authorization, report it instead of fabricating clean provenance.

### 8.1 TASK-history / Evidence boundary

TASK history files are human-readable portfolio/audit records.

Unless a frozen evidence contract explicitly requires otherwise, files under:

```text
docs/task_history/
```

are not implementation evidence and are excluded from:

- implementation source hash sets;
- implementation changed-file manifests;
- Exit Criteria implementation-file counts.

This prevents a recursive dependency where Evidence must include the history document that itself reports the Evidence result.

If a frozen evidence schema explicitly requires every repository change, follow that schema and report the ordering implications rather than silently violating it.

---

## 9. Technical Fix Self-check

Before recording TASK history, verify:

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

For every prior acceptance-blocking finding, assign exactly one status:

```text
FIXED
NOT REPRODUCIBLE
BLOCKED
```

Determine the technical corrective status now:

```text
READY FOR INDEPENDENT RE-REVIEW
```

or:

```text
NOT READY FOR INDEPENDENT RE-REVIEW
```

Do not yet return the final user-facing report.

Do not perform the independent review in this workflow.

---

## 10. TASK History Recording — Mandatory Workflow Step

After Sections 7–9 are complete, persist the corrective work using:

```text
prompts/codex/task_history_recording.md
```

This step is mandatory for the Fix workflow.

### 10.1 Determine history sequence

Inspect:

```text
docs/task_history/<TASK_ID>/
```

Determine the next sequential history number `SEQ` according to the recording policy.

Never overwrite, rename, delete, or renumber an existing history entry.

### 10.2 Create Fix history

Create:

```text
docs/task_history/<TASK_ID>/<SEQ>_fix.md
```

Use Korean for portfolio-readable narrative where English is not required.

Preserve exact technical identifiers including:

- `TASK_ID`;
- Finding IDs;
- severity values;
- file paths;
- class/function/variable names;
- contract/schema fields;
- commands;
- test names;
- error messages;
- `PASS` / `FAIL`;
- `FIXED` / `NOT REPRODUCIBLE` / `BLOCKED`;
- `READY FOR INDEPENDENT RE-REVIEW`;
- `HISTORY ACTION REQUIRED`;
- hashes and commit IDs.

At minimum record:

- 기준 Review;
- 수정 대상 Findings;
- root cause;
- 변경 파일과 목적;
- 각 Finding에 대한 수정 내용;
- regression tests added/strengthened;
- focused/full regression results;
- Evidence update;
- remaining findings;
- `GIT_HISTORY_STATUS`;
- technical corrective status;
- next step: independent Read-only Review.

### 10.3 Update TASK summary

Create or update:

```text
docs/task_history/<TASK_ID>/README.md
```

Append the current Fix run to the chronological workflow table.

Do not delete or rewrite earlier Implementation / Review / Fix entries.

Do not claim `ACCEPT` because Fix completed successfully.

The proper state after a successful Fix is conceptually:

```text
Fix: READY FOR INDEPENDENT RE-REVIEW
Review: PENDING
```

The bare `TASK_ID` review workflow is responsible for eventual `ACCEPT` / `REJECT`.

### 10.4 Update global TASK history index

Create or update:

```text
docs/task_history/README.md
```

Refresh only the row for `TASK_ID` while preserving all other TASK entries.

Use a state that distinguishes Fix completion from independent acceptance, such as:

```text
FIXED / RE-REVIEW PENDING
```

Do not mark the TASK as `ACCEPTED` until an independent Read-only Review actually returns `ACCEPT`.

### 10.5 TASK history write failure policy

If any mandatory TASK history output cannot be created or updated:

- do not alter source code merely to hide the documentation failure;
- do not fabricate a successful write;
- report the exact failure;
- preserve the technical corrective status separately;
- treat the overall Fix workflow as incomplete.

For example:

```text
Technical corrective status: READY FOR INDEPENDENT RE-REVIEW
TASK history recording: FAIL
Overall Fix workflow: NOT READY
```

Do not return the successful final Fix status until mandatory TASK history recording succeeds.

---

## 11. TASK History Verification

After recording history, verify:

```text
docs/task_history/<TASK_ID>/<SEQ>_fix.md
docs/task_history/<TASK_ID>/README.md
docs/task_history/README.md
```

Confirm:

1. all required files exist;
2. the correct `TASK_ID` is used;
3. the next valid `SEQ` was used;
4. no previous history entry was overwritten or deleted;
5. every corrected Finding ID and severity matches the review;
6. Finding statuses match actual correction results;
7. root-cause descriptions match the implemented fix;
8. test commands/results match actual validation;
9. Evidence path/status matches the updated evidence;
10. `GIT_HISTORY_STATUS` is recorded accurately;
11. technical corrective status matches Section 9;
12. TASK README workflow order is chronological;
13. global TASK index contains the current TASK and does not falsely claim `ACCEPTED`.

Then inspect:

```bash
git status --short
git diff --stat
git diff --check
```

At this stage:

- correctly generated `docs/task_history/` files are expected workflow artifacts;
- they must not be classified as unintended implementation changes;
- unrelated non-history changes must still be reported.

If TASK history verification fails, the overall Fix workflow is not ready for handoff.

---

## 12. Required Final Report

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

Separate correction artifacts from portfolio/audit history.

### Implementation / Test / Evidence

List files and purpose.

### TASK History

List:

- `docs/task_history/<TASK_ID>/<SEQ>_fix.md`
- `docs/task_history/<TASK_ID>/README.md`
- `docs/task_history/README.md`

## Tests Run

List command and pass/fail counts.

## Evidence

- Evidence updated: YES/NO/NOT APPLICABLE
- Evidence path
- Hash verification

## Remaining Findings

List only findings still relevant.

## Git History Status

Return one:

```text
No history action required.
```

or:

```text
HISTORY ACTION REQUIRED
```

with the required explanation.

## TASK History Status

- History policy loaded: YES/NO
- Fix history:
- TASK summary:
- Global history index:
- History verification: PASS/FAIL

## Final Status

Return exactly one:

```text
TASK_ID fixes are ready for independent re-review.
```

or:

```text
TASK_ID fixes are NOT ready for independent re-review.
```

The successful status is allowed only when:

- technical corrective status is `READY FOR INDEPENDENT RE-REVIEW`;
- all mandatory tests and validation required by the Fix workflow pass;
- required Evidence is truthful and current;
- no unresolved Git-history requirement prevents acceptance, unless the review explicitly allows it to be deferred;
- mandatory TASK history recording and verification pass.

If not ready, list only blocking reasons.

If ready, do not perform the independent review in this workflow.

The next user command should be the bare task ID so that the separate read-only review workflow runs independently.

---

## 13. Final Constraints

- Fix the cause, not the symptom.
- Fix only acceptance-blocking findings by default.
- Do not start the next task.
- Do not weaken frozen contracts.
- Do not rewrite Git history without explicit permission.
- Do not stage or commit unless explicitly requested.
- Do not declare acceptance yourself.
- Read and follow `prompts/codex/task_history_recording.md`.
- TASK history recording is mandatory for Fix workflow completion.
- Record TASK history only after technical fix validation and Evidence handling are resolved.
- Do not treat TASK history as implementation evidence unless a frozen contract explicitly requires it.
- Do not overwrite prior TASK history.
- Distinguish Git history status from TASK history documentation status.
- Finish by handing the task back to the independent read-only review workflow.

Begin the corrective workflow for the task identifier supplied in the current user message.
