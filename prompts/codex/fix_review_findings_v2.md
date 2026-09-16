# Common Review-Finding Fix Prompt v2

## Purpose

Correct only the acceptance-blocking findings for exactly one TASK that failed an independent Read-only Review.

Typical invocation:

```text
Fix TASK-MVP-002
```

Extract exactly one task identifier and treat it as `TASK_ID`.

If exactly one valid TASK cannot be resolved, stop and report:

```text
TASK_ID unresolved.
```

The goal is:

```text
latest blocking Review findings
→ reproduce
→ minimal root-cause fix
→ required validation
→ truthful Evidence
→ independent re-review handoff
```

Do not perform the independent re-review in this workflow.

---

## 1. Core Rules

For `TASK_ID`:

1. fix only findings that block acceptance;
2. reproduce each finding before fixing it;
3. fix the root cause, not only the reported symptom;
4. preserve frozen contracts and architecture;
5. preserve unrelated user changes;
6. do not implement later TASK functionality;
7. do not weaken tests to obtain PASS;
8. do not stage or commit unless explicitly requested;
9. do not rewrite Git history without explicit authorization;
10. update required Evidence truthfully;
11. record TASK history only after technical correction is resolved;
12. do not declare `ACCEPT`; hand the TASK back to independent Review.

Fix by default:

```text
BLOCKER
HIGH
MEDIUM only when it keeps an Acceptance Gate at FAIL
```

Do not fix `LOW` findings by default.

Do not fix non-blocking `MEDIUM` findings unless necessary for acceptance.

---

## 2. Fix Inputs

Use the minimum sufficient context.

Normal path:

```text
TASK specification
→ latest blocking Review findings
→ Required Sources
→ finding-related code/tests
```

Do not perform a full Review again by default.

---

### 2.1 TASK specification

Locate and read:

- applicable `AGENTS.md`;
- exact `TASK_ID` specification.

Read the TASK's:

- Dependencies when relevant to a finding;
- Required Sources;
- Frozen References;
- Scope;
- Non-goals;
- Requirements;
- Validation;
- Evidence;
- Exit Criteria.

Do not automatically load Conditional Sources.

---

### 2.2 Latest Review findings

Resolve the latest independent Review for `TASK_ID` in this order:

1. latest Review available in the current Codex conversation;
2. latest applicable `*_review.md` under `docs/task_history/<TASK_ID>/`;
3. narrow repository lookup for the most recent Review artifact.

Use the Review only as the source of reported findings.

The Review does not override frozen requirements or contracts.

Do not blindly fix a stale finding.

Before modification, verify every acceptance-blocking finding against the current repository.

If no reliable Review can be found:

```text
activate REVIEW_NOT_FOUND
```

Do not automatically run the entire Read-only Review workflow unless targeted reconstruction cannot resolve the blocking findings.

---

## 3. Context Expansion Policy

Conditional Sources are exception-path context.

Do not read them preemptively.

Use the following anomaly triggers when applicable:

```text
REVIEW_NOT_FOUND
FINDING_NOT_REPRODUCIBLE
FINDING_AMBIGUOUS
CONTRACT_CONFLICT
SCOPE_CONFLICT
INVARIANT_BYPASS
TEST_GAP
VALIDATION_FAILURE
REGRESSION_FAILURE
EVIDENCE_FAILURE
UNEXPECTED_REPOSITORY_CHANGE
GIT_HISTORY_ISSUE
```

When a trigger occurs:

1. identify the exact trigger;
2. load only TASK Conditional Sources mapped to the issue when available;
3. investigate only the affected finding/requirement/file/test/evidence area;
4. stop expanding context once resolved.

If Conditional Sources are insufficient, escalate narrowly:

```text
matching Conditional Sources
→ directly related file/search
→ directly related Context / Plan
→ directly relevant Architecture / ADR / Contract
→ broader repository search
```

Broader repository search is a last resort.

---

## 4. Pre-fix State

Before editing, run:

```bash
git status --short
git diff --stat
```

Preserve pre-existing user changes.

Do not read the complete repository diff by default.

Inspect detailed diff only for:

- finding-related files;
- target files with pre-existing changes;
- unexpected changes requiring investigation.

Prefer:

```bash
git diff -- <relevant-path>
```

over full repository diff output.

---

## 5. Finding Verification

