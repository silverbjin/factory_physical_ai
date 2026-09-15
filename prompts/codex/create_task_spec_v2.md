# TASK Specification Generation Prompt v2.1

## Purpose

Create exactly one implementation task specification:

```text
TASK-<PHASE>-<SEQ>.md
```

The generated TASK file will be executed with:

```text
prompts/codex/implement_task_v2.md
```

The TASK specification is the implementation agent's primary **context manifest + implementation specification**.

Its purpose is to let Codex normally operate through:

```text
TASK specification
→ Required Sources only
→ target code
→ implementation
```

and load additional project context only when a defined condition requires it:

```text
ambiguity / conflict / missing information / validation failure
→ matching Conditional Source
```

Do not implement the task.

Do not modify source code, tests, Evidence, or TASK history.

Create or update only the requested TASK specification unless explicitly instructed otherwise.

---

# 1. Target TASK

Create:

```text
<TASK_FILE_PATH>
```

for:

```text
TASK_ID = <TASK-ID>
```

Task title:

```text
<TASK_TITLE>
```

Task objective:

```text
<TASK_OBJECTIVE>
```

Task group:

```text
Phase / MVP / Week / Workstream:
<PHASE_OR_WORKSTREAM>
```

---

# 2. Source Resolution

Before writing the TASK specification, inspect only repository information necessary to define this task correctly.

Start with explicitly supplied sources.

## Source candidates

```text
<CONTEXT_PATH_OR_NONE>
<PLAN_PATH_OR_NONE>
<BACKLOG_PATH_OR_NONE>
<ARCHITECTURE_PATH_OR_NONE>
<RELATED_CONTRACT_PATHS_OR_NONE>
<RELATED_SCHEMA_PATHS_OR_NONE>
<RELATED_ADR_PATHS_OR_NONE>
<PREVIOUS_TASK_PATH_OR_NONE>
<PREVIOUS_EVIDENCE_PATH_OR_NONE>
```

Ignore non-applicable entries.

Use narrow repository search only when necessary to resolve a source required for the TASK specification.

Do not perform broad repository discovery merely to make the TASK specification more comprehensive.

---

# 3. Source Classification

Every implementation-relevant source must be classified as one of:

```text
Required Source
Conditional Source
```

Do not place the same source in both groups.

## 3.1 Required Sources

A source is `required` only if the implementation agent must read it during a normal successful implementation.

Typical reasons:

- it defines a frozen contract directly used by this TASK;
- it defines mandatory behavior not fully stated in the TASK;
- it contains a prerequisite result that must always be verified;
- it defines the schema required for implementation or Evidence;
- it defines architecture ownership directly affecting implementation.

Apply a strict test:

> If this source were not read, could a normal implementation reasonably violate this TASK?

If NO, it should normally not be `required`.

Keep this list as small as possible.

## 3.2 Conditional Sources

A source is `conditional` when it is unnecessary during the normal path but may become necessary to resolve a specific exception.

Every Conditional Source MUST define one or more explicit triggers.

Allowed trigger categories include:

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

Example:

```markdown
- `docs/mvp/day10_context.md`
  - Read when: `REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve task intent when the TASK specification and required contract do not sufficiently define expected behavior.
```

Do not classify a document as Conditional merely because it might be useful.

A trigger must correspond to a plausible failure or ambiguity path for this TASK.

---

# 4. TASK Specification Design Rules

The generated TASK must explicitly define:

1. identity and objective;
2. mandatory dependencies;
3. Required Sources;
4. Conditional Sources with triggers;
5. frozen references;
6. implementation scope;
7. explicit non-goals;
8. expected target areas;
9. functional requirements;
10. task-specific failure/safety behavior where applicable;
11. validation;
12. regression policy;
13. Evidence;
14. Exit Criteria;
15. workflow handoff.

Do not copy large parent documents into the TASK.

Prefer:

```text
precise requirement
+ exact source path
+ explicit load condition
```

over duplicated context.

---

# 5. Dependencies

Declare only dependencies that must be satisfied before this TASK can safely start.

For each dependency specify:

```text
- dependency identifier
- required state
- verification source
```

Example:

```text
- TASK-MVP-002
  Required state: ACCEPTED
  Verify from: results/mvp/MVP-002.json
