# Autonomous Diagnosis and Fix — TASK-SIM-Q01-MIN

## 1. Trigger

The canonical MIN-Q01 preflight initially failed in the SIM-009 path:

```text
scripts/run_simulation_provenance_qualification.py
  -> collect_qualification_subjects()
  -> run_sim009_qualification()
  -> run_failure_suite()
  -> load_manifest()
ValueError: SIM-009 scenario budget or shape is malformed
```

After the manifest-policy correction, the same preflight advanced through the
SIM-009 manifest boundary.  A first SIM-009 live sidecar timeout was then
converted to structured missing run-local provenance rather than escaping as
`subprocess.TimeoutExpired`.  The final preflight attempt stopped earlier in
the independently failing SIM-008 supplier with
`ValueError: MISSING_STRUCTURED_SIMULATION_TIME`; no preflight artifact was
generated.

## 2. Evidence Collected

| Authority | Observed fact |
| --- | --- |
| Current `failure_recovery.py` | `load_manifest()` requires ordered 16 IDs, exact six-field rows, positive integer budgets, and `budget_ms <= MAX_SCENARIO_BUDGET_MS`. |
| Current manifest | `SIM009-NAV-TIMEOUT-RETRY` has the accepted `budget_ms` value `33000`; the current manifest is clean. |
| Accepted SIM-009 source | `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be` has the same manifest path, IDs, row shape, and source policy: 30-second navigation execution, 2-second intentional fault, 1-second margin. |
| Accepted manifest | Exactly matches the current 16 scenario IDs and budgets, including `33000` for timeout/retry. |
| Accepted Evidence | At the accepted commit, `results/simulation/SIM-009_failure_recovery.json` has `task_id=TASK-SIM-009`, `task_specific_result=SIM_FAILURE_SUITE_READY`, and the accepted scenario decisions/outcomes. Frozen SHA256: `91d10e5bb4fb7ca1b62c325885bec276c6ef6231c6baa0424f3213702be3216e`. |

The exact failing predicate was:

```text
SIM009-NAV-TIMEOUT-RETRY
budget_ms = 33000
current MAX_SCENARIO_BUDGET_MS = 23000
predicate: 0 < budget_ms <= MAX_SCENARIO_BUDGET_MS
```

The 23,000ms maximum appeared only after `GazeboSystemWorld` initialized
SIM-008 and changed the shared navigation module's `EXECUTION_SECONDS` from
30 to 20.  Importing `failure_recovery` afterwards calculated the old
mutable-derived recovery bound as `20000 + 2000 + 1000`.

## 3. Root Cause

**root_cause_class:** `SIM009_BUDGET_POLICY_MISMATCH`

**first_failing invariant:** the accepted 33,000ms timeout/retry budget was
rejected after a different task changed a shared execution-duration global.

This was a consumer/validator regression introduced by the MIN-Q01 combined
execution order, not a malformed SIM-009 manifest.  The accepted SIM-009
authority fixes the retry budget at 30,000ms recovery plus 2,000ms fault and
1,000ms margin.  The manifest and accepted Evidence remain the semantic
oracle.

The same SIM-009 preflight then exposed a second, direct producer-consumer
fault: `gazebo_clock()` allowed a bounded `gz topic` timeout to escape as an
unhandled `subprocess.TimeoutExpired`.  The SIM-009 observer already had the
correct fail-closed rule for a sidecar failure (`None` means no run-local
measurement); it simply did not receive a normalized sidecar error.

## 4. Decision

**architecture_change_required:** NO

The frozen MIN-Q01 eleven-subject scope remains valid.  The correction is
limited to preserving accepted SIM-009 replay policy and converting a bounded
Gazebo sidecar timeout into its existing fail-closed observation state.

Rejected alternatives:

- reducing the accepted `33000` manifest budget to satisfy the leaked 20s
  SIM-008 window;
- modifying accepted SIM-009 Evidence or Acceptance;
- removing budget/shape validation;
- expanding MIN-Q01 scope.

No accepted predecessor artifact was modified.

## 5. Implementation

Modified files:

- `src/simulation_runtime/failure_recovery.py`
  - removed the mutable cross-task import of `EXECUTION_SECONDS`;
  - fixed `NORMAL_RECOVERY_TIMEOUT_MS = 30000`, the accepted SIM-009 replay
    policy used to derive the 33,000ms maximum.