For each acceptance-blocking Review finding, determine:

```text
CONFIRMED
NOT REPRODUCIBLE
BLOCKED
```

A finding is `CONFIRMED` when the reported defect still exists.

A finding is `NOT REPRODUCIBLE` only when the current repository and frozen requirements show that the defect no longer exists.

Do not mark a finding `NOT REPRODUCIBLE` merely because a test happens to pass.

If the finding is materially ambiguous:

```text
activate FINDING_AMBIGUOUS
```

If a safe target-task-local fix conflicts with frozen requirements:

```text
activate CONTRACT_CONFLICT
```

If correction appears to require later-TASK functionality:

```text
activate SCOPE_CONFLICT
```

Do not cross that boundary merely to satisfy the Review.

---

## 6. Correction

For each `CONFIRMED` blocking finding, implement the smallest root-cause correction.

Do not:

- modify unrelated modules;
- perform unrelated refactoring;
- alter frozen contracts for convenience;
- suppress errors;
- weaken guards;
- weaken tests;
- introduce future functionality.

When a Review identifies a structural invariant bypass:

```text
activate INVARIANT_BYPASS
```

Then inspect only relevant alternate public paths that can create, mutate, deserialize, copy, replace, or otherwise bypass the same invariant.

Do not apply this broader invariant inspection to unrelated finding categories.

---

## 7. Regression Proof

For each corrected finding, add or strengthen a regression test when practical.

The regression proof should primarily cover:

- the exact reported defect;
- the corrected requirement/contract;
- directly equivalent bypass paths only when the defect is structural;
- relevant existing happy behavior.

Do not expand test scope into unrelated boundaries.

If meaningful regression proof cannot be established:

```text
activate TEST_GAP
```

---

## 8. Validation

Follow the TASK validation policy.

Prefer:

```text
PASS → concise output
FAIL → targeted verbose output
```

### 8.1 Focused validation

Run the TASK's focused validation plus any regression tests added for the findings.

If it fails:

```text
activate VALIDATION_FAILURE
```

Inspect only the failing tests/checks first.

---

### 8.2 Regression

Follow the TASK declaration:

```text
REQUIRED
NOT REQUIRED
CONDITIONAL
```

Also require regression when the correction:

- changes a shared or frozen interface;
- crosses the TASK's normal local implementation boundary; or
- addresses a Review finding specifically involving regression safety.

If required regression fails:

```text
activate REGRESSION_FAILURE
```

Investigate the affected subsystem only.

---

### 8.3 Repository check

Before determining technical corrective status, run:

```bash
git status --short
git diff --stat
git diff --check
```

If unexpected changes appear:

```text
activate UNEXPECTED_REPOSITORY_CHANGE
```

Inspect affected paths only.

---

## 9. Evidence

Follow the TASK's declared Evidence policy.

If:

```text
Evidence required: YES
```

update or regenerate the declared Evidence so that it reflects the corrected repository and actual validation results.

Do not fabricate:

- changed files;
- test commands;
- test results;
- hashes;
- timestamps;
- prerequisite states;
- Exit Criteria.

TASK history is not technical Evidence unless a frozen contract explicitly requires otherwise.

If required Evidence cannot be updated or verified:

```text
activate EVIDENCE_FAILURE
```

---

## 10. Git History

Default rule:

```text
Do not rewrite Git history.
```

Do not amend, rebase, reset, force-push, or otherwise rewrite history without explicit authorization.

Only analyze Git-history correction when:

- a Review finding explicitly concerns commit provenance;
- required Evidence refers to an irreconcilably wrong committed snapshot; or
- acceptance cannot be achieved through normal source/test/Evidence correction.

Then:

```text
activate GIT_HISTORY_ISSUE
```

Determine:

```text
NO HISTORY ACTION REQUIRED
```

or:

```text
HISTORY ACTION REQUIRED
```

If history action is required, do not perform it without authorization.

Continue independent source/test fixes that do not require history rewriting.

---

## 11. Finding Status and Technical Handoff

For every prior acceptance-blocking finding, assign exactly one final status:

```text
FIXED
NOT REPRODUCIBLE
BLOCKED
```

A finding may be `FIXED` only when:

- the defect is corrected;
- required regression proof passes;
- relevant validation passes.

Determine the technical corrective status:

