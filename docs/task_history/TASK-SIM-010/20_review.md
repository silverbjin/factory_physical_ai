# Review — TASK-SIM-010

- Recommendation: REJECT
- Failed Gates: Requirements, Invariants, Tests, Regression, Evidence
- Validation: focused PASS (`44 passed`); required repository regression FAIL (`4 failed, 385 passed`); `git diff --check` PASS
- Evidence: FAIL — indexed run-validation blockers and a failed full regression are reported while `task_specific_result` remains `SIM_OBSERVABILITY_REGRESSION_READY`

## Blocking Findings

### SIM010-RR-001 — BLOCKER

- Requirement / Contract: R2, R3, R4, R10, R12; fail-closed evidence behavior
- File / Symbol: `src/simulation_runtime/observability_regression.py::build_regression_evidence`
- Issue: A valid Q01 binding clears every `required_run_failures` entry even though the accepted-source index still reports missing correlation, source hashes, and Gazebo provenance. The canonical artifact therefore returns `SIM_OBSERVABILITY_REGRESSION_READY` with multiple `run_validation.status = BLOCKED` rows.
- Why it blocks acceptance: Missing source hashes and incomplete run identity/provenance are explicitly required to fail the regression evidence closed.
- Recommended remediation: Keep predecessor diagnostics gating readiness unless each failed indexed run is replaced by an explicit, requirement-scoped qualified authority that proves the same run fields; add negative tests showing that Q01 cannot globally erase unrelated indexed-run failures.

### SIM010-RR-002 — HIGH

- Requirement / Contract: R11, EC6; canonical Evidence integrity
- File / Symbol: `scripts/run_simulation_observability_regression.py::main`; `results/simulation/SIM-010_observability_regression.json`
- Issue: The artifact records `full_repository_regression.result = FAIL` and exit code 1 but preserves `SIM_OBSERVABILITY_REGRESSION_READY`; it also omits the required test count/result summary. The runner validates a detached `HEAD`, so the current uncommitted post-Fix implementation and six added focused tests are absent from the recorded candidate run.
- Why it blocks acceptance: EC6 requires the full regression to pass or the task to return BLOCKED, and Evidence must describe the implementation actually reviewed.
- Recommended remediation: Record the exact reviewed source state and test summary, and emit `SIM_OBSERVABILITY_REGRESSION_BLOCKED` whenever the required repository regression fails unless the TASK specification is explicitly changed to authorize a different gate.

```yaml
acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: TASK-SIM-010
  review_decision: REJECT
  reviewed_commit: 0dc8e71c3b2aec56557fdfb54de83d3e446cd0a7
  task_specific_decision: SIM_OBSERVABILITY_REGRESSION_READY

  task_spec:
    path: tasks/TASK-SIM-010.md
    sha256: f66dd62459de55feb9b76d5c1eec5e45c28181ad9840079880d40429d03fff3d

  evidence:
    required: true
    path: results/simulation/SIM-010_observability_regression.json
    sha256: 3e0d45c3fd573cd952b1447720bdcb5ca70595d0522b4899ec458a33c20f7c7a

  supporting_artifacts:
    - path: docs/simulation/simulation_observability_regression_v1.md
      sha256: 1afba5664e6df8a1515016a900242a397dbb432c1f0f975609bcf0bf62e4178a

  acceptance_recording_eligible: false
  blocking_reason: Fail-open indexed-run validation and failed/stale full-regression Evidence.
```
