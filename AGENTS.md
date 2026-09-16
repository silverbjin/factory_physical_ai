# AGENTS.md

## Purpose

Repository-wide Codex worker routing and bounded-context guardrails.

The **host-side Python orchestrator** owns full TASK lifecycle execution.
Do not launch the orchestrator from inside a Codex-managed session because it
starts fresh `codex exec` workers that need normal writable Codex state.

---

## 0. Host-side Orchestration Boundary

`Run <TASK_ID>` and `Run <START_TASK_ID>..<END_TASK_ID>` are **host-side workflow
commands**, not nested Codex workflows.

Canonical entry points from a normal VS Code/WSL terminal:

```bash
python3 scripts/codex/run_task_orchestrator.py task <TASK_ID>
```

```bash
python3 scripts/codex/run_task_orchestrator.py range <START_TASK_ID> <END_TASK_ID>
```

Convenience wrappers may be used when installed:

```bash
scripts/codex/run-task <TASK_ID>
scripts/codex/run-task-range <START_TASK_ID> <END_TASK_ID>
```

If a user types a `Run ...` command inside a Codex chat session:

- do **not** invoke `run_task_orchestrator.py` from that Codex session;
- do **not** implement/review/fix the TASK as a fallback;
- return the matching host-terminal command only.

The Python runner is the sole source of truth for full lifecycle status.

## 0.1 Orchestrator Child Boundary — HIGHEST PRECEDENCE

A Codex execution whose current user message begins with:

```text
ORCHESTRATOR_CHILD
```

is already running under the host-side:

```text
scripts/codex/run_task_orchestrator.py
```

It is a **worker**, not a parent orchestration session.

This rule takes precedence over every host-side `Run ...` redirect rule.

For an `ORCHESTRATOR_CHILD` execution:

- do **not** tell the user to run `run_task_orchestrator.py`;
- do **not** invoke the host orchestrator;
- do **not** redirect the work back to a normal terminal;
- execute exactly one declared `worker_role`;
- read exactly the worker prompt named in the child envelope;
- resolve exactly the supplied `task_id`;
- emit the required machine-result marker as the last non-empty line.

Supported worker roles:

```text
worker_role=implementation
→ prompts/codex/implement_task_v2.md
→ tasks/<TASK_ID>.md

worker_role=review
→ prompts/codex/read_only_review_v2.md
→ tasks/<TASK_ID>.md

worker_role=rereview
→ prompts/codex/read_only_review_v2.md
→ tasks/<TASK_ID>.md

worker_role=fix
→ prompts/codex/fix_review_findings_v2.md
→ tasks/<TASK_ID>.md

worker_role=acceptance
→ prompts/codex/record_task_acceptance_v2.md
```

For `worker_role=acceptance`, also use the supplied:

```text
accepted_commit=<COMMIT>
```

Never reinterpret `ORCHESTRATOR_CHILD` as a `Run ...` request.

---

## 1. Worker Machine-result Protocol

Workers launched by the host orchestrator MUST terminate with the required
machine-readable marker as the **last non-empty line**.

```text
ORCHESTRATOR_CHILD + worker_role=implementation
→ WORKFLOW_RESULT_JSON with stage="implementation"

ORCHESTRATOR_CHILD + worker_role=review|rereview
→ WORKFLOW_RESULT_JSON with stage="review"

ORCHESTRATOR_CHILD + worker_role=fix
→ WORKFLOW_RESULT_JSON with stage="fix"

ORCHESTRATOR_CHILD + worker_role=acceptance
→ ACCEPTANCE_RESULT_JSON
```

A prose-only completion message is invalid for orchestrated execution.
The exact schemas are repeated near the top of each worker prompt so partial
prompt reads cannot silently omit the protocol.

---

## 2. Worker Prompt Routing

Match exactly one worker route.

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

### Acceptance recording

```text
Record <TASK_ID> acceptance for commit <COMMIT>
→ prompts/codex/record_task_acceptance_v2.md
```

### Independent Read-only Review

A message containing only:

```text
<TASK_ID>
```

routes to:

```text
prompts/codex/read_only_review_v2.md
→ tasks/<TASK_ID>.md
```

Do not load multiple worker prompts to decide a route.

---

## 3. TASK File Resolution

For an existing TASK:

```text
TASK_FILE = tasks/<TASK_ID>.md
```

Use the canonical path directly. Do not search the repository when it exists.

---

## 4. Context Budget Policy

For worker TASK workflows:

```text
routed worker prompt
→ active TASK specification
→ Authoritative Sources / Required
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

Do not read previous/future TASK specifications merely to reconstruct project history.
Prefer exact paths over repository-wide search.

---

## 5. Required / Conditional Sources

Read `Authoritative Sources > Required` on the normal path.
Do not read `Authoritative Sources > Conditional` preemptively.

Use:

```text
minimum sufficient context
→ concrete anomaly
→ targeted context expansion
```

Acceptance recording follows `record_task_acceptance_v2.md` and should read only
provenance inputs needed for the acceptance artifact.

---

## 6. Git Ownership

Worker contexts MUST NOT stage or commit.

Only the host-side `scripts/codex/run_task_orchestrator.py` may stage/commit during
automated TASK execution.

The orchestrator requires:

- clean worktree at entry;
- dedicated automation/task branch (not `main`/`master` by default);
- Review-boundary commit after completed Review;
- Fix/Re-review commit after completed Re-review;
- separate acceptance-record commit after final ACCEPT;
- clean worktree before a downstream TASK starts.

Do not rewrite Git history without explicit authorization.

---

## 7. Late-loaded Policies

Do not preload unrelated workflow prompts or project-management documents.
Load `prompts/codex/task_history_recording_v2.md` only when the active worker reaches
its history-recording step.
