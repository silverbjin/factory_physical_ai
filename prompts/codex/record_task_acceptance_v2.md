# Common Task Acceptance Recording Prompt v2

## Purpose

Create the canonical machine-readable acceptance manifest after an independent READ-ONLY review has accepted the routed TASK.

This workflow is intentionally separate from:

```text
prompts/codex/read_only_review_v2.md
```

because the independent reviewer must remain read-only.

Use the TASK identity and canonical paths already resolved by `AGENTS.md` routing:

```text
TASK_ID
TASK_FILE
SHORT_TASK_ID
ACCEPTANCE_FILE
```

Do not rediscover or reinterpret the command route.

Do not implement, review, or fix the TASK.

---

## 1. Recorder Role

Act only as an **acceptance recorder**.

Your job is to transform an already-completed, independently persisted ACCEPT review into a canonical machine-readable acceptance binding.

You are NOT:

- the implementer;
- the reviewer;
- a fixer;
- a gate-decider;
- a project-state updater.

Do not reinterpret or improve the review result.

---

## 2. Allowed Mutation

You MAY create:

```text
<ACCEPTANCE_FILE>
```

You MUST NOT modify any other repository file.

Do not:

- modify source;
- modify tests;
- modify TASK specifications;
- modify canonical Evidence;
- modify contracts or schemas;
- create or repair TASK history;
- update context or plans;
- stage or commit;
- merge;
- reset, restore, clean, or stash;
- install dependencies.

If the required persisted review record is missing, stop and instruct the caller to record it first with the existing TASK-history workflow.

Do not switch workflows automatically.

---

## 3. Required Inputs

### 3.1 TASK specification

Use the already-routed:

```text
<TASK_FILE>
```

to determine:

- whether Evidence is required;
- the canonical Evidence path;
- allowed task-specific decision values;
- explicitly required supporting report/artifact paths;
- downstream eligibility semantics when present.

### 3.2 Persisted independent review

Locate the latest independent review record for `TASK_ID` under:

```text
docs/task_history/<TASK_ID>/
```

Use the latest sequence-numbered `*_review.md` file.

Do not select implementation or fix records.

The selected review must contain exactly:

```text
ACCEPT <TASK_ID>
```

as its Final Recommendation.

It must also contain the structured:

```yaml
acceptance_handoff:
```

block emitted by the read-only review workflow.

If no persisted ACCEPT review exists, stop.

### 3.3 Canonical Evidence

When the TASK specification says:

```text
Evidence required: YES
```

the exact TASK-specified Evidence file must exist.

Do not substitute a similar artifact.

When Evidence is not required, record:

```json
{
  "required": false,
  "path": null,
  "sha256": null
}
```

---

## 4. Repository / Commit Validation

