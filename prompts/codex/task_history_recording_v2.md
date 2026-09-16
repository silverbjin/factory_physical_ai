# TASK History Recording Policy v2

## Purpose

Persist a compact, chronological audit trail for each TASK.

Supported workflow events:

```text
Implementation
Read-only Review
Fix
Re-review
```

History is an **event log**, not a duplicate of TASK specifications, Evidence, or full workflow reports.

Record only information newly established by the current workflow.

---

## 1. Core Rules

1. Store TASK history under:

```text
docs/task_history/<TASK_ID>/
```

2. History is append-only.

3. Never overwrite, rename, delete, or renumber an existing event record.

4. Use:

```text
<SEQ>_implementation.md
<SEQ>_review.md
<SEQ>_fix.md
```

5. Re-review uses the same `review` type.

6. Use Korean for concise explanatory prose.

7. Preserve exact technical identifiers, including:

```text
TASK IDs
Finding IDs
paths
symbols
commands
test names
contract/schema fields
state names
hashes
commit IDs
PASS / FAIL
ACCEPT / REJECT
BLOCKER / HIGH / MEDIUM / LOW
```

8. TASK History is not technical Evidence unless a frozen contract explicitly defines otherwise.

9. Do not duplicate large TASK, Evidence, Review, or test contents.

10. Record the workflow only after its technical result has been determined.

---

## 2. Sequence Resolution

Determine the next `SEQ` using filenames only.

Inspect:

```text
docs/task_history/<TASK_ID>/
```

for files matching:

```text
NN_*.md
```

Set:

```text
SEQ = highest existing NN + 1
```

Use two digits.

If no event file exists:

```text
SEQ = 01
```

Do not read prior event-file contents solely to determine `SEQ`.

If an apparent sequence collision or malformed history is detected, stop normal recording and report the history integrity issue.

---

## 3. Source-of-Truth Boundary

Do not restate information already authoritatively stored elsewhere unless necessary to explain the current event.

Use these sources:

```text
TASK specification
→ objective, scope, non-goals, requirements, Exit Criteria

Evidence
→ test results, hashes, structured validation facts

Review result
→ findings, severity, Acceptance Gates, recommendation

Fix result
→ finding status, root cause, correction, regression proof
```

History should reference these results rather than reproducing them in full.

---

## 4. Event Recording

Create exactly one event file for the completed workflow.

---

### 4.1 Implementation Event

Create:

```text
docs/task_history/<TASK_ID>/<SEQ>_implementation.md
```

Record only:

```markdown
# Implementation — <TASK_ID>

- Result: COMPLETE | INCOMPLETE
- Evidence: <path | NOT REQUIRED>
- Changed areas: <concise paths/modules>
- Key implementation delta: <1–5 concise bullets>
- Validation: <concise PASS/FAIL summary>
- Deviation from TASK: <NONE or concise description>
- Next: Independent Read-only Review | BLOCKED
```

Do not copy:

- full TASK Scope;
- full Non-goals;
- full Exit Criteria;
- complete test logs;
- Evidence contents.

Implementation completion must not be recorded as independent acceptance.

---

### 4.2 Review Event

Create:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
```

#### ACCEPT

Use compact form:

```markdown
# Review — <TASK_ID>

- Recommendation: ACCEPT
- Requirements: <passed>/<total> PASS
- Acceptance Gates: ALL PASS
- Focused validation: PASS
- Regression: PASS | NOT REQUIRED
- Evidence: PASS | NOT APPLICABLE
- Findings: BLOCKER <n>, HIGH <n>, MEDIUM <n>, LOW <n>
- Conditional Sources loaded: <n>
```

Do not reproduce the complete Traceability table when all requirements passed unless repository policy explicitly requires it.

#### REJECT

Record the blocking review delta:

```markdown
# Review — <TASK_ID>

- Recommendation: REJECT
- Failed Gates: <list>
- Validation: <concise status>
- Evidence: <concise status>

## Blocking Findings

### <Finding ID> — <Severity>

- Requirement / Contract:
- File / Symbol:
- Issue:
- Why it blocks acceptance:
- Recommended remediation:
```

Include only findings that materially affect acceptance or meaningful deferred risk.

Do not duplicate unrelated review prose.

---

### 4.3 Fix Event

Create:

```text
docs/task_history/<TASK_ID>/<SEQ>_fix.md
```

Use Finding IDs as references to the prior Review.

Record:

```markdown
# Fix — <TASK_ID>

- Result: READY FOR INDEPENDENT RE-REVIEW | NOT READY FOR INDEPENDENT RE-REVIEW
- Based on Review: <SEQ/path>

## Finding Results

| Finding | Severity | Status | Correction | Regression |
|---|---|---|---|---|
| <ID> | HIGH | FIXED | <concise delta> | PASS |

- Evidence: <PASS/path | NOT APPLICABLE>
- Regression: <PASS | NOT REQUIRED | FAIL>
- Git history: NO HISTORY ACTION REQUIRED | HISTORY ACTION REQUIRED
- Conditional Sources loaded: <n>
- Next: Independent Read-only Review | BLOCKED
```

Do not restate the original Finding in full.

Use:

```text
FIXED
NOT REPRODUCIBLE
BLOCKED
```

for each relevant Finding.

---

## 5. TASK README

Maintain:

```text
docs/task_history/<TASK_ID>/README.md
```

as a compact event index.

Recommended form:

```markdown
# <TASK_ID> History

