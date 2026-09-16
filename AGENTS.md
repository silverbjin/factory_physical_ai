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

---

## 1. Worker Machine-result Protocol

Workers launched by the host orchestrator MUST terminate with the required
machine-readable marker as the **last non-empty line**.

```text
Implement <TASK_ID>
→ WORKFLOW_RESULT_JSON with stage="implementation"

<TASK_ID>
→ WORKFLOW_RESULT_JSON with stage="review"

Fix <TASK_ID>
→ WORKFLOW_RESULT_JSON with stage="fix"

Record <TASK_ID> acceptance for commit <COMMIT>
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