```text
READY FOR INDEPENDENT RE-REVIEW
```

only when:

- all BLOCKER findings are `FIXED` or legitimately `NOT REPRODUCIBLE`;
- all HIGH findings are `FIXED` or legitimately `NOT REPRODUCIBLE`;
- all gate-blocking MEDIUM findings are resolved;
- required focused validation passes;
- required regression passes;
- required Evidence is valid;
- no unresolved scope/contract/history blocker prevents acceptance.

Otherwise:

```text
NOT READY FOR INDEPENDENT RE-REVIEW
```

Do not perform the independent Review here.

---

## 12. TASK History

Only after technical correction and Evidence status are fixed, read:

```text
prompts/codex/task_history_recording.md
```

Follow it as the authoritative Fix-history policy.

Do not duplicate its detailed sequencing, file-writing, or index-update rules here.

TASK history must record the actual Fix result, including:

- corrected findings;
- findings not reproducible;
- blocked findings;
- validation result;
- Evidence status;
- Git-history status;
- technical corrective status.

Fix completion must not be represented as independent `ACCEPT`.

If history recording fails, preserve the technical result separately:

```text
Technical corrective status: READY FOR INDEPENDENT RE-REVIEW | NOT READY FOR INDEPENDENT RE-REVIEW
Workflow history recording: FAIL
```

The overall Fix workflow is incomplete until mandatory history recording succeeds.

---

## 13. Final Output

Use a compact success path and detailed blocked path.

### 13.1 Ready for re-review

Return:

```text
# Fix Result — <TASK_ID>

Status: READY FOR INDEPENDENT RE-REVIEW

Findings:
- <finding ID>: FIXED | NOT REPRODUCIBLE
- ...

Validation:
- focused: PASS
- regression: PASS | NOT REQUIRED
- Evidence: PASS | NOT APPLICABLE

Git history:
- NO HISTORY ACTION REQUIRED

History:
- <Fix history path>

Context:
- Conditional Sources loaded: <count>
- Expansion triggers: <list | NONE>

Next:
<TASK_ID>

<TASK_ID> fixes are ready for independent re-review.
```

Do not reproduce TASK, Evidence, or History contents.

---

### 13.2 Not ready

Return:

```text
# Fix Result — <TASK_ID>

Status: NOT READY FOR INDEPENDENT RE-REVIEW

Blocking:
- <blocking reason>

Findings:
- <finding ID>: FIXED | NOT REPRODUCIBLE | BLOCKED

Validation:
- <relevant failures only>

Evidence:
- <status if relevant>

Git history:
- NO HISTORY ACTION REQUIRED | HISTORY ACTION REQUIRED

Context expansion:
- Trigger(s):
- Conditional Sources loaded:

<TASK_ID> fixes are NOT ready for independent re-review.
```

Include only information needed to resolve remaining blockers.

---

## 14. Efficiency Rules

Default path:

```text
read TASK
→ read latest blocking Review findings
→ read Required Sources
→ inspect finding-related code/tests
→ reproduce finding
→ minimal fix
→ focused regression proof
→ TASK-required validation
→ Evidence
→ Finding status
→ History
→ compact handoff
```

Exception path:

```text
detect anomaly
→ activate exact trigger
→ read matching Conditional Source only
→ investigate affected area only
→ return to Fix path
```

Do not default to:

```text
rerun complete Read-only Review
```

Do not default to:

```text
read every project Context / Plan / ADR / Architecture document
```

Do not default to:

```text
full repository diff
```

Do not default to:

```text
full regression
```

Do not default to:

```text
Git-history analysis
```

Prefer:

```text
minimum sufficient corrective context
```

Keep:

```text
Do not stage or commit.
```

Ready:

```text
WORKFLOW_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","stage":"fix","status":"READY_FOR_RE_REVIEW","workflow_complete":true}
```

Not ready, workflow bookkeeping complete:

```text
WORKFLOW_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","stage":"fix","status":"NOT_READY_FOR_RE_REVIEW","workflow_complete":true}
```

Mandatory Evidence/history/finalization failed:

```text
WORKFLOW_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","stage":"fix","status":"NOT_READY_FOR_RE_REVIEW","workflow_complete":false}
```

while preserving correctness and independent re-reviewability.

Begin the corrective workflow for the TASK identifier supplied in the current user message.