Before writing anything, inspect:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --format='%H'
```

Read `reviewed_commit` from the persisted review handoff.

Verify it exists:

```bash
git cat-file -e <reviewed_commit>^{commit}
```

Compare:

```bash
git diff --name-only <reviewed_commit>..HEAD
```

Allowed committed changes after the reviewed commit are limited to audit/review metadata for this exact TASK, for example:

```text
docs/task_history/<TASK_ID>/**
```

No source, test, TASK specification, canonical Evidence, contract, schema, config, or implementation file may materially differ from the reviewed commit.

For working-tree changes, persisted review-history changes for this exact TASK may already exist.

Any unrelated or material implementation change after review is a hard stop.

---

## 5. Acceptance Handoff Validation

Parse the persisted review's:

```yaml
acceptance_handoff:
```

Require:

```text
schema_version = review_acceptance_handoff_v1
task_id = TASK_ID
review_decision = ACCEPT
acceptance_recording_eligible = true
```

Require the exact reviewed commit.

Require:

```text
task_spec.path = TASK_FILE
```

Independently recompute:

```text
SHA256(TASK_FILE)
```

and require exact equality with:

```text
task_spec.sha256
```

If Evidence is required, independently recompute its SHA-256 and require exact equality with the handoff.

Do not trust a hash merely because it appears in the review.

---

## 6. Task-specific Decision

If the TASK defines a task-specific result/decision:

1. read the value from canonical Evidence/report;
2. require exact equality with the review handoff;
3. verify that the value is allowed by the TASK specification;
4. copy it exactly into the acceptance manifest.

Do not convert an accepted BLOCKED result into READY.

Examples:

```text
ACCEPT + SIM_BASELINE_READY
ACCEPT + SIM_BASELINE_BLOCKED
```

are both recordable when verified.

The downstream TASK decides which accepted task-specific state is eligible.

---

## 7. Review Record Binding

Independently compute:

```text
SHA256(latest persisted ACCEPT review record)
```

Record:

- repository-relative review path;
- review SHA-256.

The acceptance manifest binds the persisted review, not ephemeral console/chat output.

---

## 8. Supporting Artifact Binding

Use `supporting_artifacts` from the review handoff only when:

- the artifact belongs to `TASK_ID`;
- the reviewer actually verified its exact hash;
- it still exists unchanged.

Independently recompute every supporting artifact hash.

If a TASK-required supporting artifact no longer matches, stop.

Do not add extra artifacts during recording.

---

## 9. Existing Acceptance Artifact Policy

If `ACCEPTANCE_FILE` already exists:

1. validate it;
2. if it already binds the same:
   - TASK;
   - reviewed commit;
   - TASK spec hash;
   - Evidence hash;
   - review-record hash;
   - task-specific decision;

   return:

```text
ALREADY RECORDED: <ACCEPTANCE_FILE>
```

and do not rewrite it.

3. If it differs materially, stop with:

```text
ACCEPTANCE CONFLICT
```

Do not automatically overwrite a conflicting acceptance artifact.

---

## 10. Acceptance Manifest Schema

Create this logical structure:

```json
{
  "schema_version": "task_acceptance_v1",
  "task_id": "TASK-SIM-003",
  "short_task_id": "SIM-003",
  "review_decision": "ACCEPT",
  "task_specific_decision": "SIM_BASELINE_READY",
  "reviewed_commit": "<40-char SHA>",
  "recording_base_commit": "<HEAD before acceptance creation>",
  "task_spec": {
    "path": "tasks/TASK-SIM-003.md",
    "sha256": "<sha256>"
  },
  "evidence": {
    "required": true,
    "path": "results/simulation/SIM-003_baseline.json",
    "sha256": "<sha256>"
  },
  "review_record": {
    "path": "docs/task_history/TASK-SIM-003/02_review.md",
    "sha256": "<sha256>"
  },
  "supporting_artifacts": [
    {
      "path": "docs/simulation/simulation_baseline_v1.md",
      "sha256": "<sha256>"
    }
  ],
  "acceptance_recorded_at_utc": "<RFC3339 UTC timestamp>",
  "acceptance_payload_sha256": "<canonical payload hash>"
}
```

Use:

```json
"supporting_artifacts": []
```

when none exist.

Do not add `recording_commit`.

The commit that later contains this manifest is represented by Git history. Putting that future commit SHA inside the file creates a self-reference problem.

---

## 11. Canonical Payload Hash

Compute `acceptance_payload_sha256` over the manifest excluding the `acceptance_payload_sha256` field.

Canonical serialization:

```python
json.dumps(
    payload_without_acceptance_payload_sha256,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

Then:

```python
hashlib.sha256(...).hexdigest()
```

Write UTF-8 JSON with deterministic key ordering and a trailing newline.

---

## 12. Fail-closed Conditions

Do not create acceptance when any condition below is true:

```text
TASK specification missing
persisted review missing
latest applicable review is REJECT
ACCEPT line does not match TASK_ID exactly
acceptance_handoff missing
acceptance_recording_eligible != true
reviewed_commit missing or invalid
material files changed after reviewed_commit
TASK spec hash mismatch
required Evidence missing
Evidence hash mismatch
task-specific decision ambiguous
task-specific decision not allowed by TASK spec
required supporting artifact hash mismatch
repository identity is ambiguous
existing acceptance artifact conflicts
```

Never infer acceptance from passing tests alone.

---

## 13. Validation After Writing

After creating the manifest:

1. parse the JSON;
2. verify `task_id`;
3. recompute TASK spec hash;
4. recompute Evidence hash if required;
5. recompute review-record hash;
6. recompute all supporting-artifact hashes;
7. recompute `acceptance_payload_sha256`;
8. verify `review_decision == ACCEPT`;
9. verify the task-specific decision was copied unchanged;
10. run:

```bash
git diff --check -- <ACCEPTANCE_FILE>
git status --short
```

Expected mutation from this workflow:

```text
<ACCEPTANCE_FILE>
```

plus pre-existing review-history changes that existed before this workflow.

Do not stage or commit.

---

## 14. Downstream Authorization Rule

This recorder establishes:

```text
independent review acceptance
+
immutable artifact binding
```

It does NOT independently decide downstream readiness.

Example:

```text
ACCEPT + SIM_BASELINE_READY
```

may satisfy a downstream predecessor rule.

But:

```text
ACCEPT + SIM_BASELINE_BLOCKED
```

means only:

```text
the BLOCKED result is trustworthy
```

and does not authorize downstream implementation.

Downstream eligibility is evaluated by the downstream TASK specification.

---

## 15. Required Output

On success:

```text
Acceptance recorded: <ACCEPTANCE_FILE>

Task: <TASK_ID>
Review: ACCEPT
Task-specific decision: <exact value or null>
Reviewed commit: <SHA>
Review record: <path>
Evidence: <path or NOT REQUIRED>
Acceptance payload SHA-256: <sha256>

Repository mutations:
- <ACCEPTANCE_FILE>

Ready for:
- commit review history + acceptance metadata
- downstream dependency evaluation
```

If already valid:

```text
ALREADY RECORDED: <ACCEPTANCE_FILE>
```

If blocked:

```text
ACCEPTANCE NOT RECORDED

Reason:
<exact fail-closed reason>
```

---

## 16. Workflow Boundary

Normal accepted-task flow:

```text
implementation
→ implementation/evidence commit
→ independent read-only review
→ persisted review history
→ this acceptance recorder
→ acceptance metadata commit
→ downstream dependency evaluation
```

Rejected review:

```text
REJECT
→ persist review history
→ Fix workflow
→ new implementation commit
→ new independent review
```

Do not create acceptance from a rejected review.
