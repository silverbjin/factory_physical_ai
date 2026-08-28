# Common Task Implementation Prompt

## Purpose

This file defines the reusable implementation procedure for project tasks in this repository.

The task to implement is supplied by the user's current Codex message.

Typical invocation:

```text
Implement TASK-MVP-003
```

or:

```text
Implement TASK-W2-001
```

When this procedure is invoked, extract the exact task identifier from the current user message and treat it as `TASK_ID`.

---

## 1. Target Task Resolution

1. Extract exactly one task identifier from the current user message.
2. Set that identifier as `TASK_ID`.
3. Locate the authoritative task specification in the repository.
4. Locate the phase / MVP / week context and plan that govern `TASK_ID`.
5. Locate frozen contracts, schemas, ADRs, architecture decisions, and prior-task evidence that constrain `TASK_ID`.
6. Determine the immediately preceding task and next task only when needed for dependency and scope checks.
7. Do not ask the user to provide paths for repository information that can be discovered automatically.

If no valid task identifier can be resolved, stop and report that the implementation target is unresolved.

---

## 2. Implementer Role

Act as the implementation agent for `TASK_ID`.

Your job is to:

- understand the frozen requirements;
- verify prerequisites;
- implement only the target task;
- add or update only tests required by the target task;
- run required validation;
- generate required evidence;
- persist the implementation workflow history under `docs/task_history/`;
- report completion status.

Do not perform an independent acceptance review. That is handled separately by the read-only review workflow.

---

## 3. Sources of Truth

Before modifying files, locate and read all relevant project instructions and frozen sources.

At minimum inspect, when present:

- `AGENTS.md` files applicable to the working directory;
- project implementation context;
- phase / MVP / week context;
- phase / MVP / week plan;
- task backlog;
- exact `TASK_ID` specification;
- project architecture;
- frozen contracts;
- schemas;
- relevant ADRs / architecture decisions;
- acceptance criteria;
- exit criteria;
- prior-task evidence or freeze decisions required as prerequisites;
- repository testing and evidence conventions.

Also read:

```text
prompts/codex/task_history_recording.md
```

Follow its TASK history recording policy.

`prompts/codex/task_history_recording.md` defines portfolio/audit recording behavior only.
It does not override frozen task requirements, contracts, architecture, acceptance criteria, or evidence rules.

If `prompts/codex/task_history_recording.md` is required by repository workflow but cannot be found or read, stop before implementation and report the missing workflow dependency.

Search the repository instead of assuming every filename or directory is fixed.

When sources conflict, use this priority unless the repository defines a stricter hierarchy:

1. Explicit frozen contract / architecture decision / approved freeze
2. Explicit `TASK_ID` requirements and Exit Criteria
3. Current phase / MVP / week plan
4. Current phase / MVP / week context
5. General project conventions

Do not modify a frozen contract merely to make the implementation easier.

If a material conflict makes implementation unsafe or ambiguous, stop before modifying files and report the conflict.

---

## 4. Pre-implementation Gate

Before modifying repository files, perform a preflight inspection.

### 4.1 Repository state

Inspect at least:

```bash
git status --short
git diff --stat
git diff
```

If staged changes exist, inspect them too.

Preserve all pre-existing user changes.

Never reset, restore, clean, checkout, stash, overwrite, or delete unrelated user work.

### 4.2 Prerequisite verification

Identify prerequisites declared by `TASK_ID`, the current plan, architecture freezes, or previous tasks.

Examples may include:

- previous task status;
- architecture freeze = GO;
- contract freeze = GO;
- required evidence exists;
- required schema or interface is already frozen;
- previous regression suite is green.

Verify required prerequisites from repository evidence.

Do not assume a prerequisite is satisfied merely because a later task exists.

If a mandatory prerequisite is not satisfied, do not implement the task. Report the blocking prerequisite.

### 4.3 Scope verification

Before implementation, determine:

- exact required behavior of `TASK_ID`;
- explicit non-goals;
- components owned by later tasks;
- files or modules likely to be touched;
- tests required by the Exit Criteria;
- evidence required for completion;
- TASK history files that will be created or updated after implementation validation.

Do not expand the current phase / MVP / week scope.

### 4.4 Pre-implementation summary

Before editing, briefly state:

- resolved `TASK_ID`;
- prerequisite status;
- expected implementation files or modules to change;
- expected tests;
- expected evidence artifact;
- expected TASK history location;
- important explicit non-goals.