```

If the verification source must always be read before implementation, include it under `Required Sources`.

If prerequisite status can normally be established without reading a larger parent document, place that larger document under `Conditional Sources` instead.

Do not infer that all earlier numbered TASKs are mandatory dependencies.

If there are none:

```text
None.
```

---

# 6. Authoritative Sources

Create two separate source groups.

## 6.1 Required Sources

Use this format:

```markdown
### Required

- `<path>`
  - Purpose: <why normal implementation requires this source>
```

Only list sources needed on the normal implementation path.

Target:

```text
0–5 Required Sources
```

where practical.

Do not list Context, Plan, Backlog, Architecture, or ADR documents by default.

## 6.2 Conditional Sources

Use:

```markdown
### Conditional

- `<path>`
  - Read when: `<TRIGGER>`
  - Purpose: <what uncertainty/failure this source resolves>
```

Multiple triggers may be used:

```text
Read when: REQUIREMENT_AMBIGUITY | SOURCE_CONFLICT
```

If no conditional sources are needed:

```text
None.
```

---

# 7. Frozen References

Explicitly identify interfaces that implementation must not silently alter.

Examples:

- schema fields;
- API signatures;
- state names;
- enum values;
- lifecycle semantics;
- Evidence schemas;
- ownership rules.

Use exact paths and identifiers.

Do not reproduce an entire frozen contract when a source reference is sufficient.

When the complete contract must be read during every implementation, it should also appear under `Required Sources`.

When it only needs consultation if a contract ambiguity arises, classify it as `Conditional`.

---

# 8. Scope

Define observable outcomes.

The section must answer:

```text
What must exist or behave differently when this TASK is complete?
```

Avoid vague requirements such as:

```text
improve robustness
prepare integration
support future functionality
```

unless concrete behavior is specified.

---

# 9. Non-goals

List only task-specific boundaries realistically at risk of scope expansion.

Example:

```text
- ROS 2 integration
- physical hardware execution
- database persistence
```

Do not paste a generic project-wide prohibition list.

---

# 10. Target Areas

Identify the narrowest expected implementation areas.

Example:

```text
Implementation:
- src/mission_runtime/

Tests:
- tests/test_mission_runtime.py
```

Do not invent paths unless their creation is explicitly required.

These paths guide implementation; they do not authorize unrelated changes.

---

# 11. Functional Requirements

Use stable identifiers:

```text
R1
R2
R3
...
```

Every requirement must be:

- testable;
- implementation-relevant;
- concise;
- compatible with frozen references.

Prefer:

```text
R3. `UNKNOWN` must not transition directly to `SUCCEEDED`.
```

over:

```text
The system should robustly handle unknown states.
```

---

# 12. Failure / Safety Requirements

Include only task-specific behavior.

Possible topics:

- invalid input;
- illegal state;
- retries;
- timeout;
- reconciliation;
- idempotency;
- recovery;
- escalation;
- fail-closed behavior.

If none:

```text
No task-specific failure/safety behavior beyond Required Sources and frozen references.
```

---

# 13. Validation

Define the minimum proof required.

## Focused validation

Provide exact commands when known.

Example:

```bash
pytest -q tests/test_mission_runtime.py
```

Prefer quiet output for successful runs.

## Regression

Specify exactly one:

```text
REQUIRED
NOT REQUIRED
CONDITIONAL
```

If `CONDITIONAL`, define the trigger.

Example:

```text
Regression: CONDITIONAL

Run when:
- a shared public contract changes; or
- implementation modifies code outside `src/mission_runtime/`.
```

Do not require full regression by default.

## Additional checks

List only required checks.

Example:

```bash
python3 -m compileall -q src tests
git diff --check
```

---

# 14. Evidence

Specify:

```text
Evidence required: YES | NO
```

If YES:

```text
Path: <EXPECTED_EVIDENCE_PATH>
```

State the minimum facts Evidence must prove.

Prefer referencing an existing Evidence schema over reproducing it.

TASK-history documents are not technical Evidence unless a frozen contract explicitly says otherwise.

---

# 15. Exit Criteria

Use concise binary-verifiable criteria.

Recommended:

```text
3–8 Exit Criteria
```

Each must support:

```text
PASS
FAIL
NOT APPLICABLE
```

Example:

```text
EC1. Required behavior defined by R1–R3 is implemented.
EC2. Focused validation passes.
EC3. Required Evidence is valid.
EC4. No declared Non-goal has been implemented.
```

Do not repeat the entire requirements section.

---

# 16. Workflow Handoff

Unless explicitly overridden:

```text
Implementation workflow:
prompts/codex/implement_task_v2.md

