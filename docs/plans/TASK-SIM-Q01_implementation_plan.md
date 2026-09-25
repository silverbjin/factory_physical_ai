# TASK-SIM-Q01 Implementation Plan

> Status: APPROVED FOR SPECIFICATION ONLY
>
> Implementation authorization: NO — requires explicit approval of this plan.
>
> Task: `TASK-SIM-Q01`

## Goal

Implement additive, immutable provenance qualification Evidence for the
specific gaps frozen in `tasks/TASK-SIM-Q01.md`, without changing accepted
SIM-004 through SIM-009 artifacts or treating a new qualification run as a
historical predecessor run.

## Invariants

- Resolve every predecessor from Acceptance → `accepted_commit` → exact Git
  Evidence blob → SHA256; never from current worktree state.
- Do not create historical identity or time.  New identities belong only to
  Q01 operation records.
- Preserve profile aggregates and accepted non-success semantics.
- Require exact subject bindings; reject positional, timestamp, backend-name,
  and cross-scenario joins.
- A version-wide claim cannot satisfy a run-local requirement.
- Q01 is Simulation-only and has no physical or production-performance claim.

## Planned implementation tasks

### Task 1 — Evidence schema and domain models

Files: task-owned `src/simulation_runtime/` model/validation module(s),
`tests/test_simulation_provenance_qualification.py`, and task-owned schema or
fixture assets where repository conventions require them.

Behavior: Define the versioned Q01 Evidence model, the three record kinds,
applicability rules, independent semantic asset roles, and result states.

Tests: Reject unknown record kinds, fake `not_applicable` placeholders,
missing required fields, and use of one generic hash for distinct roles.

Evidence/completion: Serialization produces the Section 8 shape in
`tasks/TASK-SIM-Q01.md` and validates a minimal positive subject of each kind.

### Task 2 — Immutable predecessor resolver

Files: task-owned resolver module and focused tests.

Behavior: Resolve the five frozen predecessor tuples through Git object APIs;
verify the acceptance task/status/commit, exact Evidence path, and recomputed
SHA256 before exposing a binding to collectors.

Tests: Missing commit/blob, wrong task, wrong commit, wrong Evidence path,
tampered hash, and current-worktree substitution all fail closed.

Evidence/completion: Each Evidence subject records the resolver-proven
`predecessor_binding` and immutable authority paths.

### Task 3 — Gazebo/Nav2 qualification collector

Files: task-owned Gazebo collector/runner, bounded configuration assets, and
focused tests.

Behavior: Execute `q01-sim004-success-time`,
`q01-sim004-blocked-time`, and
`q01-sim004-timeout-reconciliation-time` against verified predecessor assets.
Capture structured simulator time, wall time, bounds/cleanup, world identity,
and separately bound bridge and launch/run assets.

Tests: Action identity binds wall time only to its matching operation;
simulation time cannot derive from logs/wall time; cleanup/bounds are required.

Evidence/completion: Three unique `operation_run` subjects with expected
frozen semantics and explicit source paths.

### Task 4 — MuJoCo qualification collector

Files: task-owned MuJoCo collector/runner and focused tests.

Behavior: Execute one new, bounded Q01 operation for each consumed SIM-005
scenario class. Create correlation identity at run start and capture MuJoCo
version, model/scene/config/source hashes, seed, timestep, step settings, and
initial-state identity.

Tests: Missing trace fails; action ID is required only for action-bound
operations; a new trace cannot be attached to an old row; config/model/seed
mismatch fails.

Evidence/completion: Each Q01 MuJoCo operation records its own correlation
identity and maps exactly one frozen predecessor scenario scope.

### Task 5 — SIM-007 profile-aggregate qualifier

Files: task-owned profile collector/validator and tests.

Behavior: Produce four `profile_aggregate` subjects with profile-local
configuration/source authority and expected accepted aggregate semantics.

Tests: Aggregate records accept `action_ids[]` but reject invented singular
request/action values; expected profile failure remains expected; wrong
profile/configuration binding fails.

Evidence/completion: All four profile IDs have unique records and no operation
message impersonation.

### Task 6 — SIM-008 semantic-asset qualification

Files: task-owned normal-system collector/validator and tests.

