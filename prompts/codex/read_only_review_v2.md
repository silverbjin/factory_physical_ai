# Common Read-only Review Prompt v2

## Orchestration Output Contract — MANDATORY

This workflow may run standalone or as a child of `scripts/codex/run_task_orchestrator.py`.

For orchestrated execution, the final response **MUST end with exactly one**
`WORKFLOW_RESULT_JSON` line. A prose-only `ACCEPT` or `REJECT` is invalid.

ACCEPT:

```text
WORKFLOW_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","stage":"review","status":"ACCEPT","workflow_complete":true}
```

REJECT:

```text
WORKFLOW_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","stage":"review","status":"REJECT","workflow_complete":true}
```

If mandatory Review-history/finalization fails, preserve the technically determined
`status` (`ACCEPT` or `REJECT`) but set:

```text
"workflow_complete": false
```

Rules:

- never omit the marker;
- the marker must be the **last non-empty line** of the final response;
- keep `REVIEW_METRICS_JSON` separate when telemetry is enabled;
- if an acceptance handoff is emitted, place it **before** the final `WORKFLOW_RESULT_JSON`;
- do not stage or commit.

## Purpose

Perform an independent review of exactly one implementation TASK identified by the user's current Codex message.

Typical invocation:

```text
TASK-MVP-003
```

Extract exactly one task identifier and treat it as `TASK_ID`.

If exactly one valid TASK cannot be resolved, stop and report:

```text
TASK_ID unresolved.
```

The review must determine whether `TASK_ID` is safe to accept before subsequent work proceeds.

---

## 1. Core Review Rules

For `TASK_ID`:

1. act as an independent reviewer, not the implementer;
2. judge implementation against the TASK specification and frozen sources;
3. review only the target TASK;
4. do not modify implementation, tests, Evidence, contracts, schemas, TASK specifications, architecture, plans, or Git state;
5. do not proactively fix findings;
6. preserve all pre-existing user changes;
7. verify requirements through implementation, tests, and Evidence;
8. do not treat passing tests alone as proof of correctness;
9. do not treat implementation as the source of its own requirements;
10. write TASK history only after the technical review decision is fixed;
11. TASK history is an audit record, not implementation Evidence;
12. do not stage or commit changes.

The only allowed repository write is the post-decision TASK-history recording defined in Section 9.

---

## 2. Context Loading Policy

Use the minimum sufficient review context.

Normal review path:

```text
TASK specification
→ Required Sources
→ Change Set
→ changed/relevant implementation
→ changed/relevant tests
→ required validation
→ declared Evidence
→ review decision
```

Do not perform repository-wide discovery by default.

---

### 2.1 Initial sources

Locate and read:

- applicable `AGENTS.md`;
- exact `TASK_ID` specification.

From the TASK specification, read every source under:

```text
## Authoritative Sources
### Required
```

Do not automatically read:

- parent Context;
- Plan;
- Backlog;
- unrelated Architecture;
- unrelated ADRs;
- previous TASK specifications;
- next TASK specifications;
- previous Evidence;
- Conditional Sources.

---

### 2.2 Conditional Sources

Sources under:

```text
## Authoritative Sources
### Conditional
```

must not be read during the normal review path.

Load a Conditional Source only after a concrete anomaly activates a relevant trigger.

Do not load all Conditional Sources merely because one anomaly exists.

---

### 2.3 Review anomaly triggers

Use the following trigger categories when applicable:

```text
CHANGESET_UNCLEAR
UNEXPECTED_REPOSITORY_CHANGE
SCOPE_LEAKAGE
REQUIREMENT_AMBIGUITY
SOURCE_CONFLICT
CONTRACT_CONFLICT
TRACEABILITY_GAP
TEST_COVERAGE_GAP
VALIDATION_FAILURE
REGRESSION_FAILURE
EVIDENCE_MISSING
EVIDENCE_MISMATCH
PRIOR_COMPATIBILITY_UNCLEAR
NEXT_TASK_BOUNDARY_UNCLEAR
```

When a trigger occurs:

1. identify the exact trigger;
2. load only matching Conditional Sources;
3. investigate only the affected requirement/file/test/evidence area;
4. stop expanding context once the issue is resolved.

