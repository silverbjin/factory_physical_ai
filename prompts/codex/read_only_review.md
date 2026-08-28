# Common Read-only Review Prompt

## Purpose

This file defines the reusable independent **READ-ONLY REVIEW** procedure for implementation tasks in this repository.

The task to review is supplied by the user's current Codex message.

Typical invocation:

```text
TASK-MVP-002
```

or:

```text
TASK-W2-001
```

When this review procedure is invoked, treat the exact task identifier from the current user message as `TASK_ID`.

---

## 1. Target Task Resolution

1. Extract exactly one task identifier from the current user message.
2. Set that identifier as `TASK_ID`.
3. Do not ask the user to repeat information that can be located in the repository.
4. Locate the specification, backlog entry, plan, context, contracts, ADRs, tests, and evidence relevant to `TASK_ID`.
5. Infer the next task only when needed to detect scope leakage. Never implement it.

If no valid task identifier can be determined, stop and report that the review target is unresolved.

---

## 2. Reviewer Role

Act as an **independent read-only reviewer**, not as the implementer.

Your responsibility is to determine whether `TASK_ID` can safely be accepted before the next task begins.

Judge the implementation against frozen requirements and contracts.

Do not reinterpret requirements merely to match the implementation.

---

## 3. Strict Read-only Rules

This is a **READ-ONLY REVIEW**.

You MUST NOT:

- modify repository files;
- create implementation files;
- create or update tests;
- create or update evidence;
- update documentation, except for the explicit TASK history audit-log write exception defined below;
- run formatters or linters in auto-fix mode;
- install dependencies unless the repository explicitly defines a non-mutating review procedure;
- stage files;
- commit changes;
- reset, checkout, restore, clean, stash, or otherwise alter Git state;
- implement `TASK_ID`;
- implement any later task;
- proactively fix findings.

You MAY:

- inspect files;
- inspect Git state and diffs;
- inspect frozen context, plans, backlog, contracts, schemas, and ADRs;
- run tests;
- run syntax/static checks that do not modify tracked or untracked repository contents;
- calculate hashes;
- inspect evidence;
- run read-only Git commands;
- report recommended remediation without applying it.

If a command may mutate the repository, do not run it.

Preserve all pre-existing user changes.

### 3.1 TASK History Audit-log Write Exception

The review itself remains strictly read-only for all implementation and source-of-truth surfaces.

Only **after the review decision and final `ACCEPT` / `REJECT` recommendation have been determined**, you MAY write the review audit record defined by:

```text
prompts/codex/task_history_recording.md
```

Before starting the review, read `prompts/codex/task_history_recording.md` in full.

The audit-log write exception permits creating or updating only:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
docs/task_history/<TASK_ID>/README.md
docs/task_history/README.md
```

No other repository mutation is permitted.

The following remain strictly read-only even when recording review history:

- source code;
- tests;
- evidence under `results/` or equivalent evidence directories;
- contracts;
- schemas;
- ADRs;
- architecture documents;
- plans;
- task specifications;
- Git index;
- Git history;
- unrelated documentation.

The review history must be written **after** the independent review conclusion is complete.

Do not use the newly written review history as evidence or as a source of truth for the same review.

The review-history write is an audit-log side effect only and must never change the review conclusion.

---

## 4. Scope Boundary

Review only `TASK_ID`.

Verify that:

1. every required behavior for `TASK_ID` is implemented;
2. no required behavior is missing;
3. implementation does not exceed task scope without a necessary architectural reason;
4. functionality assigned to later tasks was not prematurely implemented;
5. unrelated repository files were not modified;
6. frozen architectural boundaries remain intact.

Small structural preparation for later work is acceptable only when it is required to implement `TASK_ID` cleanly and does not introduce later-task behavior.

---

## 5. Sources of Truth

Before judging code, locate and inspect all applicable sources of truth.

Search the repository rather than assuming fixed filenames.

Inspect when present:

- project implementation context;
- MVP / phase / week context;
- MVP / phase / week plan;
- task backlog;
- the exact `TASK_ID` definition;
- acceptance criteria;
- exit criteria;
- frozen contracts;
- schemas;
- ADRs / architecture decisions;
- public interface definitions;
- previous-task evidence that constrains this task;
- repository-level development and testing rules;
- applicable `AGENTS.md` instructions.

Also read:

```text
prompts/codex/task_history_recording.md
```

This file defines only how the completed review is persisted for portfolio/audit purposes.

It is **not** a source of truth for implementation correctness, task requirements, contract interpretation, or acceptance decisions.

When requirements conflict, use this priority unless the repository explicitly defines another hierarchy:

1. Explicit frozen contract or architecture decision
2. Explicit `TASK_ID` acceptance / exit criteria
3. Current phase / MVP / week plan
4. Current phase / MVP / week context
5. General repository conventions
6. Implementation

Do not treat implementation as a source of truth for its own requirements.

Report unresolved specification conflicts.

---

## 6. Repository State Review

Use read-only Git inspection.

At minimum, when valid for the repository, inspect:

```bash
git status --short
git diff --stat
git diff
git diff --check
```

If staged changes exist, also inspect:

```bash
git diff --cached --stat
git diff --cached
```

Determine:

- all changed files;
- tracked versus untracked changes;
- whether each change belongs to `TASK_ID`;
- whether unrelated user changes were preserved;
- whether generated artifacts were mixed into source changes unexpectedly;
- whether later-task files were modified.

Do not alter repository state to make the review easier.

When evaluating repository cleanliness and scope, distinguish pre-existing TASK history files from implementation changes.

Files under:

```text
docs/task_history/
```

that were created by prior workflow runs are audit records and must not be mistaken for implementation scope expansion.

However, unexpected or manually altered TASK history files may still be reported when they create provenance or audit-integrity concerns.

---

## 7. Requirement Traceability

Build a requirement traceability map before issuing the final recommendation.

For every explicit `TASK_ID` requirement, identify:

- source requirement;
- implementation file and symbol;
- test that verifies it;
- evidence entry when evidence is required;
- PASS / FAIL status.

Use this chain:

```text
Requirement
    ↓