Current status: <STATE>

| Seq | Type | Result | Record |
|---:|---|---|---|
| 01 | Implementation | COMPLETE | `01_implementation.md` |
| 02 | Review | REJECT | `02_review.md` |
| 03 | Fix | READY FOR RE-REVIEW | `03_fix.md` |
| 04 | Review | ACCEPT | `04_review.md` |
```

For each workflow:

1. read only the current TASK README;
2. append one event row;
3. update `Current status`;
4. do not reread prior detailed history files unless an inconsistency requires investigation.

Use these TASK-level states:

```text
IMPLEMENTED / REVIEW PENDING
REJECTED / FIX REQUIRED
FIXED / RE-REVIEW PENDING
ACCEPTED
INCOMPLETE
```

Mapping:

```text
Implementation COMPLETE
→ IMPLEMENTED / REVIEW PENDING

Review REJECT
→ REJECTED / FIX REQUIRED

Fix READY FOR INDEPENDENT RE-REVIEW
→ FIXED / RE-REVIEW PENDING

Review ACCEPT
→ ACCEPTED

failed/incomplete workflow
→ INCOMPLETE when no more specific valid state applies
```

---

## 6. Final ACCEPT Enrichment

Only when an independent Review returns:

```text
ACCEPT <TASK_ID>
```

may the TASK README be enriched with:

```markdown
## Final Summary

- Final validation: <concise summary>
- Evidence: <path>
- Final review: <review record>

## Portfolio Summary

<3–5 sentences describing:
the engineering problem,
the most important implementation decision,
any meaningful Review/Fix lesson,
and the final quality gate achieved.>
```

Do not generate or repeatedly rewrite a Portfolio Summary before final ACCEPT.

---

## 7. Global TASK Index

The optional global index is:

```text
docs/task_history/README.md
```

Do not update it after every workflow by default.

Update it only when:

```text
- a TASK reaches ACCEPTED; or
- the user/repository explicitly requires an intermediate global status update.
```

When updating it:

1. read the existing index only;
2. update or add only the row for `TASK_ID`;
3. do not scan every TASK history directory;
4. preserve all unrelated rows.

Recommended form:

```markdown
# TASK History

| TASK | Status | Last Event | Final Result |
|---|---|---|---|
| TASK-MVP-001 | ACCEPTED | Review | ACCEPT |
| TASK-MVP-002 | FIXED / RE-REVIEW PENDING | Fix | - |
```

For an ACCEPT Review, updating this file is an allowed audit-log write.

---

## 8. Review Audit-write Boundary

Read-only Review remains read-only for implementation and source-of-truth surfaces.

After the Review recommendation is fixed, History recording may modify only:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
docs/task_history/<TASK_ID>/README.md
```

and, only when Section 7 requires it:

```text
docs/task_history/README.md
```

No source, test, Evidence, TASK specification, contract, schema, architecture, Git index, or Git history may be modified by the Review history step.

---

## 9. History Verification

Use minimal verification.

Confirm:

1. the expected event file exists;
2. the correct `TASK_ID` and workflow result are recorded;
3. `SEQ` does not overwrite an existing event;
4. the TASK README contains the new event row;
5. the TASK-level state matches the workflow result.

When final ACCEPT updates the global index, also verify the `TASK_ID` row.

Do not reread every prior event file solely for verification.

If an inconsistency is detected, investigate only the affected history files.

---

## 10. History Failure Policy

If mandatory History recording fails:

- do not alter implementation, tests, Evidence, or source-of-truth documents to hide the failure;
- do not fabricate a successful write;
- preserve the already-determined technical result;
- report the History failure separately.

Example:

```text
Technical result: READY FOR INDEPENDENT RE-REVIEW
History recording: FAIL
Workflow completion: INCOMPLETE
```

History failure must not rewrite or soften an already-determined Review recommendation.

---

## 11. Efficiency Rules

Default recording path:

```text
technical workflow result
→ determine SEQ from filenames
→ create one compact event record
→ update TASK README
→ verify current event
```

For final ACCEPT only:

```text
→ add final/portfolio summary
→ update global TASK index
```

Do not default to:

```text
read all previous history events
```

Do not default to:

```text
rewrite the TASK README as a full summary
```

Do not default to:

```text
update the global TASK index after every event
```

Do not duplicate:

```text
TASK specification
Evidence
full test output
full Review report
```

Prefer:

```text
reference + event-specific delta
```

over:

```text
full snapshot duplication
```

---

## 12. Acceptance Recording Handoff

section verbatim, including the fenced YAML block.

**Rules:**

1. Do not recompute or reinterpret the handoff while recording history.

2. Do not change:

- review_decision;

- reviewed_commit;

- task_specific_decision;

- TASK spec path/hash;

- Evidence path/hash;

- supporting artifact path/hash;

- acceptance_recording_eligible.

3. The history recorder may add its normal history metadata outside the preserved review content, but must not rewrite the handoff.

4. For REJECT reviews, preserve:

- acceptance_recording_eligible: false

5. The persisted review record under:

- docs/task_history/<TASK_ID>/<NN>_review.md
becomes the source hashed by record_task_acceptance_v2.md.

6. Do not create the acceptance JSON in the history-recording workflow.

Recommended flow:

read_only_review_v2.md
        ↓
review output with handoff
        ↓
task_history_recording_v2.md
        ↓
persisted <NN>_review.md with handoff unchanged
        ↓
record_task_acceptance_v2.md