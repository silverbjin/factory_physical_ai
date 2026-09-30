# TASK History Recording Policy v2.1

## Purpose

Persist a compact chronological audit trail for one TASK.

Supported events:

```text
Implementation
Review
Fix
Diagnosis
```

Re-review is recorded as `Review`.

History is an **event log**, not a copy of TASK specs, Evidence, test logs, or full workflow reports.

Record only facts newly established by the current workflow.

---

# 1. Common Rules

History directory:

```text
docs/task_history/<TASK_ID>/
```

Event files:

```text
<SEQ>_implementation.md
<SEQ>_review.md
<SEQ>_fix.md
<SEQ>_diagnosis.md
```

Rules:

1. History is append-only.
2. Never overwrite, rename, delete, or renumber an existing event.
3. Record only after the current workflow result is known.
4. Use Korean for concise explanatory prose.
5. Preserve exact technical identifiers:

   * TASK / Finding IDs;
   * paths / symbols;
   * commands / tests;
   * contract/schema fields;
   * states;
   * hashes / commit IDs;
   * PASS / FAIL;
   * ACCEPT / REJECT;
   * severity names.
6. Reference authoritative artifacts instead of reproducing them.
7. TASK History is not technical Evidence unless a frozen contract says otherwise.
8. Do not stage or commit as part of history recording.

Allowed history writes are limited to:

```text
docs/task_history/<TASK_ID>/<SEQ>_<event>.md
docs/task_history/<TASK_ID>/README.md
```

and, only when Section 6 requires it:

```text
docs/task_history/README.md
```

No source, test, Evidence, TASK specification, contract, schema, architecture, Acceptance JSON, Git index, or Git history may be modified.

---

# 2. Sequence Resolution

Determine `SEQ` from filenames only.

Inspect:

```text
docs/task_history/<TASK_ID>/
```

for:

```text
NN_*.md
```

Then:

```text
SEQ = highest existing NN + 1
```

Use two digits.

If none exists:

```text
SEQ = 01
```

Do not read prior event contents merely to determine sequence.

If numbering is malformed or the next sequence would collide, stop and report a history-integrity failure.

---

# 3. Source-of-Truth Boundary

Use authoritative sources as follows:

```text
TASK spec
→ objective / scope / requirements / Exit Criteria

Evidence
→ structured validation facts / hashes

Review result
→ findings / gates / recommendation / acceptance handoff

Fix result
→ finding status / correction / regression proof

Diagnosis result
→ root cause / authority / contract boundary / correction scope / verification
```

History records only the event-specific delta.

Do not duplicate:

* full TASK scope;
* full Exit Criteria;
* Evidence payloads;
* complete test logs;
* full Review prose;
* prior Findings already recorded.

---

# 4. Event Records

Create exactly one event file for the completed workflow.

## 4.1 Implementation

Path:

```text
docs/task_history/<TASK_ID>/<SEQ>_implementation.md
```

Compact format:

```markdown
# Implementation — <TASK_ID>

- Result: COMPLETE | INCOMPLETE
- Evidence: <path | NOT REQUIRED>
- Changed areas: <concise paths/modules>
- Validation: <concise PASS/FAIL>
- Deviation: <NONE | concise>
- Next: Independent Read-only Review | BLOCKED

## Delta

- <1–5 concise implementation changes>
```

Do not represent Implementation completion as Review acceptance.

---

## 4.2 Review / Re-review

Path:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
```

### ACCEPT

```markdown
# Review — <TASK_ID>

- Recommendation: ACCEPT
- Requirements: <passed>/<total> PASS
- Acceptance Gates: ALL PASS
- Focused validation: PASS
- Regression: PASS | NOT REQUIRED
- Evidence: PASS | NOT APPLICABLE
- Findings: BLOCKER <n>, HIGH <n>, MEDIUM <n>, LOW <n>
```

Do not reproduce full traceability when all requirements passed unless explicitly required.

### REJECT

```markdown
# Review — <TASK_ID>

- Recommendation: REJECT
- Failed Gates: <list>
- Validation: <concise>
- Evidence: <concise>

## Blocking Findings

### <Finding ID> — <Severity>

- Requirement / Contract:
- File / Symbol:
- Issue:
- Why it blocks acceptance:
- Recommended remediation:
```

Record only acceptance-blocking findings or meaningful deferred risks.

If the Review output contains an Acceptance Recording Handoff, preserve it exactly as required by Section 9.

---

## 4.3 Fix

Path:

```text
docs/task_history/<TASK_ID>/<SEQ>_fix.md
```

```markdown
# Fix — <TASK_ID>

- Result: READY FOR INDEPENDENT RE-REVIEW | NOT READY FOR INDEPENDENT RE-REVIEW
- Based on Review: <SEQ/path>
- Evidence: <PASS/path | NOT APPLICABLE>
- Regression: PASS | NOT REQUIRED | FAIL
- Git history: NO HISTORY ACTION REQUIRED | HISTORY ACTION REQUIRED
- Next: Independent Read-only Review | BLOCKED

## Finding Results

| Finding | Severity | Status | Correction | Regression |
|---|---|---|---|---|
| <ID> | <severity> | FIXED | <concise delta> | PASS |
```

Allowed finding statuses:

```text
FIXED
NOT REPRODUCIBLE
BLOCKED
```

Do not repeat the original Finding in full.

---

## 4.4 Diagnosis

Path:

```text
docs/task_history/<TASK_ID>/<SEQ>_diagnosis.md
```

Diagnosis is read-only with respect to implementation/source-of-truth surfaces.

Statuses:

```text
RESOLVED
UNRESOLVED
```

Meaning:

```text
RESOLVED
→ authority, root cause, correction boundary, and verification are sufficient
  for the next Implementation/Fix worker to proceed without guessing.

