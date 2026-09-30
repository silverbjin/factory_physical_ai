# Autonomous Accepted-Binding Consumer Diagnosis and Fix

## 1. Trigger

The canonical 11-subject MIN-Q01 preflight had passed the repaired SIM-008
runtime, then stopped while constructing SIM-009 accepted bindings:

```text
run_failure_suite()
  -> _accepted_binding("SIM-004")
  -> ValueError: SIM-004 accepted evidence hash does not match
```

The preceding SIM-008 diagnosis is recorded in
`09_autonomous_sim008_launch_fix.md`; it was not reopened in this correction.

## 2. Protected Dirty Worktree Condition

The mutable current-worktree file remained deliberately dirty throughout this
work:

```yaml
path: results/simulation/SIM-004_navigation_backend.json
current_worktree_sha256: 2540d52989cd1b52ee6b9ac52e72ba92555a6512256f076701403d58e9359f45
accepted_git_blob_sha256: b4c0ce91dde6c2f92c57ea6a227149362279993dee0dec4fd1ab12877e73f1d9
worktree_diff: 82 insertions / 82 deletions
```

It was not restored, normalized, overwritten, staged, or used as accepted
authority. The purpose of this correction was to prove accepted provenance
despite this intentional mutable-worktree divergence.

## 3. Current `_accepted_binding()` Behavior

Before correction, `_accepted_binding()` loaded the current Acceptance record
but then performed this effective resolution:

```text
ROOT / record["evidence"]["path"]
  -> read current worktree bytes
  -> compare those bytes with Acceptance SHA
```

It did not consume `record["accepted_commit"]`. Therefore a valid immutable
accepted blob was rejected whenever its mutable working copy differed. The
consumer handled SIM-004, SIM-005, SIM-006, and SIM-008, so the defect was not
limited to the first failing SIM-004 call.

## 4. Immutable Accepted Authority

The corrected consumer freezes and verifies these established bindings:

| Consumer task | Accepted commit | Evidence path | Expected result |
| --- | --- | --- | --- |
| SIM-004 | `b7e8266abd17f48c18cca94d9433db50fd55464d` | `results/simulation/SIM-004_navigation_backend.json` | `SIM_NAVIGATION_BACKEND_READY` |
| SIM-005 | `542514a4d10bc03087834e8a5f672d53afe6aa21` | `results/simulation/SIM-005_mujoco_vla_backend.json` | `SIM_MANIPULATION_BACKEND_READY` |
| SIM-006 | `a10be6725d386e531f9cb0e00079c8d39ffdb1bf` | `results/simulation/SIM-006_verification_backend.json` | `SIM_VERIFICATION_BACKEND_READY` |
| SIM-008 | `ea91e0c16412e20c8cae66355a1a39129919dd42` | `results/simulation/SIM-008_normal_system_e2e.json` | `SIM_NORMAL_E2E_READY` |

Resolution is now:

```text
Acceptance -> frozen accepted_commit/evidence path ->
git show <accepted_commit>:<evidence_path> -> SHA-256 -> task/result validation
```

## 5. Comparison with Contract-B Resolver

`resolve_predecessor_binding()` already implemented the required Contract-B
model: it validates Acceptance identity, accepted commit, optional rich
Acceptance evidence fields, immutable Git blob existence, SHA-256, Evidence
task identity, and expected task decision. `_accepted_binding()` now reuses
that resolver rather than maintaining a second authority model.

One accepted legacy detail was found during focused verification: immutable
SIM-006 Evidence predates `task_specific_result` and records the identical
task-level decision in `result`. The resolver now reads
`task_specific_result` with the existing legacy `result` fallback **from the
accepted Git blob only**. It remains fail-closed when the resolved value does
not equal the frozen expected result.

## 6. Root Cause

```yaml
root_cause_class: SIM009_ACCEPTED_BINDING_CONSUMER_DEFECT
first_failing_invariant: accepted predecessor Evidence must be resolved from its accepted Git tree, never from mutable ROOT bytes
current_authority_source: current worktree Evidence path from Acceptance
correct_authority_source: frozen accepted_commit plus Git blob and SHA-256
architecture_change_required: NO
```

Current-worktree dirtiness is a normal condition in this task and must not
alter immutable accepted provenance. The old code made it authoritative by
accident; the accepted commit was present in Acceptance but unused.

## 7. Decision

The minimum correction was to use the existing Contract-B resolver in
`_accepted_binding()` with a local frozen mapping for its four actual consumer
tasks. No architecture or MIN-Q01 scope change was required.

Rejected alternatives:

- modifying, restoring, or copying over the protected SIM-004 worktree file;
- trusting the current Evidence path after comparing its bytes;
- dropping hash, commit, task identity, or task-result validation;
- introducing a parallel immutable-provenance implementation;
- changing accepted predecessor artifacts.