If the declared Conditional Sources are insufficient, escalate narrowly:

```text
matching Conditional Sources
→ directly related repository search
→ directly related parent Context / Plan
→ directly relevant Architecture / ADR / Contract
→ broader repository search
```

Broader repository search is a last resort.

---

## 3. Review Target and Change Set

Before detailed code review, establish what implementation is being reviewed.

### 3.1 Change inventory

Start with non-mutating Git inspection:

```bash
git status --short
git diff --name-status
git diff --stat
```

If staged changes exist, also inspect:

```bash
git diff --cached --name-status
git diff --cached --stat
```

Do not read the complete repository diff by default.

Identify:

- TASK-related implementation files;
- TASK-related test files;
- Evidence files;
- pre-existing unrelated changes;
- unexpected changed files.

TASK-history files from prior workflow runs are audit records and are not implementation scope by themselves.

---

### 3.2 Detailed diff policy

Inspect detailed diffs only for files relevant to `TASK_ID`.

Prefer:

```bash
git diff -- <path>
```

or the equivalent review range for the known implementation commit.

Do not run full:

```bash
git diff
```

unless required to resolve:

```text
CHANGESET_UNCLEAR
UNEXPECTED_REPOSITORY_CHANGE
SCOPE_LEAKAGE
```

---

### 3.3 Committed implementation

If the TASK specification, Evidence, or repository state clearly identifies an implementation commit or base range, review that change range.

If the reviewed implementation cannot be reliably identified from the TASK, Evidence, working tree, or a narrow Git-history inspection:

```text
activate CHANGESET_UNCLEAR
```

Do not guess the implementation range.

---

## 4. Review Procedure

Review correctness before style.

Use the TASK specification as the review checklist.

---

### 4.1 Scope review

Verify:

- every required Scope item is implemented;
- no required behavior is missing;
- declared Non-goals were not implemented;
- unrelated files were not modified without justification;
- frozen ownership boundaries remain intact.

Do not inspect the next TASK by default.

If changed behavior cannot be classified using Scope and Non-goals:

```text
activate NEXT_TASK_BOUNDARY_UNCLEAR
```

Only then inspect directly relevant future-plan information.

---

### 4.2 Requirement traceability

For every explicit TASK requirement (`R1`, `R2`, ...), establish:

```text
Requirement
→ Implementation
→ Test
→ Evidence, when required
```

Record for each requirement:

- implementation file/symbol;
- meaningful test;
- Evidence entry if applicable;
- PASS / FAIL.

A requirement is not complete if its implementation or meaningful verification is missing.

If the chain cannot be established:

```text
activate TRACEABILITY_GAP
```

TASK-history documents must never satisfy this chain.

---

### 4.3 Frozen reference review

Verify every TASK-relevant Frozen Reference against the changed implementation.

Check only contract properties applicable to this TASK, such as:

- public fields or schema;
- API/signature;
- state/lifecycle semantics;
- error semantics;
- retry/idempotency behavior;
- ownership boundary;
- Evidence schema.

Do not run generic contract checklists unrelated to the TASK.

If Frozen Sources conflict or interpretation is materially unclear:

```text
activate CONTRACT_CONFLICT
```

Passing tests do not override a frozen contract violation.

---

### 4.4 Invariant and failure review

Review state, safety, determinism, mutation, retry, reconciliation, or failure semantics only when required by:

- TASK Requirements;
- Frozen References;
- loaded authoritative sources.

Do not apply unrelated generic safety checklists.

Where such behavior is required, verify that invalid or ambiguous paths cannot silently violate the declared invariant.

---

### 4.5 Test adequacy

Inspect the tests that directly verify TASK Requirements.

Always inspect:

- tests added or changed for `TASK_ID`;
- existing tests directly referenced by the TASK;
- tests used as requirement proof.

Verify meaningful coverage of the required:

- valid behavior;
- rejected/invalid behavior;
- relevant boundaries;
- invariants;
- failure behavior.

Do not inspect the entire regression suite source by default.

If meaningful requirement coverage is missing:

```text
activate TEST_COVERAGE_GAP
```