Implementation
    ↓
Test
    ↓
Evidence
```

A requirement with no implementation, no meaningful verification, or false evidence is not complete.

TASK history documents under `docs/task_history/` are not substitutes for implementation evidence and must not be used to satisfy this traceability chain.

---

## 8. Implementation Review

Review correctness before style.

### 8.1 Contract compliance

Verify all relevant frozen:

- field names;
- field sets;
- required / optional fields;
- data types;
- enums;
- state names;
- API signatures;
- public imports;
- message schemas;
- return semantics;
- error semantics;
- idempotency rules;
- retry rules;
- persistence boundaries;
- ownership boundaries.

Passing tests do not excuse a frozen contract violation.

### 8.2 Fail-closed behavior

Look for invalid or ambiguous paths that could be silently accepted.

Check for:

- permissive defaults;
- silent fallbacks;
- swallowed exceptions;
- implicit success;
- invalid enum or state acceptance;
- missing validation;
- caller-controlled safety invariants;
- bypassable guards;
- unbounded retries;
- partially initialized objects;
- ambiguous `None`, empty, or default behavior.

Safety-sensitive and stateful behavior should fail closed unless the specification explicitly requires otherwise.

### 8.3 State / lifecycle invariants

When applicable, verify:

- state set is finite where required;
- transitions are explicit;
- illegal transitions are rejected;
- terminal states remain terminal where required;
- unknown or ambiguous outcomes cannot silently become success;
- retry counts are actually bounded;
- reconciliation is distinct from success;
- recovery behavior is explicit;
- escalation / HITL is reachable where required;
- alternate APIs cannot bypass invariants.

### 8.4 Determinism

When deterministic behavior is required, check for:

- random behavior;
- wall-clock dependence;
- hidden global state;
- unordered iteration affecting output;
- environment-dependent branching;
- shared mutation between calls.

Equivalent inputs and equivalent state should produce equivalent decisions where required.

### 8.5 Immutability and mutation

When immutable models or state are required, inspect:

- mutable default arguments;
- exposed mutable collections;
- aliasing;
- in-place mutation;
- shared object references;
- dataclass / model configuration;
- copied versus shared structures.

### 8.6 Boundary ownership

Verify that `TASK_ID` does not take ownership of components explicitly assigned to other tasks.

Examples include:

- ROS execution;
- real robot execution;
- VLA inference;
- agent orchestration;
- persistence;
- databases;
- Docker;
- observability;
- Grafana;
- networking;
- multi-agent execution;
- external APIs.

Treat premature implementation as a scope finding unless explicitly required.

---

## 9. Test Review

Do not judge test adequacy from pass counts alone.

Inspect the tests themselves.

Verify meaningful coverage of:

### Happy paths

Required valid behavior succeeds.

### Negative paths

Invalid inputs, illegal transitions, rejected contracts, or prohibited behavior fail correctly.

### Boundaries

Test applicable limits such as:

- minimum / maximum;
- empty / null;
- unknown;
- duplicates;
- retry exhaustion;
- terminal states;
- malformed values.

### Invariants

Important architecture, safety, state, and contract properties have explicit regression tests.

### Failure paths

When relevant, inspect tests for:

- timeout;
- unknown result;
- partial failure;
- retry exhaustion;
- reconciliation;
- recovery;
- escalation;
- malformed input;
- duplicate request;
- unexpected state.

### Regression

Identify and run the repository-defined focused test suite for `TASK_ID`.

Also run the full regression suite when feasible.

Use repository-defined commands when available.

Otherwise use suitable non-mutating commands such as:

```bash
python3 -m pytest <focused-tests> -vv
python3 -m pytest -vv
python3 -m compileall -q src tests
```

Prevent generated cache files from contaminating repository state when necessary.

If a test cannot be run, state why. Do not claim PASS.

---

## 10. Evidence Review

Locate the evidence artifact for `TASK_ID` when the task requires one.

Do not assume the exact path; search expected result/evidence directories and task documents.

Verify:

- correct task identity;
- correct status;
- actual changed-file list;
- actual test commands;
- actual test results;
- actual acceptance / exit criteria;
- source hashes when present;
- timestamps or provenance when required;
- reproducibility sufficient for later audit.

Recompute hashes independently when practical.

Do not trust `"PASS"` merely because it is present in JSON or another generated artifact.

Evidence must describe the repository that was actually reviewed.

TASK history documents are human-readable audit records and are not implementation evidence unless the task specification explicitly defines otherwise.

---

## 11. Previous-task Compatibility

Inspect prior frozen outputs that constrain `TASK_ID`.

Verify that the current implementation does not break:

- earlier contracts;
- schemas;
- public imports;
- APIs;
- naming explicitly frozen by prior work;
- architecture boundaries;
- prior evidence assumptions;
- existing regression behavior.

A later task must not silently redefine an earlier frozen contract.

---

## 12. Next-task Leakage

Determine the task that follows `TASK_ID` only when needed for scope analysis.

Identify functionality currently present that belongs to later work.

Classify each case as:

- harmless preparation;
- necessary architectural prerequisite;
- unnecessary premature implementation;
- scope violation.

Do not implement or modify the next task.

---

## 13. Code Quality Review

Report code-quality issues only when they materially affect:

- correctness;
- maintainability;
- testability;
- architecture;
- future task integration.

Check for:

- unclear public API;
- duplicated domain rules;
- hidden coupling;
- overly large functions/classes;
- ambiguous names;
- dead or unreachable code;
- duplicated constants;
- inconsistent exception semantics;
- insufficient type clarity;
- circular dependency risk;
- fragile imports.

Do not block acceptance for cosmetic preferences alone.

---

## 14. Severity Classification

Classify every finding as exactly one of:

### BLOCKER

The task cannot safely be accepted.

Examples:

- core requirement missing;
- frozen contract violation that invalidates the task;
- critical invariant bypassable;
- tests or evidence fundamentally unreliable;
- repository/scope corruption affecting subsequent tasks.

### HIGH

Normally must be fixed before starting the next task.

Examples:

- incorrect failure semantics;
- important untested invariant;
- significant scope violation;
- retry/reconciliation/state safety defect;
- materially false evidence.

### MEDIUM

Should be corrected, but may be explicitly deferred when it does not make progression unsafe.

Examples:

- meaningful edge case gap;
- maintainability risk;
- incomplete defensive validation;
- non-critical test gap.

### LOW

Minor issue that does not block acceptance by itself.

Examples:

- small naming inconsistency;
- low-risk documentation gap;
- minor test readability issue.

Do not inflate severity.

---

## 15. Required Review Output

Return the review in this structure.

# Read-only Review — `TASK_ID`

## 1. Review Summary

- Task:
- Review mode: READ-ONLY
- Files changed:
- Focused tests:
- Regression tests:
- Evidence:
- Overall recommendation:

## 2. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| ... | ... | ... | ... | PASS/FAIL |

Use the actual requirements of `TASK_ID`.

## 3. Findings

Report findings in severity order.

### BLOCKER

For each finding:

- **ID:** `<TASK_ID>-REV-B01`
- **File / Symbol:**
- **Issue:**
- **Why it matters:**
- **Requirement / Contract affected:**
- **Evidence:**
- **Recommended remediation:**

If none:

`No BLOCKER findings.`

### HIGH

Use the same format.

If none:

`No HIGH findings.`

### MEDIUM

Use the same format.

If none:

`No MEDIUM findings.`

### LOW

Use the same format.

If none:

`No LOW findings.`

## 4. Scope Review

Report:

- required scope implemented: PASS/FAIL
- unrelated changes: PASS/FAIL
- next-task leakage: PASS/FAIL
- frozen boundaries preserved: PASS/FAIL

Explain every failure.

## 5. Contract Review

Report:

- contract compliance: PASS/FAIL
- prior-task compatibility: PASS/FAIL
- public interface compatibility: PASS/FAIL

List frozen sources checked.

## 6. Test Adequacy

Report:

- happy paths: PASS/FAIL
- invalid paths: PASS/FAIL
- boundary cases: PASS/FAIL
- invariant coverage: PASS/FAIL
- focused suite: PASS/FAIL/NOT RUN
- full regression: PASS/FAIL/NOT RUN

List important missing scenarios.

## 7. Evidence Integrity

Report:

- evidence exists: PASS/FAIL/NOT APPLICABLE
- task identity correct: PASS/FAIL/NOT APPLICABLE
- changed-file list correct: PASS/FAIL/NOT APPLICABLE
- test claims verified: PASS/FAIL/NOT APPLICABLE
- exit criteria verified: PASS/FAIL/NOT APPLICABLE
- hashes verified: PASS/FAIL/NOT APPLICABLE

## 8. Acceptance Gates

Report exactly:

```text
Scope compliance: PASS/FAIL
Requirement compliance: PASS/FAIL
Contract compliance: PASS/FAIL
State / invariant safety: PASS/FAIL/NOT APPLICABLE
Test adequacy: PASS/FAIL
Regression safety: PASS/FAIL
Evidence integrity: PASS/FAIL/NOT APPLICABLE
```

## 9. Final Recommendation

Return exactly one:

```text
ACCEPT <TASK_ID>
```

or:

```text
REJECT <TASK_ID>
```

Policy:

- Any BLOCKER → REJECT
- Any unresolved HIGH → normally REJECT
- MEDIUM → explicitly state whether safe to defer
- LOW → does not block acceptance by itself

Then briefly state the reason.

### 15.1 Persist Review History

Only after the complete review output above has been determined, persist the review result according to:

```text
prompts/codex/task_history_recording.md
```

Determine the next sequential history number `SEQ` from:

```text
docs/task_history/<TASK_ID>/
```

Then create:

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
```

