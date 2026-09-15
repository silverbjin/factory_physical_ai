# Common Task Implementation Prompt v2.1

## Purpose

Implement exactly one repository task identified by the user's current Codex message.

Typical invocation:

```text
Implement TASK-MVP-003
```

Extract exactly one task identifier and treat it as `TASK_ID`.

If exactly one valid `TASK_ID` cannot be resolved, stop and report:

```text
TASK_ID unresolved.
```

---

## 1. Core Rules

For `TASK_ID`:

1. implement only the target task;
2. verify mandatory prerequisites before editing;
3. preserve frozen contracts and architecture;
4. preserve unrelated user changes;
5. make the smallest correct change;
6. run only required validation;
7. evaluate Exit Criteria;
8. generate required Evidence truthfully;
9. record mandatory TASK history after technical validation;
10. do not start later tasks;
11. do not stage or commit unless explicitly requested;
12. do not perform the independent acceptance review.

Implementation completion and independent Review acceptance are separate states.

---

## 2. Context Loading Policy

Minimize context aggressively while preserving correctness.

The normal path is:

```text
TASK specification
→ Required Sources
→ target code/tests
→ implementation
```

Conditional Sources are exception-path context.

Do not read them preemptively.

---

### 2.1 Initial load

Locate and read only:

- applicable `AGENTS.md`;
- exact `TASK_ID` specification.

Do not begin with repository-wide search.

---

### 2.2 Required Sources

From:

```text
## Authoritative Sources
### Required
```

read every listed Required Source.

Read no other project Context, Plan, Backlog, Architecture, ADR, contract, schema, prior TASK, or Evidence unless:

- it is a Required Source; or
- a Conditional Source trigger becomes true.

Required Sources define the default implementation context.

---

### 2.3 Conditional Sources

Do NOT read:

```text
## Authoritative Sources
### Conditional
```

during the normal path.

Load a Conditional Source only when one of its declared `Read when` triggers actually occurs.

Supported trigger categories may include:

```text
MISSING_REFERENCE
PREREQUISITE_UNCLEAR
REQUIREMENT_AMBIGUITY
SOURCE_CONFLICT
ARCHITECTURE_CONFLICT
CONTRACT_CONFLICT
UNEXPECTED_CODE_STRUCTURE
VALIDATION_FAILURE
REGRESSION_FAILURE
EVIDENCE_FAILURE
UNEXPECTED_REPOSITORY_CHANGE
```

A trigger is considered active only when there is concrete evidence of that condition.

Do not activate a trigger merely because additional context might be useful.

---

### 2.4 Trigger handling

When a trigger occurs:

1. identify the exact trigger;
2. load only Conditional Sources mapped to that trigger;
3. attempt to resolve the issue;
4. stop loading additional context once resolved.

Example:

```text
VALIDATION_FAILURE
→ read only Conditional Sources whose Read when includes VALIDATION_FAILURE
→ diagnose
→ continue if resolved
```

Do not automatically load all Conditional Sources after one failure.

---

### 2.5 Escalation beyond declared sources

Broader repository search is a last resort.

Use this order:

```text
TASK specification
→ Required Sources
→ matching Conditional Sources
→ narrowly related file search
→ directly related parent Context / Plan
→ directly relevant Architecture / ADR / Contract
→ broader repository search
```

Stop expansion immediately when sufficient information is available.

If safe implementation remains materially ambiguous or conflicting, stop and report the blocker.

---

## 3. Preflight

Before editing, run:

```bash
git status --short
git diff --stat
```

Preserve all pre-existing user changes.

Never reset, restore, clean, checkout, stash, overwrite, or delete unrelated user work.

Do not run full `git diff` by default.

Inspect detailed diffs only for:

- target files with pre-existing changes;
- unexpected repository changes;
- files relevant to a concrete conflict.

Prefer:

```bash
git diff -- <relevant-path>
```

over repository-wide diff output.

Verify mandatory dependencies declared by the TASK.

Use the dependency's declared verification source.

If prerequisite status is unclear:

```text
activate PREREQUISITE_UNCLEAR
```

and load only matching Conditional Sources.

If the prerequisite still cannot be verified, stop.

---

## 4. Implementation

Implement the smallest solution satisfying `TASK_ID`.

Follow:

- TASK requirements;
- Required Sources;
- loaded Conditional Sources, if any;
- frozen references;
- Scope;
- Non-goals;
- ownership boundaries;
- validation policy;
- Exit Criteria.

Do not:

- implement later tasks;
- add future functionality for convenience;
- modify unrelated modules;
- rewrite frozen contracts without authorization;
- perform unrelated refactoring.

If target code structure differs materially from the TASK specification:

```text
activate UNEXPECTED_CODE_STRUCTURE
```

before expanding the implementation scope.

---

## 5. Validation

Run only validation required by the TASK.

Prefer concise successful output.

General rule:

```text
PASS → concise output
FAIL → targeted detailed output
```

---

### 5.1 Focused validation

Run the task-defined focused validation.

If it passes, do not run additional diagnostic commands without reason.

If it fails:

```text
activate VALIDATION_FAILURE
```

Read only matching Conditional Sources if required for diagnosis.

Inspect detailed test output only for the failing target.

---

### 5.2 Regression

Follow the TASK regression policy exactly:

```text
REQUIRED
NOT REQUIRED
CONDITIONAL
```

If `CONDITIONAL`, run regression only when the TASK-defined condition is met.

If required regression fails:

```text
activate REGRESSION_FAILURE
```

and use matching Conditional Sources as necessary.

---

### 5.3 Repository checks

Before technical completion, run:

```bash
git status --short
git diff --stat
git diff --check
```

If unexpected changes appear:

```text
activate UNEXPECTED_REPOSITORY_CHANGE
```

Investigate only the affected paths first.

---

## 6. Exit Criteria and Evidence

Evaluate each TASK Exit Criterion as:

```text
PASS
FAIL
NOT APPLICABLE
```

Tests passing alone do not establish completion.

If Evidence is required, generate it according to the declared path/schema.

Never fabricate:

- tests;
- hashes;
- timestamps;
- changed files;
- prerequisites;
- Exit Criteria;
- Evidence values.

If Evidence generation or validation fails:

```text
activate EVIDENCE_FAILURE
```

Read only relevant Conditional Sources if required.

Determine:

```text
Technical implementation: COMPLETE
```

or:

```text
Technical implementation: INCOMPLETE
```

---

## 7. TASK History

Only after technical validation and Evidence resolution, read:

```text
prompts/codex/task_history_recording.md
```

This file is the authoritative TASK-history policy.

Do not load it during initial implementation context unless another repository rule explicitly requires it earlier.

Record the workflow under:

```text
docs/task_history/<TASK_ID>/
```

Do not represent implementation completion as independent Review acceptance.

If history recording fails:

```text
Technical implementation: COMPLETE|INCOMPLETE
Workflow history recording: FAIL
```

The overall workflow remains incomplete.

---

## 8. Final Status

A TASK is complete only when:

- mandatory prerequisites pass;
- target requirements are implemented;
- no later TASK is started;
- required validation passes;
- Exit Criteria pass;
- required Evidence is valid;
- mandatory TASK history succeeds.

---

### 8.1 Successful run

Return only a compact result:

```text
# Implementation Result — <TASK_ID>

Status: COMPLETE

Changed:
- <task-related implementation/test files>

Validation:
- focused: PASS
- regression: PASS | NOT REQUIRED
- Exit Criteria: PASS

Evidence:
- <path | NOT REQUIRED>

History:
- <implementation history path>

Context:
- Required Sources: <count>
- Conditional Sources loaded: <count>

Review:
- Independent Read-only Review pending

Recommended commit:
<Conventional Commit message>

<TASK_ID> is complete.
```

Do not reproduce TASK, Evidence, or History content.

---

### 8.2 Incomplete run

Return only information required to resolve the blocker:

```text
# Implementation Result — <TASK_ID>

Status: INCOMPLETE

Blocking:
- <reason>

Trigger:
- <trigger if applicable>

Conditional Sources loaded:
- <paths or NONE>

Technical implementation:
- COMPLETE | INCOMPLETE

Validation:
- <relevant failure only>

Evidence:
- <status if relevant>

History:
- <status if relevant>

<TASK_ID> is NOT complete.
```

---

## 9. Efficiency Rules

Default behavior:

```text
read TASK
→ read Required Sources
→ inspect target code
→ implement
→ focused validation
→ Evidence
→ History
→ compact report
```

Exception behavior:

```text
problem detected
→ activate exact trigger
→ read matching Conditional Source only
→ resolve
→ return to normal path
```

Never use:

```text
read all potentially relevant documents first
```

as a default strategy.

Prefer:

```text
minimum sufficient context
```

over:

```text
maximum available context
```

Begin implementation of the TASK identifier supplied in the current user message.