---

### 4.6 Code quality

Report code-quality findings only when they materially affect:

- correctness;
- maintainability;
- testability;
- architecture;
- future TASK integration.

Do not block acceptance for cosmetic style preferences alone.

---

## 5. Validation

Run only non-mutating validation required by the TASK.

Follow the TASK's declared validation policy.

---

### 5.1 Focused validation

Run the declared focused validation.

Prefer concise successful output.

General rule:

```text
PASS → concise output
FAIL → targeted verbose output
```

If focused validation fails:

```text
activate VALIDATION_FAILURE
```

Inspect detailed output only for failing tests/checks.

Do not claim PASS for commands that were not run.

---

### 5.2 Regression

Follow the TASK regression declaration exactly:

```text
REQUIRED
NOT REQUIRED
CONDITIONAL
```

If `REQUIRED`, run it.

If `NOT REQUIRED`, do not run it merely because a full suite exists.

If `CONDITIONAL`, evaluate only the TASK-declared condition.

If required regression fails:

```text
activate REGRESSION_FAILURE
```

Investigate the failing area only.

---

### 5.3 Repository mutation safety

Do not run validation commands known to rewrite source files or tracked repository content.

Avoid auto-fix modes.

When a normally used validation command would create repository artifacts and the repository does not provide a safe non-mutating mode, report the limitation rather than altering repository state.

---

## 6. Evidence Review

If the TASK declares:

```text
Evidence required: YES
```

inspect the exact declared Evidence path.

Do not search evidence directories by default.

Verify only Evidence properties required by the TASK or frozen Evidence schema, including as applicable:

- TASK identity;
- changed-file claim;
- validation commands/results;
- Exit Criteria;
- required hashes/provenance;
- status.

Compare Evidence against independently observed repository and validation results.

Do not trust a stored `PASS` without verification.

Recompute hashes only when:

- the Evidence contract requires them;
- an Exit Criterion requires them; or
- an Evidence mismatch makes verification necessary.

If the declared Evidence does not exist:

```text
activate EVIDENCE_MISSING
```

If Evidence disagrees with reviewed reality:

```text
activate EVIDENCE_MISMATCH
```

TASK-history documents are not implementation Evidence unless a frozen specification explicitly says otherwise.

---

## 7. Findings and Acceptance

### 7.1 Severity

Classify each finding as exactly one:

```text
BLOCKER
HIGH
MEDIUM
LOW
```

Use these meanings:

```text
BLOCKER
The TASK cannot safely be accepted.

HIGH
Normally must be resolved before subsequent TASK work.

MEDIUM
May be deferred only when progression remains safe.

LOW
Non-blocking minor issue.
```

Do not inflate severity.

---

### 7.2 Acceptance Gates

Determine:

```text
Scope compliance: PASS/FAIL
Requirement compliance: PASS/FAIL
Contract compliance: PASS/FAIL
Invariant safety: PASS/FAIL/NOT APPLICABLE
Test adequacy: PASS/FAIL
Regression safety: PASS/FAIL/NOT APPLICABLE
Evidence integrity: PASS/FAIL/NOT APPLICABLE
```

Recommendation policy:

```text
Any BLOCKER → REJECT
Any unresolved HIGH → normally REJECT
MEDIUM → explicitly determine whether safe to defer
LOW → non-blocking by itself
```

The technical recommendation must be fixed before TASK history is written.

---

## 8. Review Output

Use a compact success path and detailed failure path.

---

### 8.1 ACCEPT output

If no blocking finding exists, return:

```text
# Read-only Review — <TASK_ID>

Recommendation: ACCEPT

Traceability:
- Requirements: <passed>/<total> PASS

Validation:
- focused: PASS
- regression: PASS | NOT REQUIRED
- Evidence: PASS | NOT APPLICABLE

Acceptance Gates:
- Scope: PASS
- Requirements: PASS
- Contract: PASS
- Invariants: PASS | NOT APPLICABLE
- Tests: PASS
- Regression: PASS | NOT APPLICABLE
- Evidence: PASS | NOT APPLICABLE

Findings:
- BLOCKER: 0
- HIGH: 0
- MEDIUM: <count>
- LOW: <count>

Conditional Sources loaded:
- <count>

ACCEPT <TASK_ID>
```