- `scripts/q01_execution_adapters.py`
  - `gazebo_clock()` now normalizes `OSError` and
    `subprocess.TimeoutExpired` to `RuntimeError("Gazebo stats sidecar timed out")`.
  - The existing SIM-009 observer catches that runtime error and emits no
    fabricated run-local measurement.
- `tests/test_simulation_failure_recovery.py`
  - proves SIM-008's local 20s window cannot reduce SIM-009's accepted
    33,000ms timeout/retry allowance;
  - proves over-budget, malformed-shape, and reordered manifests still fail
    closed.
- `tests/test_simulation_provenance_qualification.py`
  - proves a Gazebo stats timeout becomes an absent SIM-009 run-local
    observation instead of an unhandled exception.

## 6. Tests

### UNIT_PASS

```text
pytest -q tests/test_simulation_failure_recovery.py \
  -k 'isolated_from_sim008 or rejects_budget'
2 passed

pytest -q tests/test_simulation_provenance_qualification.py \
  -k gazebo_stats_timeout
1 passed
```

### SCENARIO_COVERAGE_PASS

```text
pytest -q tests/test_simulation_failure_recovery.py \
  -k 'not suite_fails_closed and not runner_evidence_is_machine_readable'
31 passed, 2 deselected

pytest -q tests/test_simulation_provenance_qualification.py
36 passed
```

The two deselected failure-recovery tests were separately run in the full
focused attempt and failed because the pre-existing dirty
`results/simulation/SIM-004_navigation_backend.json` no longer matches its
Acceptance SHA256 (82 changed lines).  This correction did not modify that
protected file.

```text
python -m py_compile src/simulation_runtime/provenance_qualification.py \
  scripts/q01_execution_adapters.py \
  scripts/run_simulation_provenance_qualification.py \
  src/simulation_runtime/failure_recovery.py
PASS

git diff --check
PASS
```

### CANONICAL_COMPLETE

NOT COMPLETE.  The canonical preflight remains blocked by SIM-008 before a
complete eleven-subject aggregate can be produced.

## 7. Canonical Preflight

Executed with the established Q01 Python interpreter:

```text
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  scripts/run_simulation_provenance_qualification.py \
  --output /tmp/SIM-Q01-MIN_preflight.json \
  --report /tmp/SIM-Q01-MIN_preflight.md
```

The first run reached SIM-009 and demonstrated that the manifest validation
blocker was removed; its first next error was the bounded Gazebo stats sidecar
timeout.  After the sidecar correction, the next run stopped in the prior
SIM-008 supplier at `MISSING_STRUCTURED_SIMULATION_TIME` before subjects could
be aggregated.  The Python process terminated non-zero due to that unhandled
supplier `ValueError`; no `/tmp` JSON or Markdown preflight artifact exists.

Therefore:

```text
subject count: unavailable
missing subjects: unavailable
extra subjects: unavailable
binding errors: unavailable
task-specific result: unavailable
```

**Exact remaining blocker:** SIM-008 live supplier did not produce a
structured simulator-time observation in this shared preflight runtime.

## 8. Protected Scope Verification

| Scope | Status |
| --- | --- |
| Accepted SIM-004 artifacts | UNCHANGED by this correction |
| Accepted SIM-005 artifacts | UNCHANGED |
| Accepted SIM-007 artifacts | UNCHANGED |
| Accepted SIM-008 artifacts | UNCHANGED by this correction |
| Accepted SIM-009 artifacts | UNCHANGED |
| MIN-Q01 architecture/scope | UNCHANGED |

The worktree already contained dirty TASK-SIM-Q01-MIN files, including the
SIM-004 and SIM-008 current-worktree Evidence files.  They were preserved;
none was written by this correction or by the `/tmp` preflight.

## 9. Final State

```text
NOT_READY_FOR_ORCHESTRATOR_RESUME
```

The exact remaining blocker is the SIM-008 structured simulation-time failure
in the combined canonical preflight runtime.

## 10. Next Action

Diagnose the SIM-008 preflight-only runtime regression at the boundary between
its canonical live supplier and structured simulation-time extraction.  Do not
restart TASK-SIM-Q01-MIN and do not alter the frozen MIN-Q01 scope.
