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

Read `reviewed_commit` from the persisted review handoff and verify that it exists:

```bash
git cat-file -e <reviewed_commit>^{commit}
```

Inspect every committed path changed after the reviewed commit:

```bash
git diff --name-status <reviewed_commit>..HEAD
```

Also inspect working-tree changes:

```bash
git status --short
```

### 4.1 Post-review Change Classification

Classify every post-review changed path as exactly one of:

```text
TASK_AUDIT_METADATA
WORKFLOW_CONTROL_METADATA
MATERIAL_TASK_CHANGE
UNRELATED_CHANGE
```

Do not reject acceptance merely because `HEAD != reviewed_commit`.

The acceptance decision is bound to the exact reviewed TASK artifacts through hashes and the persisted review record. The purpose of this classification is to determine whether later repository changes invalidate that reviewed TASK state.

#### TASK_AUDIT_METADATA

Allowed without invalidating the review:

```text
docs/task_history/<TASK_ID>/**
```

Examples include persisted review/fix/implementation history for the same TASK.

These files may exist as committed or working-tree changes after the reviewed implementation commit.

#### WORKFLOW_CONTROL_METADATA

The following repository-control files may change after the reviewed implementation commit without invalidating the implementation review:

```text
AGENTS.md
prompts/codex/read_only_review_v2.md
prompts/codex/task_history_recording_v2.md
prompts/codex/record_task_acceptance_v2.md
```

They are allowed only when their changes do not modify the reviewed TASK's specification, implementation, tests, canonical Evidence, supporting Evidence, contracts, schemas, runtime configuration, or TASK-owned implementation/verifier behavior.

Workflow-control changes affect repository procedure for current/future workflow execution. They do not by themselves change the implementation state that was independently reviewed.

Do not rerun or reinterpret the independent review merely because one of these workflow-control files changed.

If a repository uses an equivalent renamed workflow file, classify it as `WORKFLOW_CONTROL_METADATA` only when its role is clearly repository workflow/routing control and it has no TASK-owned implementation/evidence responsibility. Otherwise classify it as `UNRELATED_CHANGE` and evaluate conservatively.

#### MATERIAL_TASK_CHANGE

Any post-review modification to reviewed TASK material is a hard stop. This includes, when applicable:

```text
<TASK_FILE>
canonical Evidence declared by <TASK_FILE>
TASK-owned supporting Evidence/report artifacts
TASK-owned implementation source
TASK-owned tests
TASK-owned runtime configuration
TASK-owned implementation/verifier scripts
contracts or schemas consumed/frozen by <TASK_ID>
```

Use the TASK specification, review handoff, canonical Evidence, and supporting-artifact list to identify these paths precisely.

Do not classify an entire shared directory as material solely because the TASK read from it. A file is material when the reviewed TASK implementation or accepted Evidence depends on that exact file/revision.

If any material TASK artifact changed after `reviewed_commit`, stop with:

```text
ACCEPTANCE NOT RECORDED

Reason:
material TASK content changed after the reviewed commit; a new independent review is required.
```

#### UNRELATED_CHANGE

A repository change unrelated to `TASK_ID` must not automatically invalidate acceptance.

It may be tolerated only when all of the following are true:

```text
- it does not modify a reviewed TASK artifact;
- it does not modify a frozen contract/schema consumed by the TASK;
- it does not alter the canonical Evidence or supporting artifact hashes;
- it does not make repository identity or review provenance ambiguous.
```

If independence cannot be established narrowly, fail closed and report the path requiring resolution.

### 4.2 Immutable Reviewed-artifact Invariant

Acceptance may proceed only when the reviewed TASK identity is still cryptographically intact. At minimum require:

```text
TASK specification hash == review handoff hash
canonical Evidence hash == review handoff hash, when required
required supporting artifact hashes == review handoff hashes
reviewed_commit exists
persisted review == ACCEPT <TASK_ID>
acceptance_recording_eligible == true
```

These immutable bindings, rather than equality between current `HEAD` and `reviewed_commit`, establish the reviewed TASK identity.

### 4.3 Working-tree Rule

Working-tree changes are evaluated using the same classification.

Allowed:

```text
TASK_AUDIT_METADATA
WORKFLOW_CONTROL_METADATA
demonstrably unrelated non-material changes
```

Blocked:

```text
MATERIAL_TASK_CHANGE
ambiguous unrelated changes
```

Do not alter, stash, reset, or clean working-tree changes to make recording easier.

### 4.4 Post-review Change Audit

Before creating the acceptance manifest, build a deterministic list of every path changed between `reviewed_commit` and `recording_base_commit`, plus relevant current working-tree changes.

For each path record:

```text
path
classification = TASK_AUDIT_METADATA | WORKFLOW_CONTROL_METADATA | UNRELATED_CHANGE
source = committed | working_tree
```

Do not include `MATERIAL_TASK_CHANGE` because its presence blocks recording.

Sort the list lexicographically by `path`, then by `source`.

This list is audit metadata explaining why `recording_base_commit` may legitimately differ from `reviewed_commit`.

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
  "post_review_changes": [
    {
      "path": "prompts/codex/read_only_review_v2.md",
      "classification": "WORKFLOW_CONTROL_METADATA",
      "source": "committed"
    }
  ],
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
material TASK artifacts changed after reviewed_commit
post-review change classification is ambiguous for a path that may affect TASK identity
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
7. verify every `post_review_changes` entry against the actual Git/working-tree classification;
8. recompute `acceptance_payload_sha256`;
9. verify `review_decision == ACCEPT`;
10. verify the task-specific decision was copied unchanged;
11. run:

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
Post-review changes: <count, all non-material>
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