## 8. Implementation

Modified files:

- `src/simulation_runtime/failure_recovery.py`
- `src/simulation_runtime/provenance_qualification.py`
- `tests/test_simulation_failure_recovery.py`
- this report

Changed symbols:

- `ACCEPTED_PREDECESSOR_BINDINGS`
- `_accepted_binding()`
- `resolve_predecessor_binding()` task-result compatibility check

Behavioral change:

`_accepted_binding()` now invokes `resolve_predecessor_binding()` against the
frozen binding and emits the verified commit/path/SHA. It never reads current
worktree Evidence bytes. The resolver retains minimal- and rich-Acceptance
support, validates rich path/SHA when supplied, and validates legacy SIM-006
`result` only as a value in the immutable accepted Git blob.

## 9. Focused Tests

The meaningful RED used a real temporary Git repository containing a valid
accepted SIM-004 blob plus divergent worktree bytes. Before the correction it
failed with:

```text
ValueError: SIM-004 accepted evidence hash does not match
```

The focused binding tests then covered:

- dirty worktree cannot override a valid accepted Git blob;
- minimal Contract-B Acceptance;
- frozen SHA mismatch;
- missing accepted Git blob;
- mismatched accepted commit;
- wrong accepted Git task result;
- mutable worktree cannot make invalid frozen provenance pass;
- immutable legacy SIM-006 `result` compatibility.

Command:

```text
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  -m pytest -q -p no:cacheprovider \
  tests/test_simulation_failure_recovery.py \
  tests/test_simulation_provenance_qualification.py
```

Result:

```text
76 passed in 1.22s
```

`py_compile` passed for `failure_recovery.py`,
`provenance_qualification.py`, `q01_execution_adapters.py`, and
`run_simulation_provenance_qualification.py`. `git diff --check` passed.

```yaml
UNIT_PASS: YES
SCENARIO_COVERAGE_PASS: YES
CANONICAL_COMPLETE: NO
```

## 10. Immutable Binding Verification

```yaml
accepted_commit_verification: PASS
accepted_git_blob_verification: PASS
sha256_verification: PASS
task_identity_verification: PASS
task_result_verification: PASS
minimal_acceptance_support: PASS
rich_acceptance_conflict_fail_closed: PASS
dirty_worktree_independence: PASS
```

The preflight advanced beyond the former SIM-004 hash error, confirming the
consumer no longer treats the protected dirty file as authority.

## 11. Canonical 11-Subject Preflight

The canonical command was run without writing canonical repository Evidence:

```text
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  scripts/run_simulation_provenance_qualification.py \
  --output /tmp/SIM-Q01-MIN_preflight.json \
  --report /tmp/SIM-Q01-MIN_preflight.md
```

It passed the repaired accepted-binding stage and then stopped with a new,
separate runtime-result contract failure:

```text
collect_qualification_subjects()
  -> collect_sim009_execution_result(...)
  -> ValueError: MISSING_RUN_LOCAL_CORRELATION
```

Exit code was `1`; no canonical aggregate artifact was produced.

```yaml
required_subjects: 11
observed_subjects: NOT_PRODUCED
missing: NOT_EVALUATED
extra: NOT_EVALUATED
binding_errors: 0
validation: BLOCKED
task_specific_result: NOT_PRODUCED
CANONICAL_COMPLETE: NO
```

A bounded live-adapter observation located the first downstream shape:
all four required SIM-009 navigation records had
`correlation_identity={}` and raw result keys only `error` and `result` because
the SIM-009 runtime reported `Gazebo/Nav2 runtime did not become ready` before
issuing its same-run navigation request. That is a separate SIM-009 live
navigation-bootstrap/correlation fault domain, not an accepted-binding defect.

## 12. Protected Scope Verification

```yaml
protected_dirty_SIM-004_Evidence_modified: NO
accepted_SIM-004_modified: NO
accepted_SIM-005_modified: NO
accepted_SIM-006_modified: NO
accepted_SIM-007_modified: NO
accepted_SIM-008_modified: NO
accepted_SIM-009_modified: NO
MIN-Q01_architecture_or_scope_changed: NO
frozen_SIM-010_state_changed: NO
orchestrator_resumed: NO
```

## 13. Final State

```text
NOT_READY_FOR_ORCHESTRATOR_RESUME
```

The immutable accepted-binding consumer is corrected and verified. Canonical
completion remains blocked by the first separate SIM-009 live navigation
bootstrap result that lacks same-run correlation.

## 14. Next Action

Diagnose the SIM-009 live navigation bootstrap path that yields
`Gazebo/Nav2 runtime did not become ready` before it creates a
mission/request/trace correlation. Keep accepted artifacts immutable and do
not modify the protected SIM-004 worktree Evidence.
