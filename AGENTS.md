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

### Routing Precedence

Apply routing in this order:

```text
1. Implement <TASK_ID>
2. Fix <TASK_ID>
3. Create <TASK_ID>
4. bare <TASK_ID>
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
→ active TASK specification
→ Required Sources
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

Do not load Review, Fix, or TASK-history prompts during initial implementation.

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

Do not use TASK-creation context rules during ordinary Implementation, Review, or Fix workflows.

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

Likewise, do not preload unrelated Implementation, Review, Fix, or TASK-creation prompts.

---

## 8. Efficiency Invariant

For a normal TASK run, the expected path is:

```text
user command
→ route exactly one workflow
→ load exactly one workflow prompt
→ load active TASK when applicable
→ load Required Sources
→ inspect only workflow-relevant files
→ execute workflow
```

On anomaly:

```text
detect concrete blocker
→ activate targeted context expansion
→ load only the necessary Conditional Source or directly related file
→ return to the normal workflow
```

Avoid repository-wide rediscovery unless narrower resolution has failed.