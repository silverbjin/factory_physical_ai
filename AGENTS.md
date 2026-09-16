# AGENTS.md

## Purpose

This file defines repository-wide Codex routing and context-budget rules.

Keep this file small.

`AGENTS.md` is a dispatcher and guardrail only.

Workflow procedures belong in `prompts/codex/*.md`.

---

## 1. Prompt Routing

Route TASK commands by exact command form.

### Implementation

Command:

```text
Implement <TASK_ID>
```

Example:

```text
Implement TASK-SIM-002
```

Load exactly:

```text
prompts/codex/implement_task_v2.md
tasks/<TASK_ID>.md
```

Then follow the routed workflow prompt.

---

### Fix

Command:

```text
Fix <TASK_ID>
```

Example:

```text
Fix TASK-SIM-002
```

Load exactly:

```text
prompts/codex/fix_review_findings_v2.md
tasks/<TASK_ID>.md
```

Then follow the routed workflow prompt.

---

### Read-only Review

Command must contain only the TASK ID:

```text
<TASK_ID>
```

Example:

```text
TASK-SIM-002
```

Load exactly:

```text
prompts/codex/read_only_review_v2.md
tasks/<TASK_ID>.md
```

Then follow the routed workflow prompt.

Do not interpret:

```text
Implement <TASK_ID>
Fix <TASK_ID>
Create <TASK_ID>
Record acceptance <TASK_ID>
```

as Review commands.

---

### TASK Specification Creation

Command:

```text
Create <TASK_ID>
```

Example:

```text
Create TASK-SIM-002
```

Load:

```text
prompts/codex/create_task_spec_v2.md
```

Do not require `tasks/<TASK_ID>.md` to exist before creation.

Follow the routed workflow prompt to resolve only the planning/context sources needed to create the TASK specification.

---

### Acceptance Recording

Command:

```text
Record acceptance <TASK_ID>
```

Example:

```text
Record acceptance TASK-SIM-003
```

Load exactly:

```text
prompts/codex/record_task_acceptance_v2.md
tasks/<TASK_ID>.md
```

Then follow the routed workflow prompt.

This route records an already-completed independent ACCEPT review.

It is not a Review command and must not rerun or reinterpret the independent review.

Resolve:

```text
SHORT_TASK_ID = <TASK_ID> with the leading `TASK-` removed
ACCEPTANCE_FILE = results/reviews/<SHORT_TASK_ID>_acceptance.json
```

Example:

```text
TASK_ID         = TASK-SIM-003
SHORT_TASK_ID   = SIM-003
ACCEPTANCE_FILE = results/reviews/SIM-003_acceptance.json
```

If the required TASK file is missing, follow the recorder workflow's fail-closed policy.

---

### Routing Precedence

Apply routing in this order:

```text
1. Implement <TASK_ID>
2. Fix <TASK_ID>
3. Create <TASK_ID>
4. Record acceptance <TASK_ID>
5. bare <TASK_ID>
```

Match exactly one route.

Do not load multiple workflow prompts to decide which route applies.

If no route matches, do not automatically load TASK workflow prompts.

---

## 2. TASK File Resolution

For an existing TASK:

```text
TASK_ID = exact identifier from the user command
TASK_FILE = tasks/<TASK_ID>.md
```

Example:

```text
TASK_ID   = TASK-SIM-002
TASK_FILE = tasks/TASK-SIM-002.md
```

Use the canonical path directly.

Do not search the repository for the TASK specification when the canonical file exists.

If the expected TASK file is missing, follow the routed workflow's missing-reference policy.

---

## 3. Context Budget Policy

Use bounded context by default.

For TASK workflows, use this loading order:

```text
routed workflow prompt
→ active TASK specification when applicable
→ Required Sources or workflow-declared inputs
→ workflow-relevant target files
```

Do not recursively rediscover project context.

Do not recursively read:

```text
context/
docs/
plans/
tasks/
prompts/
repository history
```

unless the routed workflow or active TASK requires a specific file.

Do not read previous or future TASK specifications merely to reconstruct project history.

Prefer exact paths over repository-wide search.

---

## 4. Required and Conditional Sources

