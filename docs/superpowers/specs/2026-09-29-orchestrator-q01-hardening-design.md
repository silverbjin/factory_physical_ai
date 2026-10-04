# Codex Task Orchestrator Q01 Hardening Design

## Goal
Extend the existing host-side Codex TASK orchestrator so RED integration/provenance tasks can autonomously resolve same-gate blocker chains, finalize canonical evidence from immutable source state, protect accepted predecessor artifacts, verify literal validation launcher provenance, and preserve task-lifetime accounting across resume runs without changing the legacy workflow for tasks that do not opt into staged qualification.

## Compatibility model
The existing GREEN/YELLOW/legacy RED lifecycle remains the default. A task opts into the new path only when a machine-readable task contract is present at `tasks/orchestrator/<TASK_ID>.json` and declares `profile: staged_integration_v1`. Existing TASK markdown classification, diagnosis routing, review/fix/rereview semantics, deterministic acceptance, and acceptance commit semantics remain authoritative.

## Lifecycle
For `staged_integration_v1` tasks:

`diagnosis -> implementation -> gate_resolution(G0..G7) -> finalization(G8) -> literal_validation(G9) -> review -> review-boundary commit -> acceptance`

After review rejection and a successful review fix:

`fix -> gate_resolution -> finalization -> literal_validation -> rereview`

The host owns gate iteration. Codex workers may diagnose/fix one bounded blocker, but cannot own the unbounded gate loop.

## ORCH-A — State schema v3 and routing
Checkpoint schema becomes v3 while v2 checkpoints are upgraded in memory on load. New state fields:
- `qualification_profile`
- `review_return_phase`
- `gate_state`
- `finalization`
- `protected_artifacts`
- `literal_validation`
- `aggregate`

New resumable phases: `gate_resolution`, `finalization`, `literal_validation`. Legacy tasks never enter them.

## ORCH-B — Gate Resolver
The task contract declares ordered gates, each with an exact argv command. `gate_state.current_gate_index` is the durable cursor. A gate execution captures command, exit code, stdout/stderr tail, HEAD, and timestamp.

Failures are normalized into a structured blocker signature with:
- `gate_id`
- `finding_id`
- `root_cause_class`
- `first_failing_invariant`
- `affected_boundary`
- `classification`

Supported classifications: `SAME_GATE`, `REGRESSION`, `NEW_EXTERNAL_FAULT_DOMAIN`, `CONTRACT_OR_ARCHITECTURE_CONTRADICTION`.

For `SAME_GATE` and `REGRESSION`, the host may invoke one bounded gate-fix worker then rerun the same gate. The same normalized invariant may be fixed at most 3 times; then status becomes `ARCHITECTURE_REVIEW_REQUIRED`. External/contract classifications stop immediately. Passed gates are frozen as durable baselines. Supplier cache is scoped by `attempt_id` and cleared when a correction changes source state.

## ORCH-C — Immutable source finalization
After G7, the orchestrator creates a dedicated `source-finalization` commit. `source_paths` names the immutable source/config paths whose Git blobs are hashed for provenance. `finalization_paths` is the pre-canonical commit allowlist and may additionally include durable diagnosis/task-history artifacts; it defaults to `source_paths`. The resulting commit is stored as `finalization.source_commit`, then the contract's canonical command runs. Canonical evidence must declare `source_git_sha == source_commit`; declared source hashes must be reproducible from `git show <source_commit>:<path>`. Before Review and Re-review commits, a finalization-authority guard verifies HEAD still equals `source_commit`, source paths are unchanged, canonical Evidence bytes still match the recorded evidence SHA-256, and literal validation was executed against the same source commit. `accepted_commit` retains its existing meaning: the independent-review accepted snapshot.

## ORCH-D — Protected artifact guard
At task start, protected paths declared in the task contract are snapshotted from HEAD using Git object ID and SHA-256. Before every orchestrator-owned commit boundary, changed/deleted/renamed protected paths are rejected with `PROTECTED_ARTIFACT_VIOLATION`. The orchestrator never auto-restores protected files.

## ORCH-E — Literal validation and aggregate accounting
Literal validation commands are executed exactly as argv arrays. Each result records requested command, resolved executable, interpreter (when determinable), exit code, test count when parseable, and Git SHA. Non-zero exit stops before review.

Task-lifetime aggregate counters live in the checkpoint and are incremented across invocations: orchestrator runs, Codex calls, reported tokens, diagnosis calls, gate fix calls, review fix calls, review calls, and gate resolution cycles.

`--force` on a HEAD mismatch no longer preserves downstream proof. It accepts the new repository state but invalidates gate baselines, supplier cache, source commit/bindings, literal validation results, and review readiness, then resumes from the earliest safe phase (`gate_resolution` for staged tasks, the checkpoint phase for legacy tasks).

## ORCH-F — Verification
Add focused tests covering:
1. staged route enters gate resolution while legacy route still enters review;
2. two different same-gate blockers can be corrected sequentially;
3. the same invariant fails closed after 3 bounded fixes;
4. external/contract blockers stop without an automatic fix;
5. protected predecessor modification blocks commit;
6. source SHA mismatch blocks finalization;
7. literal launcher provenance is recorded and non-zero exit blocks review;
8. resume preserves passed gate cursor;
9. forced HEAD mismatch invalidates staged proof;
10. supplier cache is attempt-scoped;
11. aggregate counters survive resume;
12. legacy task routing remains unchanged.

## Non-goals
- Do not infer gate commands or protected paths from prose.
- Do not alter historical predecessor Acceptance/Evidence.
- Do not redefine `accepted_commit`.
- Do not make gate fixes consume independent-review fix budget.
- Do not globally kill unrelated processes or reset/stash/clean the user's worktree.