Then proceed directly with implementation if prerequisites pass.

---

## 5. Strict Scope Rules

Implement **only `TASK_ID`**.

You MUST NOT:

- implement the next task;
- implement later-task functionality for convenience;
- expand phase / MVP / week scope;
- rewrite frozen contracts without explicit authorization;
- modify unrelated modules;
- refactor unrelated code merely for cleanliness;
- introduce infrastructure that belongs to later tasks;
- hide scope expansion inside helper abstractions;
- commit or stage changes unless the user explicitly asks.

Small structural preparation is allowed only when all of the following are true:

1. it is necessary for `TASK_ID`;
2. it does not implement later-task behavior;
3. it does not change frozen public contracts;
4. it is covered by the target task's tests or required architecture.

When uncertain, prefer the smallest implementation that satisfies the task.

TASK history files under:

```text
docs/task_history/
```

are expected workflow/audit artifacts and are not considered later-task implementation or scope expansion when they are created according to `prompts/codex/task_history_recording.md`.

---

## 6. Boundary Ownership

Respect architectural ownership defined by the project.

Do not implement components outside `TASK_ID` merely because they will eventually be required.

Potential future boundaries may include, depending on the project:

- ROS / ROS 2 execution;
- physical robot execution;
- Nav2;
- MoveIt / MoveIt 2;
- VLA or model inference;
- agent orchestration;
- AMR integration;
- persistence;
- PostgreSQL or other databases;
- Docker / deployment;
- observability;
- Grafana;
- networking;
- multi-agent behavior;
- external services.

This list is illustrative, not automatically applicable to every task.

Use the actual task specification and frozen architecture to determine prohibited boundaries.

---

## 7. Implementation Requirements

Implement the smallest correct solution that satisfies the frozen task requirements.

### 7.1 Contract correctness

Honor all frozen:

- field names;
- field sets;
- required / optional fields;
- data types;
- enum values;
- state names;
- schemas;
- function / method signatures;
- public imports;
- API semantics;
- error semantics;
- idempotency semantics;
- retry semantics;
- ownership boundaries.

Do not silently introduce alternate contracts.

### 7.2 Fail-closed behavior

Where applicable, invalid or ambiguous conditions should fail closed.

Avoid:

- permissive defaults that bypass requirements;
- silent fallbacks;
- swallowed exceptions;
- implicit success;
- accepting unknown states as valid;
- unbounded retries;
- caller-controlled safety invariants;
- partially initialized state.

### 7.3 State / lifecycle correctness

When the task defines lifecycle or state behavior:

- use finite states when required;
- make transitions explicit;
- reject illegal transitions;
- preserve terminal-state semantics;
- prevent ambiguous outcomes from becoming success without reconciliation;
- enforce retry bounds in implementation, not only tests;
- expose recovery / escalation behavior only when required.

### 7.4 Determinism

Where deterministic behavior is required:

- avoid unnecessary randomness;
- avoid hidden global state;
- avoid wall-clock dependent decisions unless specified;
- avoid unordered behavior that affects externally visible results.

### 7.5 Minimal change discipline

Prefer:

```text
required implementation
+ required tests
+ required evidence
+ required TASK history
```

over broad refactoring.

---

## 8. Test Implementation

Add or modify tests only as required to prove `TASK_ID`.

Tests should cover relevant:

- happy paths;
- invalid paths;
- boundary cases;
- frozen contract behavior;
- safety invariants;
- failure paths;
- regression behavior.

For stateful tasks, explicitly test illegal transitions and invariant violations.

For retry/reconciliation/recovery tasks, explicitly test limits and failure outcomes.

For contract tasks, test both accepted and rejected field sets where applicable.

Do not weaken an existing test merely to make the new implementation pass.

---

## 9. Validation

After implementation, run all validation required by the task and repository.

### 9.1 Focused tests

Run the most specific tests for `TASK_ID`.

### 9.2 Full regression

Run the project's full regression suite when feasible and when required by the task / project process.

### 9.3 Syntax / static checks

Run repository-defined checks.

When no project-specific command exists, suitable non-mutating examples may include:

```bash
python3 -m compileall -q src tests
git diff --check
```

Avoid checks that rewrite source files unless the repository explicitly requires them and they are safely scoped.

### 9.4 Repository cleanliness before evidence/history

Inspect:

```bash
git status --short
git diff --stat
git diff --check
```

Verify only intended implementation, test, and evidence-preparation files changed.