If MEDIUM or LOW findings exist, list them briefly with file/symbol and remediation.

Do not reproduce TASK, Evidence, tests, or authoritative sources unnecessarily.

---

### 8.2 REJECT output

If rejection is required, return:

```text
# Read-only Review — <TASK_ID>

Recommendation: REJECT

## Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| ... | ... | ... | ... | PASS/FAIL |

## Blocking Findings

### <SEVERITY> — <FINDING_ID>

- File / Symbol:
- Requirement / Contract:
- Issue:
- Evidence:
- Why it matters:
- Recommended remediation:

## Validation

- focused:
- regression:
- Evidence:

## Acceptance Gates

- Scope:
- Requirements:
- Contract:
- Invariants:
- Tests:
- Regression:
- Evidence:

## Context Expansion

- Trigger(s):
- Conditional Sources loaded:

REJECT <TASK_ID>
```

Include only findings relevant to the rejection or meaningful deferred risk.

---

## 9. TASK History

Only after `ACCEPT` or `REJECT` has been technically determined, read:

```text
prompts/codex/task_history_recording.md
```

Follow it as the authoritative audit-recording policy.

The review decision must not change because of TASK-history recording.

Only the TASK-history files permitted by that policy may be written.

Do not modify:

- implementation;
- tests;
- Evidence;
- contracts;
- schemas;
- TASK specification;
- architecture;
- plans;
- Git index;
- Git history;
- unrelated documentation.

If history recording fails, preserve the review recommendation and report separately:

```text
Review recommendation: ACCEPT|REJECT
Workflow history recording: FAIL
```

---

## 10. Efficiency Rules

Default:

```text
read TASK
→ read Required Sources
→ establish Change Set
→ inspect relevant code/tests
→ run required validation
→ verify declared Evidence
→ build traceability
→ decide
→ record History
→ compact report
```

On anomaly:

```text
detect anomaly
→ activate exact trigger
→ read matching Conditional Source only
→ investigate affected area only
→ return to review path
```

Do not default to:

```text
read every potentially relevant project document
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
verbose successful test output
```

Prefer:

```text
minimum sufficient independent evidence
```

Keep:

```text
Do not stage or commit.
```

The final response MUST follow the mandatory Orchestration Output Contract at the top of this file.

while preserving independent review quality.

Begin the independent READ-ONLY review of the TASK identifier supplied in the current user message.

---

## 11. Acceptance Recording Handoff

Return exactly one fenced YAML block:

acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: <TASK_ID>
  review_decision: ACCEPT | REJECT
  reviewed_commit: <40-character Git commit SHA>
  task_specific_decision: <exact task-specific decision or null>

  task_spec:
    path: <repository-relative TASK specification path>
    sha256: <sha256>

  evidence:
    required: true | false
    path: <repository-relative canonical evidence path or null>
    sha256: <sha256 or null>

  supporting_artifacts:
    - path: <repository-relative path>
      sha256: <sha256>
    # Use [] when none were independently verified.

  acceptance_recording_eligible: true | false
  blocking_reason: <null or concise reason>

**Rules:**

1. The reviewer remains READ-ONLY.

2. Never create/update results/reviews/*_acceptance.json.

3. reviewed_commit is the exact implementation commit reviewed.

4. Independently compute the TASK spec SHA-256.

5. If Evidence is required, independently compute its SHA-256.

6. task_specific_decision comes from verified canonical Evidence/report, never from the review recommendation.

7. ACCEPT + BLOCKED is valid. ACCEPT does not imply READY.

8. Set acceptance_recording_eligible=true only when:

-  Final Recommendation is exactly ACCEPT <TASK_ID>;

-  the reviewed commit is unambiguous;

-  required Evidence exists and its hash was independently verified;

-  the task-specific decision is unambiguous when defined by the TASK.

9. For REJECT, always set acceptance_recording_eligible=false.

10. If any required handoff fact is unavailable or ambiguous, eligibility is false.

11. supporting_artifacts includes only task-owned artifacts actually hash-verified during review.
