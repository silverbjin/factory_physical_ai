# Record TASK Acceptance v2

## Orchestration Output Contract — MANDATORY

This workflow is normally executed as a child of `scripts/codex/run_task_orchestrator.py`.

The final response **MUST end with exactly one** `ACCEPTANCE_RESULT_JSON` line.
A prose-only acceptance result is invalid.

Successful recording:

```text
ACCEPTANCE_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","status":"RECORDED","accepted_commit":"<COMMIT>","acceptance_path":"<repo-relative-path>","workflow_complete":true}
```

Failure:

```text
ACCEPTANCE_RESULT_JSON: {"v":1,"task_id":"<TASK_ID>","status":"FAILED","accepted_commit":"<COMMIT>","acceptance_path":null,"workflow_complete":false}
```

Rules:

- never omit the marker;
- the marker must be the **last non-empty line** of the final response;
- never claim `RECORDED` unless all preconditions and post-write verification pass;
- create/replace only the resolved acceptance JSON;
- do not stage or commit; the external orchestrator owns the acceptance-record commit.

## Orchestrated Child Invocation

When the current user message begins with:

```text
ORCHESTRATOR_CHILD
worker_role=acceptance
task_id=<TASK_ID>
accepted_commit=<COMMIT>
```

this process is already a child worker of `scripts/codex/run_task_orchestrator.py`.

Treat the supplied `task_id` and `accepted_commit` as authoritative orchestration
inputs, subject to the verification rules in this prompt.

Do **not**:

- invoke or recommend `run_task_orchestrator.py`;
- redirect the user to a terminal;
- perform Implementation, Fix, or a new Review;
- reinterpret the message as a host-side `Run ...` request.

Execute this Acceptance-recording workflow only, then end with the mandatory
`ACCEPTANCE_RESULT_JSON` marker defined above.

## Resume Invocation

When the current `ORCHESTRATOR_CHILD` envelope contains:

```text
resume=true
resume_from_stage=acceptance
```

continue acceptance recording from the current repository state.

Normally Acceptance requires a clean worktree. During resume, a dirty worktree is
allowed **only** when the sole changed path is the resolved
`<TASK_SHORT>_acceptance.json` from the interrupted Acceptance attempt.

Resume rules:

- never modify source/tests/TASK/history;
- validate or replace only the resolved acceptance JSON;
- re-verify `accepted_commit`, Review provenance, Evidence path/hash, and filename;
- end with the normal mandatory `ACCEPTANCE_RESULT_JSON` marker;
- do not stage or commit.

## Purpose

Create one machine-verifiable acceptance artifact after an independent Review
has returned `ACCEPT` and the reviewed snapshot has been committed.

Typical invocation:

```text
Record TASK-SIM-003 acceptance for commit <COMMIT>
```

Extract exactly:

```text
TASK_ID
ACCEPTED_COMMIT
```

This is a narrow post-ACCEPT recording workflow.

Do not perform implementation, Fix, or a new independent Review.

---

## 1. Preconditions

Before writing anything:

1. resolve `tasks/<TASK_ID>.md`;
2. verify the Git worktree is clean, except for the narrow `resume=true` acceptance-file-only case defined above;
3. verify:

```bash
git rev-parse HEAD
```

equals `ACCEPTED_COMMIT`;

4. locate the latest Review history record for `TASK_ID`;
5. verify that Review explicitly records:

```text
ACCEPT <TASK_ID>
```

or an equivalent unambiguous `Recommendation: ACCEPT`;

6. verify that the accepted Review record is contained in `ACCEPTED_COMMIT`.

If any precondition fails, do not create or modify the acceptance artifact.

---

## 2. Context Budget

Read only what is required to establish acceptance provenance:

```text
tasks/<TASK_ID>.md
latest accepted review record
declared Evidence file when required
Git metadata for ACCEPTED_COMMIT
```

Do not load:

- previous TASK specifications;
- future TASK specifications;
- project Context / Plan;
- unrelated source files;
- unrelated tests;
- full Git history.

Do not re-run the full Read-only Review.

---

## 3. Acceptance Path

Let:

```text
TASK_SHORT = TASK_ID with leading "TASK-" removed
```

Example:

```text
TASK-SIM-003
→ SIM-003
```

The acceptance filename MUST be:

```text
<TASK_SHORT>_acceptance.json
```

Example:

```text
SIM-003_acceptance.json
```

The repository-wide canonical acceptance path is:

```text
results/reviews/<TASK_SHORT>_acceptance.json
```

Examples:

```text
TASK-SIM-003 -> results/reviews/SIM-003_acceptance.json
TASK-MVP-002 -> results/reviews/MVP-002_acceptance.json
```

Rules:

- always write the acceptance manifest under `results/reviews/`;
- do not place acceptance manifests beside TASK Evidence;
- do not use `results/simulation/`, `results/phase0/`, or another Evidence directory for acceptance manifests;
- if the orchestrator child envelope supplies `acceptance_path=...`, it MUST equal this canonical path;
- a TASK may declare its technical Evidence elsewhere; that does not change the acceptance-manifest directory.

Do not invent another naming convention.

---

## 4. Acceptance JSON

Create exactly one acceptance JSON.

Minimum structure:

```json
{
  "schema_version": 1,
  "task_id": "TASK-SIM-003",
  "status": "ACCEPT",
  "accepted_commit": "<COMMIT>",
  "review_record": "docs/task_history/TASK-SIM-003/<SEQ>_review.md",
  "evidence": {
    "path": "<declared Evidence path or null>",
    "sha256": "<sha256 or null>"
  }
}
```

Rules:

- `accepted_commit` MUST equal the supplied `ACCEPTED_COMMIT`;
- `review_record` MUST identify the Review that accepted this exact snapshot;
- when Evidence is required, hash the actual declared Evidence file;
- when Evidence is not required, use `null` values;
- do not add claims that were not verified;
- do not copy full test logs or Review prose into this JSON.

---

## 5. Write Boundary

This workflow may create or replace only the resolved acceptance JSON.

It MUST NOT modify:

- source;
- tests;
- TASK specification;
- contracts / schemas / ADRs;
- Review history;
- TASK history README;
- Evidence other than the acceptance JSON;
- Git index;
- Git history.

Do not stage or commit.

The external orchestrator owns the acceptance-record commit.

---

## 6. Verification

After writing:

1. parse the JSON;
2. verify `task_id`;
3. verify `status == "ACCEPT"`;
4. verify `accepted_commit`;
5. verify the exact canonical path `results/reviews/<TASK_SHORT>_acceptance.json`;
6. verify Evidence path/hash when applicable;
7. verify no repository file other than the acceptance JSON changed.

If verification fails, return failure and do not claim successful recording.

---

## 7. Final Output

Return a concise summary, then end with the exact machine-readable marker required by the mandatory Orchestration Output Contract at the top of this file.

Use no guessed token or credit values in this result.

The task becomes fully `ACCEPTED` for orchestration purposes only after the
external orchestrator successfully commits the recorded acceptance JSON.