Behavior: Execute the bounded normal-system qualification and bind bridge and
launch/run configuration as semantically distinct assets alongside normal
correlation, world/configuration, timing, and outcome data.

Tests: Aliasing one generic hash into both semantic roles fails unless an
explicit source proves dual role; wrong normal scenario/world fails.

Evidence/completion: `q01-sim008-normal-system-authority` is complete and
clearly additive.

### Task 7 — SIM-009 scenario qualification collector

Files: task-owned scenario runner/validator and tests.

Behavior: Execute one operation subject per applicable Gazebo/MuJoCo SIM-009
scenario; capture run-local config, world/model, structured simulation time,
and only applicable recovery or Verification fields. Preserve each frozen
scenario's expected semantic outcome.

Tests: Cross-scenario mixing fails; an operational Verification failure does
not require verdict; success invocation verdicts `fail`/`uncertain` are valid
semantic outcomes; version-wide facts cannot fill local fields.

Evidence/completion: Every in-scope SIM-009 scenario has an explicit,
unambiguous Q01 subject or Evidence truthfully remains BLOCKED.

### Task 8 — Evidence aggregator and fail-closed validator

Files: task-owned Q01 aggregation runner, report generator, and tests.

Behavior: Validate subject completeness, claim scope, duplicate detection,
expected semantics, and task-specific result. Generate the canonical JSON and
human-readable report without manual state changes.

Tests: Tampered Evidence, stale source Git SHA, duplicate subjects, missing
run-local facts, backend-name-only association, and unaccepted predecessor
revision all BLOCK.

Evidence/completion: Fresh JSON at
`results/simulation/SIM-Q01_provenance_qualification.json` reports READY only
when every required subject passes.

### Task 9 — Controlled qualification execution and verification

Files: no speculative production changes; task-owned fixtures/results only as
defined by implementation.

Behavior: Run focused tests, execute every bounded qualification collector,
generate Evidence/report, run `git diff --check`, and execute the exact
regression command stated in the Q01 task implementation.

Tests: The actual commands and raw results are recorded; no prior SIM-010
regression classification is reused as Q01 proof.

Evidence/completion: Fresh Q01 Evidence has a matching `source_git_sha`,
complete validation status, and truthful result.

### Task 10 — Independent review and acceptance handoff

Files: generated Q01 Evidence/report and normal lifecycle review/acceptance
artifacts only after implementation is complete.

Behavior: Hand Q01 to independent review. The reviewer verifies immutable
bindings, new-run identity, structured timing, semantic asset roles, claim
scope, and tamper tests. Acceptance binds the accepted Q01 commit and exact
Evidence according to the canonical project model.

Tests: Reviewer reruns or inspects focused negative tests and verifies no
predecessor artifact changed.

Evidence/completion: Only independently accepted Q01 Evidence becomes an
eligible source for a later SIM-010 resolver change.

## Interfaces to implement

The implementation should expose deterministic operations equivalent to:

```text
resolve_predecessor_binding(task_id) -> VerifiedPredecessorBinding | error
collect_qualification_subject(binding, subject_spec) -> QualificationSubject | error
validate_qualification_evidence(evidence) -> ValidationReport
write_qualification_evidence(report) -> JSON artifact
```

These are behavioral interfaces, not a mandated class layout.  Each error
must preserve a structured, fail-closed reason and source path.

## Future execution order

1. Implement Tasks 1–2 with their focused negative tests.
2. Implement collectors one domain at a time (Tasks 3–7), running focused
   tests after each bounded change.
3. Implement aggregation (Task 8) and test all positive/negative bindings.
4. Execute the planned qualification runs only after the implementation is
   complete and validated.
5. Generate fresh Q01 Evidence/report, run required regression and
   `git diff --check`.
6. Submit the result to independent Review, then normal Acceptance.
7. Only after Acceptance, separately authorize any TASK-SIM-010 consumption
   work using the contract in the Q01 specification.

## Plan self-review checklist

- [x] Does not modify predecessor Acceptance/Evidence/commits.
- [x] Does not create retroactive historical IDs or simulation time.
- [x] Defines separate operation, aggregate, and version scopes.
- [x] Rejects loose joins and semantic hash aliases.
- [x] Retains independent Review and Acceptance.
- [x] Does not authorize implementation in this documentation checkpoint.