At this stage, `docs/task_history/` files for the current workflow may not exist yet.

If test or tool execution generates caches or temporary files inside the repository, remove only files generated by the current task when it is safe and unambiguous to do so.

Never remove pre-existing user files.

---

## 10. Exit Criteria

Locate the actual Exit Criteria for `TASK_ID`.

Evaluate every criterion individually as:

```text
PASS
FAIL
NOT APPLICABLE
```

Do not mark the task complete when a required criterion fails.

Passing tests alone is not sufficient if contract, scope, evidence, or prerequisite criteria fail.

Store the resolved Exit Criteria results for use in both Evidence Generation and TASK History Recording.

---

## 11. Evidence Generation

If the project requires a task evidence artifact, generate or update the evidence for `TASK_ID` according to repository conventions.

Evidence should contain, when applicable:

- task identifier;
- implementation status;
- changed implementation/test files;
- test commands;
- test results;
- Exit Criteria;
- relevant hashes;
- timestamp / provenance required by the project;
- scope / non-goal confirmation.

Evidence must describe the actual validated implementation state.

Do not fabricate test results or hashes.

If evidence is not required, explicitly report that it is not applicable.

### 11.1 TASK-history / Evidence boundary

TASK history documents are human-readable portfolio/audit records.

Unless a frozen evidence contract explicitly requires otherwise, files under:

```text
docs/task_history/
```

are not implementation evidence and are excluded from:

- source hash sets;
- implementation changed-file manifests;
- Exit Criteria implementation-file counts.

This avoids making a human-readable audit record recursively depend on its own evidence representation.

If a frozen evidence schema explicitly requires every repository change, follow that schema and report the resulting ordering requirement rather than silently violating it.

---

## 12. Final Implementation Self-check

Before recording TASK history or declaring completion, verify:

1. `TASK_ID` requirements are implemented.
2. Mandatory prerequisites were satisfied.
3. No later task was started.
4. Frozen contracts remain intact.
5. Only task-related implementation/test/evidence files were changed.
6. Required focused tests pass.
7. Required regression tests pass.
8. Required Exit Criteria pass.
9. Required evidence exists and matches the implementation.
10. Repository diff has no unintended whitespace or generated-file issues.
11. No unrelated user changes were modified.

Determine the technical implementation status now:

```text
COMPLETE
```

or:

```text
INCOMPLETE
```

Do not yet return the final user-facing report.

The determined implementation status must not be changed merely to make TASK history look successful.

---

## 13. TASK History Recording — Mandatory Workflow Step

After Sections 9–12 are complete, persist the implementation result according to:

```text
prompts/codex/task_history_recording.md
```

This step is mandatory for the implementation workflow.

### 13.1 Determine history sequence

Use:

```text
docs/task_history/<TASK_ID>/
```

Determine the next sequential history number `SEQ` according to the recording policy.

Never overwrite or renumber an existing history entry.

### 13.2 Create implementation history

Create:

```text
docs/task_history/<TASK_ID>/<SEQ>_implementation.md
```

The document must describe the actual validated result of this implementation run.

Use Korean for portfolio-readable narrative where English is not required.

Preserve exact technical identifiers including:

- `TASK_ID`;
- file paths;
- class/function/variable names;
- contract/schema fields;
- commands;
- test names;
- error messages;
- `PASS` / `FAIL`;
- `COMPLETE` / `INCOMPLETE`;
- hashes and commit IDs.

At minimum record:

- TASK 목적;
- prerequisite 상태;
- 구현 범위;
- 명시적 비범위;
- 변경 파일과 목적;
- 주요 설계 판단;
- 테스트 명령과 결과;
- Exit Criteria;
- Evidence 경로/상태;
- technical implementation status;
- 다음 단계가 independent Read-only Review인지 여부.

### 13.3 Update TASK summary

Create or update:

```text
docs/task_history/<TASK_ID>/README.md
```

The README must summarize the chronological workflow for the TASK.

Add the current implementation run to the work-flow table without deleting prior history.

Do not claim `ACCEPT` here unless an independent Read-only Review has actually accepted the task.

After Implementation only, distinguish:

```text
Implementation: COMPLETE
Review: NOT YET ACCEPTED
```

when applicable.

### 13.4 Update global TASK history index

Create or update:

```text
docs/task_history/README.md
```

Add or refresh the row for `TASK_ID`.

Do not erase other TASK entries.