and update:

```text
docs/task_history/<TASK_ID>/README.md
docs/task_history/README.md
```

Recording requirements:

- use Korean for portfolio-readable explanations when English is not required;
- preserve exact English technical identifiers, paths, commands, error messages, contract/schema fields, state names, severity names, and `PASS` / `FAIL` / `ACCEPT` / `REJECT`;
- record the actual review result, including rejected reviews;
- never delete or overwrite an earlier review/fix/implementation history entry;
- preserve chronological sequence;
- include Requirement Traceability, Findings, Acceptance Gates, and Final Recommendation;
- include a concise Korean explanation of the most important engineering risks or lessons learned;
- do not convert a `REJECT` into a softer status for portfolio presentation;
- do not modify implementation, tests, evidence, or source-of-truth documents while recording history.

If history recording itself fails, do not change the already-determined technical recommendation.

Report the history-write failure separately.

---

## 16. Final Constraints

Remember:

- read only for implementation and source-of-truth surfaces;
- no fixes;
- no repository mutations except the explicit TASK history audit-log write exception;
- no next-task implementation;
- no staging or commits;
- passing tests alone are not proof of correctness;
- generated evidence must be independently verified;
- implementation must be judged against frozen specification;
- use concrete file, symbol, contract, and requirement references;
- report unavailable information instead of guessing;
- read and follow `prompts/codex/task_history_recording.md`;
- determine the review conclusion before writing TASK history;
- TASK history is an audit record, not a source of truth or implementation evidence.

Begin the independent READ-ONLY review of the task identifier supplied in the current user message.
