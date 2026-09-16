# AGENTS.md

## Purpose

Repository-wide Codex routing, context-budget, and orchestration guardrails.

Keep this file small. Workflow procedures belong in `prompts/codex/*.md`.

---

## 1. Prompt Routing

Match exactly one route in this order.

### TASK range automation

```text
Run <START_TASK_ID>..<END_TASK_ID>
→ prompts/codex/run_task_range_v2.md
```

Example:

```text
Run TASK-SIM-002..TASK-SIM-004
```

### Single TASK automation

```text
Run <TASK_ID>
→ prompts/codex/run_task_workflow_v2.md
```

Example:

```text
Run TASK-SIM-002
```

### Acceptance recording

```text
Record <TASK_ID> acceptance for commit <COMMIT>
→ prompts/codex/record_task_acceptance_v2.md
```

This route is normally invoked only by the external orchestrator after an
independent Review has returned `ACCEPT` and the reviewed snapshot has been committed.

### Implementation

```text
Implement <TASK_ID>
→ prompts/codex/implement_task_v2.md
→ tasks/<TASK_ID>.md
```

### Fix

```text
Fix <TASK_ID>
→ prompts/codex/fix_review_findings_v2.md
→ tasks/<TASK_ID>.md
```

### TASK creation

```text
Create <TASK_ID>
→ prompts/codex/create_task_spec_v2.md
```

Do not require `tasks/<TASK_ID>.md` to exist before creation.

### Independent Read-only Review

A message containing only:

```text
<TASK_ID>
```

routes to:

```text
prompts/codex/read_only_review_v2.md
tasks/<TASK_ID>.md
```

Do not load multiple workflow prompts to decide a route.

---

## 2. TASK File Resolution

For an existing TASK:

```text
TASK_FILE = tasks/<TASK_ID>.md
```

Use the canonical path directly.

Do not search the repository for the TASK specification when this path exists.

---

## 3. Context Budget Policy

Use bounded context by default.

For worker TASK workflows:

```text
routed workflow prompt
→ active TASK specification
→ Required Sources
→ workflow-relevant target files
```

Do not recursively read:

```text
context/
docs/
plans/
tasks/
prompts/
repository history
```

unless the active workflow or TASK requires a specific file.

Do not read previous or future TASK specifications merely to reconstruct project history.

Prefer exact paths over repository-wide search.

---

## 4. Required / Conditional Sources

The active TASK is the context manifest.

Read `Authoritative Sources > Required` on the normal worker path.

Do not read `Authoritative Sources > Conditional` preemptively.

Use:

```text
minimum sufficient context
→ concrete anomaly
→ targeted context expansion
```

Load only the Conditional Source needed for the active trigger.

Acceptance recording is a special post-ACCEPT workflow and follows
`record_task_acceptance_v2.md`; it must not load ordinary Required Sources unless
that prompt explicitly needs a specific reference.

---

## 5. Run Orchestration Boundary

`Run ...` routes are orchestration-only.

The parent orchestration context MUST NOT load:

- TASK specifications;
- Required Sources;
- Conditional Sources;
- implementation files;
- tests;
- Evidence;
- Review findings;
- TASK history;
- acceptance Evidence.

The routed Run prompt invokes the external orchestrator.

Fresh child Codex contexts own all TASK-level work.

For a TASK range, only compact terminal state crosses TASK boundaries.

---

## 6. Orchestrated Git Ownership

For `Run ...` workflows:

- child Implementation, Review, Fix, Re-review, and Acceptance workers MUST NOT stage or commit;
- only `scripts/codex/run_task_orchestrator.py` may stage and commit;
- orchestration MUST start from a clean Git worktree;
- orchestration should run on a dedicated automation branch, not `main` or `master`;
- the first completed Review creates the Implementation+Review snapshot;
- a completed Re-review after Fix creates the Fix+Re-review snapshot;
- REJECT review states are committed as traceable snapshots;
- after final Review `ACCEPT`, the accepted Review snapshot commit is frozen first;
- Acceptance recording then creates exactly one acceptance JSON referring to that accepted commit;
- Acceptance JSON is committed in a separate acceptance-record commit;
- unrelated/pre-existing changes must never be auto-committed;
- a downstream TASK may start only after the preceding TASK is `ACCEPTED`,
  its acceptance record commit succeeded, and the worktree is clean.

Outside `Run ...` orchestration, do not stage or commit unless explicitly requested.

Do not rewrite Git history without explicit authorization.

---

## 7. Worker Context Boundaries

### Implementation

```text
TASK
→ Required Sources
→ task-related implementation/tests
```

Do not preload Review, Fix, Acceptance, or TASK-history prompts.

### Review

```text
TASK
→ Required Sources
→ TASK-specific change set
→ relevant implementation/tests
→ declared Evidence
```

Do not default to the entire merge-base diff.

### Fix

```text
TASK
→ latest blocking Review findings
→ Required Sources
→ finding-related code/tests
```

Do not repeat the complete Review by default.

### Acceptance recording

```text
TASK identity
→ accepted commit
→ latest accepted Review record
→ declared Evidence pointer if needed
→ one acceptance JSON
```

Do not rediscover project context or inspect unrelated source files.

### TASK Creation

Load only the project-state/planning sources needed to define the requested TASK.

---

## 8. Late-loaded Policies

Do not preload:

```text
prompts/codex/task_history_recording_v2.md
```

Load TASK-history policy only when the routed worker reaches its history-recording step.

Do not preload unrelated workflow prompts.

---

## 9. Efficiency Invariant

Normal worker path:

```text
route one workflow
→ load one workflow prompt
→ load active TASK when required
→ load minimum authoritative inputs
→ inspect only relevant files
→ execute
```

Normal accepted TASK path:

```text
Implement
→ Review ACCEPT
→ commit reviewed snapshot
→ Acceptance record
→ commit acceptance JSON
→ ACCEPTED
```

Normal range path:

```text
Run TASK-A..TASK-B
→ parent state machine only
→ isolated TASK-A lifecycle
→ ACCEPTED + acceptance commit + clean
→ isolated TASK-A+1 lifecycle
```

Avoid repository-wide rediscovery unless narrower resolution fails.