Next step after successful implementation:
Independent Read-only Review
```

Implementation completion does not imply Review acceptance.

---

# 17. Required TASK Output Structure

Generate the TASK file with this structure:

```markdown
# <TASK_ID> — <TASK_TITLE>

## 1. Objective

<Concise observable outcome.>

---

## 2. Dependencies

<Dependencies with required state and verification source.>

---

## 3. Authoritative Sources

### 3.1 Required

- `<path>`
  - Purpose: <why this must be read during normal implementation>

### 3.2 Conditional

- `<path>`
  - Read when: `<TRIGGER>`
  - Purpose: <what problem this resolves>

---

## 4. Frozen References

- `<path / identifier>`
  - <what is frozen>

---

## 5. Scope

This TASK must:

1. ...
2. ...
3. ...

---

## 6. Non-goals

This TASK must not:

- ...
- ...

---

## 7. Target Areas

### Implementation

- `<path/module>`

### Tests

- `<path/module>`

### Evidence

- `<path or NOT REQUIRED>`

---

## 8. Requirements

### R1 — <name>

<testable requirement>

### R2 — <name>

<testable requirement>

---

## 9. Failure / Safety Behavior

<task-specific requirements or reference-based statement>

---

## 10. Validation

### Focused

```bash
<command>
```

Expected proof:

- ...

### Regression

```text
REQUIRED | NOT REQUIRED | CONDITIONAL
```

Run when:

- <condition if applicable>

### Additional checks

```bash
<commands if required>
```

---

## 11. Evidence

```text
Evidence required: YES | NO
```

If required:

```text
Path: <path>
```

Evidence must prove:

- ...

---

## 12. Exit Criteria

- EC1. ...
- EC2. ...
- EC3. ...

Each criterion is evaluated as:

```text
PASS
FAIL
NOT APPLICABLE
```

---

## 13. Workflow Handoff

Implementation:

```text
prompts/codex/implement_task_v2.md
```

After successful implementation:

```text
Independent Read-only Review
```
```

---

# 18. Source Classification Quality Gate

Before saving the TASK, verify every source.

For each `Required Source`, ask:

```text
Must Codex read this during a normal successful implementation?
```

If not, move it to Conditional or remove it.

For each `Conditional Source`, verify:

```text
Is there an explicit trigger?
Does the source resolve that trigger?
```

If not, remove it.

Also verify:

1. no source appears in both groups;
2. parent Context/Plan documents are not Required without a concrete reason;
3. Backlog is normally omitted after TASK creation;
4. future-task documents are not included;
5. Conditional Sources are not generic "read if useful" references;
6. the normal implementation path can use Required Sources alone;
7. broader repository search should not be necessary during a normal run.

---

# 19. Final Quality Check

Before writing the file, verify:

1. exactly one TASK is defined;
2. Objective is observable;
3. dependencies are explicit;
4. Required Sources are minimal;
5. Conditional Sources have explicit triggers;
6. frozen references are precise;
7. Scope and Non-goals are distinct;
8. requirements are testable;
9. validation is sufficient but minimal;
10. regression has an explicit policy;
11. Evidence is explicit;
12. Exit Criteria are independently verifiable;
13. no future-task behavior is included;
14. parent documents are referenced rather than copied;
15. a normal implementation should not require repository-wide discovery.

---

# 20. Final Response

After creating the TASK file, return only:

```text
Created: <TASK_FILE_PATH>

TASK: <TASK_ID>
Dependencies: <count>
Required Sources: <count>
Conditional Sources: <count>
Requirements: <count>
Exit Criteria: <count>
Regression: REQUIRED | NOT REQUIRED | CONDITIONAL
Evidence: YES | NO

Ready for:
Implement <TASK_ID>
```

Do not implement the TASK.