The global index must distinguish implementation completion from independent acceptance.

For example:

```text
IMPLEMENTED / REVIEW PENDING
REJECTED / FIX REQUIRED
ACCEPTED
```

### 13.5 History write failure policy

If any mandatory TASK history file cannot be created or updated:

- do not modify source code merely to solve the history problem;
- do not fabricate a successful history write;
- report the exact failure;
- treat the **implementation workflow** as incomplete even if the technical implementation itself passed.

In that case, preserve the technical status separately:

```text
Technical implementation: COMPLETE
Workflow history recording: FAIL
```

Do not return `TASK_ID is complete.` until the required TASK history recording succeeds.

---

## 14. TASK History Verification

After writing TASK history, verify all required history outputs.

At minimum confirm:

```text
docs/task_history/<TASK_ID>/<SEQ>_implementation.md
docs/task_history/<TASK_ID>/README.md
docs/task_history/README.md
```

Verify:

1. all required files exist;
2. the implementation history uses the correct `TASK_ID`;
3. the sequential filename did not overwrite prior history;
4. tests and Exit Criteria match actual results;
5. Evidence path/status matches the generated evidence;
6. `COMPLETE` / `INCOMPLETE` matches Section 12;
7. TASK README workflow order is correct;
8. global index contains the current TASK;
9. no previous TASK history entry was deleted;
10. Korean narrative does not translate or alter exact technical identifiers.

Then inspect:

```bash
git status --short
git diff --stat
git diff --check
```

At this final repository check:

- expected `docs/task_history/` changes are valid workflow artifacts;
- do not classify correctly generated TASK history files as unintended or unrelated changes;
- still report any unrelated non-history changes.

If history verification fails, the workflow is not complete.

---

## 15. Required Final Report

Return the implementation result in this structure.

# Implementation Result — `TASK_ID`

## Scope

- Task implemented:
- Later tasks started: YES/NO
- Scope expansion detected: YES/NO

## Files Changed

Separate implementation artifacts from portfolio/audit history.

### Implementation / Test / Evidence

List each changed file and its purpose.

### TASK History

List:

- `docs/task_history/<TASK_ID>/<SEQ>_implementation.md`
- `docs/task_history/<TASK_ID>/README.md`
- `docs/task_history/README.md`

## Implementation

Summarize only what was implemented for `TASK_ID`.

Also summarize explicit non-goals that were preserved when they are important to task scope.

## Tests Run

For every command include:

- command;
- passed;
- failed;
- status.

## Exit Criteria

List each actual Exit Criterion:

```text
<criterion> — PASS/FAIL/NOT APPLICABLE
```

## Evidence

- Evidence required: YES/NO
- Evidence path:
- Evidence status:
- Hash verification: PASS/FAIL/NOT APPLICABLE

## TASK History

- History policy loaded: YES/NO
- Implementation history:
- TASK summary:
- Global history index:
- History verification: PASS/FAIL

## Repository Check

- `git diff --check`: PASS/FAIL
- unintended non-history files changed: YES/NO
- expected TASK history files changed: YES/NO
- unrelated user changes preserved: YES/NO

## Recommended Commit Message

Provide one concise Conventional Commit-style message unless repository conventions specify another format.

## Final Status

Return exactly one:

```text
TASK_ID is complete.
```

or:

```text
TASK_ID is NOT complete.
```

`TASK_ID is complete.` is allowed only when:

- technical implementation status is COMPLETE;
- all mandatory validation and Exit Criteria pass;
- required Evidence is valid;
- mandatory TASK history recording and verification pass.

If incomplete, list only the blocking reasons.

---

## 16. Final Constraints

Remember:

- implement only the task named in the current user message;
- do not start the next task;
- discover relevant repository files automatically;
- verify prerequisites before editing;
- preserve unrelated user work;
- obey frozen contracts and architecture;
- use the smallest correct implementation;
- run required tests and Exit Criteria;
- generate truthful evidence;
- read and follow `prompts/codex/task_history_recording.md`;
- TASK history recording is mandatory for workflow completion;
- create TASK history only after technical validation, Exit Criteria, Evidence, and implementation self-check are resolved;
- do not treat TASK history as implementation evidence unless a frozen contract explicitly requires it;
- do not overwrite prior TASK history;
- do not stage or commit unless explicitly requested;
- do not claim completion when mandatory validation, Evidence, or TASK history recording fails.

Begin implementation of the task identifier supplied in the current user message.
