# Review — TASK-SIM-010

- Recommendation: REJECT
- Failed Gates: Scope, Requirements, Contract, Invariants, Tests, Evidence
- Validation: focused PASS (`6 passed`); regression FAIL (`4 failed, 347 passed`), with the same four node IDs and failure signatures reproduced at baseline commit `6909c6cceb727598570f6e170ae8d1d293418c9a`; `git diff --check` PASS
- Evidence: FAIL — `results/simulation/SIM-010_observability_regression.json` reports `SIM_OBSERVABILITY_REGRESSION_READY` from synthesized provenance and correlation values

## Blocking Findings

### SIM010-REV-001 — BLOCKER

- Requirement / Contract: R2–R10, R12; EC2–EC5, EC8; fail-closed Evidence integrity
- File / Symbol: `src/simulation_runtime/observability_regression.py::_normalize_evidence`, `build_regression_evidence`
- Issue: Predecessor fields that are missing or structurally unresolved are replaced with invented identities, labels, source hashes, simulator provenance, scenarios, invariants, and replay outcomes. The generated index therefore marks placeholders such as `accepted-sim-003-mission_id` as verified and returns `SIM_OBSERVABILITY_REGRESSION_READY` without preserving the actual accepted trace/scenario relationships.
- Why it blocks acceptance: Missing provenance and unbound scenarios must fail closed; synthetic PASS inputs make the canonical Evidence contradict the accepted artifacts and cannot establish reproducible correlation, backend provenance, replay, or semantic regression.
- Recommended remediation: Normalize each predecessor through explicit task-specific extraction that preserves real relationships and exact source/config hashes; treat every unavailable required field, scenario, label, or invariant as a blocking failure rather than manufacturing a value.

### SIM010-REV-002 — HIGH

- Requirement / Contract: diagnosis Required Verification; R10–R11; test adequacy
- File / Symbol: `scripts/run_simulation_observability_regression.py::main`, `tests/test_simulation_observability_regression.py`
- Issue: `PROVEN_PREEXISTING` is inferred from a hard-coded current failure-node set without executing the declared baseline or comparing failure signatures. Tests omit the diagnosis-mandated invalid/missing commit, missing blob, malformed JSON, task mismatch, rich hash/path conflict, and synthetic-normalization rejection cases.
- Why it blocks acceptance: A changed failure with the same node ID can be mislabeled pre-existing, and the resolver's required fail-closed boundaries are not regression-protected.
- Recommended remediation: Produce baseline/current results from the same command in isolated Git states and compare both node IDs and stable signatures; add focused negative coverage for every diagnosis-mandated resolver failure and missing normalized field.

```yaml
acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: TASK-SIM-010
  review_decision: REJECT
  reviewed_commit: 5a15ecb1073df0ed9bde3139a0ce1d0f956f1ff6
  task_specific_decision: SIM_OBSERVABILITY_REGRESSION_READY

  task_spec:
    path: tasks/TASK-SIM-010.md
    sha256: f9f2ff5d29e5acd263fad7d6e88762e8bee098064208a0ad1a3854ffebaae3e4

  evidence:
    required: true
    path: results/simulation/SIM-010_observability_regression.json
    sha256: e00e68d13386d3fa28da9f426ff5ab453c298d4a6e00d201bf691910ec358e0a

  supporting_artifacts:
    - path: docs/simulation/simulation_observability_regression_v1.md
      sha256: 3ad2fbe9d1a1422948b2e76f2729ca0143124878b38db60bc6028e619a30d52e

  acceptance_recording_eligible: false
  blocking_reason: Synthetic normalized provenance and incomplete baseline/fail-closed verification make READY evidence untrustworthy.
```