UNRESOLVED
→ architecture/contract/root-cause uncertainty remains;
  speculative Implementation/Fix is not authorized.
```

Compact format:

```markdown
# Diagnosis — <TASK_ID>

- Status: RESOLVED | UNRESOLVED
- Trigger: <concise blocker>
- Triggering status: <optional>
- Finding IDs: <optional>
- Diagnosis tier/model: <optional>

## Root Cause

<established cause | UNPROVEN>

## Requirement / Contract

<violated or missing boundary>

## Authoritative Sources

<only sources actually used>

## Resolution

<resolved correction direction | remaining decision>

## Modification Scope

<allowed files/symbols, if established>

## Protected Scope

<must-not-change surfaces>

## Verification

<minimum focused verification>

## Next Action

<valid next action>

Final diagnosis status: RESOLVED
```

or:

```text
Final diagnosis status: UNRESOLVED
```

The exact final-status line is mandatory.

Valid RESOLVED next actions:

```text
IMPLEMENTATION
IMPLEMENT_RESOLVED_FIX
RESUME_IMPLEMENTATION
RESUME_FIX
```

Valid UNRESOLVED next actions:

```text
ESCALATION_REQUIRED
MANUAL_ARCHITECTURE_DECISION
```

Preserve a supplied valid next action exactly.

`RESOLVED` does not mean Implementation complete, Review accepted, or TASK accepted.

Diagnosis must never create or infer:

```text
acceptance_handoff
Acceptance JSON
ACCEPT
```

---

# 5. TASK README

Maintain:

```text
docs/task_history/<TASK_ID>/README.md
```

Read only the current README, append one event row, and update `Current status` when applicable.

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

TASK-level states:

| Event result                        | TASK status                                      |
| ----------------------------------- | ------------------------------------------------ |
| Implementation COMPLETE             | `IMPLEMENTED / REVIEW PENDING`                   |
| Review REJECT                       | `REJECTED / FIX REQUIRED`                        |
| Fix READY FOR INDEPENDENT RE-REVIEW | `FIXED / RE-REVIEW PENDING`                      |
| Review ACCEPT                       | `ACCEPTED`                                       |
| failed/incomplete workflow          | `INCOMPLETE` when no more specific state applies |

Diagnosis always appears in the event index but **does not change TASK-level status**.

Retain the status established by the preceding lifecycle event.

Do not reread detailed prior history unless the README/index is inconsistent.

---

# 6. Final ACCEPT and Global Index

Only after an independent Review returns ACCEPT may the TASK README add:

```markdown
## Final Summary

- Final validation: <concise>
- Evidence: <path>
- Final review: <review record>

## Portfolio Summary

<3–5 concise sentences covering the engineering problem,
main implementation decision, important Review/Fix lesson,
and final quality gate.>
```

Do not create or repeatedly rewrite this summary before final ACCEPT.

The optional global index is:

```text
docs/task_history/README.md
```

Update it only when:

```text
TASK reaches ACCEPTED
```

or repository/user policy explicitly requires an intermediate update.

When updating:

1. read the existing global index only;
2. modify/add only the row for `TASK_ID`;
3. preserve unrelated rows;
4. do not scan all TASK-history directories.

Diagnosis may be shown as `Last Event`, but never changes `Status` or `Final Result` to ACCEPTED.

---

# 7. Verification and Failure

After recording:

1. confirm the expected event file exists;
2. confirm TASK_ID, event type, and result;
3. confirm no existing sequence was overwritten;
4. confirm TASK README contains the event row;
5. confirm TASK-level status mapping;
6. run minimal repository integrity validation such as:

```bash
git diff --check
```

If final ACCEPT updates the global index, verify only that TASK row.

Do not reread all previous event files.

If History recording fails:

```text
Technical result: <already determined result>
History recording: FAIL
Workflow completion: INCOMPLETE
```

Do not change, weaken, or reinterpret the technical result to hide a History failure.

---

# 8. Efficiency Rules

Default path:

```text
workflow result
→ determine SEQ from filenames
→ create one compact event
→ update TASK README
→ minimal verification
```

Final ACCEPT only:

```text
→ Final Summary / Portfolio Summary
→ global TASK index
```

Never default to:

```text
read all history
rewrite README as a full workflow summary
update global index after every event
copy TASK/Evidence/test/Review contents
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

# 9. Acceptance Recording Handoff

This section applies only to Review/Re-review history containing an Acceptance Recording Handoff.

Persist the handoff **verbatim**, including its fenced YAML block.

Do not recompute, reinterpret, normalize, or modify:

```text
review_decision
reviewed_commit
task_specific_decision
TASK spec path/hash
Evidence path/hash
supporting artifact path/hash
acceptance_recording_eligible
```

For REJECT preserve:

```text
acceptance_recording_eligible: false
```

The persisted Review record:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
```

is the source later hashed by `record_task_acceptance_v2.md`.

History recording must NOT create the Acceptance JSON.

Required flow:

```text
read_only_review_v2.md
        ↓
Review output + acceptance handoff
        ↓
task_history_recording.md
        ↓
persisted <SEQ>_review.md
with handoff unchanged
        ↓
record_task_acceptance_v2.md
```