The active TASK specification is the context manifest.

### Required Sources

Read sources listed under:

```text
Authoritative Sources
→ Required
```

when required by the routed workflow.

Keep the normal execution path within these sources whenever possible.

### Conditional Sources

Do not read sources listed under:

```text
Authoritative Sources
→ Conditional
```

preemptively.

Load a Conditional Source only when its declared trigger or an equivalent concrete anomaly actually occurs.

Use:

```text
minimum sufficient context
→ concrete anomaly
→ targeted context expansion
```

Never use:

```text
maximum available context first
```

as the default strategy.

---

## 5. Workflow Context Boundaries

### Implementation

Default context:

```text
TASK
→ Required Sources
→ task-related implementation/tests
```

Do not load Review, Fix, Acceptance Recording, or TASK-history prompts during initial implementation.

---

### Read-only Review

Default context:

```text
TASK
→ Required Sources
→ TASK-specific change set
→ relevant implementation/tests
→ declared Evidence
```

Review the TASK-specific change set.

Do not default to the entire diff against the repository merge base.

Do not inspect previous or next TASKs unless a concrete review anomaly requires it.

---

### Fix

Default context:

```text
TASK
→ latest blocking Review findings
→ Required Sources
→ finding-related code/tests
```

Fix only acceptance-blocking findings.

Do not repeat the complete Read-only Review by default.

Use a reviewed revision or change range only when it is explicitly identified by Review or Evidence.

Do not reconstruct Git history by default.

---

### TASK Creation

Load only the project-state, planning, architecture, backlog, or contract sources necessary to define the requested TASK.

Do not use TASK-creation context rules during ordinary Implementation, Review, Fix, or Acceptance Recording workflows.

---

### Acceptance Recording

Default context:

```text
TASK
→ latest persisted independent Review for that TASK
→ TASK-declared canonical Evidence
→ only supporting artifacts named by the Review handoff
```

Do not reload the full implementation context.

Do not load Implementation, Fix, Review, TASK-creation, or TASK-history workflow prompts merely to record acceptance.

Do not reconstruct acceptance from project history, passing tests, or memory.

The recorder must bind the persisted independent Review to the exact reviewed repository artifacts according to:

```text
prompts/codex/record_task_acceptance_v2.md
```

---

## 6. Repository Safety

For every workflow:

- preserve unrelated user changes;
- do not expand into later TASK functionality;
- do not modify frozen contracts merely for convenience;
- do not stage or commit unless explicitly requested;
- do not rewrite Git history without explicit authorization;
- prefer targeted file inspection over full repository inspection.

Workflow-specific safety and validation rules are defined by the routed prompt.

---

## 7. Late-loaded Workflow Policies

Do not preload auxiliary workflow policies.

In particular, do not load:

```text
prompts/codex/task_history_recording_v2.md
```

at TASK start unless the routed workflow explicitly requires it at that stage.

Load TASK-history policy only when the routed workflow reaches its history-recording step.

For Acceptance Recording, inspect the already-persisted review record directly.

Do not load `task_history_recording_v2.md` merely because the recorder consumes a review-history file.

If the required persisted review is missing, follow the recorder's fail-closed instructions rather than switching workflows automatically.

Likewise, do not preload unrelated Implementation, Review, Fix, TASK-creation, or Acceptance Recording prompts.

---

## 8. Efficiency Invariant

For a normal TASK run, the expected path is:

```text
user command
→ route exactly one workflow
→ load exactly one workflow prompt
→ load active TASK when applicable
→ load Required Sources or workflow-declared inputs
→ inspect only workflow-relevant files
→ execute workflow
```

For Acceptance Recording:

```text
Record acceptance <TASK_ID>
→ record_task_acceptance_v2.md
→ active TASK
→ latest persisted ACCEPT review
→ canonical Evidence
→ explicitly bound supporting artifacts
→ create/validate one acceptance artifact
```

On anomaly:

```text
detect concrete blocker
→ activate targeted context expansion
→ load only the necessary Conditional Source or directly related file
→ return to the normal workflow
```

Avoid repository-wide rediscovery unless narrower resolution has failed.
