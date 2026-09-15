# TASK-SIM-E2E — Simulation Qualification Gate

## 1. Objective

Evaluate the accepted Simulation Week A/B evidence and decide whether the ROS 2 Jazzy + Gazebo Harmonic + MuJoCo Simulation First lane is substantively qualified.

This TASK is an evidence-consumption gate only.

It must return exactly:

```text
SIM_E2E_QUALIFIED
SIM_E2E_NOT_QUALIFIED
```

A truthful `SIM_E2E_NOT_QUALIFIED` is a valid gate-task completion outcome.

---

## 2. Dependencies

All dependencies below must be independently `ACCEPTED` with their required READY result:

- `TASK-SIM-003`
  - Required result: `SIM_BASELINE_READY`
  - Verify from: `results/reviews/SIM-003_acceptance.json`

- `TASK-SIM-004`
  - Required result: `SIM_NAVIGATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-004_acceptance.json`

- `TASK-SIM-005`
  - Required result: `SIM_MANIPULATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-005_acceptance.json`

- `TASK-SIM-006`
  - Required result: `SIM_VERIFICATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-006_acceptance.json`

- `TASK-SIM-007`
  - Required result: `SIM_MISSION_INTEGRATION_READY`
  - Verify from: `results/reviews/SIM-007_acceptance.json`

- `TASK-SIM-008`
  - Required result: `SIM_NORMAL_E2E_READY`
  - Verify from: `results/reviews/SIM-008_acceptance.json`

- `TASK-SIM-009`
  - Required result: `SIM_FAILURE_SUITE_READY`
  - Verify from: `results/reviews/SIM-009_acceptance.json`

- `TASK-SIM-010`
  - Required result: `SIM_OBSERVABILITY_REGRESSION_READY`
  - Verify from: `results/reviews/SIM-010_acceptance.json`

An accepted BLOCKED predecessor is trustworthy but non-qualifying.

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-003_acceptance.json`
  - Purpose: Verify accepted Simulation baseline readiness.

- `results/reviews/SIM-004_acceptance.json`
  - Purpose: Verify accepted ROS 2 Jazzy / Gazebo Navigation backend readiness.

- `results/reviews/SIM-005_acceptance.json`
  - Purpose: Verify accepted MuJoCo manipulation backend readiness.

- `results/reviews/SIM-006_acceptance.json`
  - Purpose: Verify accepted cross-simulator Verification readiness.

- `results/reviews/SIM-007_acceptance.json`
  - Purpose: Verify accepted Mission/backend-profile integration readiness.

- `results/reviews/SIM-008_acceptance.json`
  - Purpose: Verify accepted canonical Gazebo normal system E2E.

- `results/reviews/SIM-009_acceptance.json`
  - Purpose: Verify accepted multi-layer failure/recovery suite.

- `results/reviews/SIM-010_acceptance.json`
  - Purpose: Verify accepted observability/regression source index.

- `results/simulation/SIM-010_observability_regression.json`
  - Purpose: Provide the canonical accepted-source/evidence/hash index and final regression/provenance summary consumed by this gate.

### 3.2 Conditional

- `results/simulation/SIM-003_baseline.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Resolve baseline/toolchain provenance inconsistency.

- `results/simulation/SIM-004_navigation_backend.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve Gazebo Navigation qualification evidence inconsistency.

- `results/simulation/SIM-005_mujoco_vla_backend.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve MuJoCo manipulation qualification evidence inconsistency.

- `results/simulation/SIM-006_verification_backend.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve cross-simulator Verification qualification evidence inconsistency.

- `results/simulation/SIM-008_normal_system_e2e.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve canonical normal E2E evidence inconsistency.

- `results/simulation/SIM-009_failure_recovery.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve failure-suite evidence inconsistency.

- `results/reviews/SIM-GATE_acceptance.json`
  - Read when: `PREREQUISITE_UNCLEAR | SOURCE_CONFLICT`
  - Purpose: Resolve original Simulation Lane authorization ambiguity.

- `context/simulation_task_mapping_v2.md`
  - Read when: `REQUIREMENT_AMBIGUITY | ARCHITECTURE_CONFLICT`
  - Purpose: Resolve qualification-matrix or simulator-authority ambiguity.

---

## 4. Frozen References

Qualification matrix:

```yaml
baseline:
  sim_baseline_bound: PASS
  accepted_contract_regression: PASS

deterministic:
  L0_contract_runtime: PASS
  timeout_reconciliation: PASS

gazebo:
  ros2_jazzy_gazebo_navigation: PASS
  normal_system_e2e: PASS
  required_navigation_system_failures: PASS

mujoco:
  manipulation_backend: PASS
  required_manipulation_failures: PASS
  model_config_provenance: PASS

verification:
  cross_simulator_verification: PASS
  uncertain_never_auto_success: PASS

system:
  required_failure_cases: PASS
  forbidden_state_transition: false
  leaked_process: false
  evidence_reproducible: true
  regression_green: true
  observability_sufficient: true
  physical_dependency: false
  dual_world_cosimulation_required: false
```

Authorization invariant:

- `SIM_E2E_QUALIFIED` remains Simulation-only evidence.
- It does not authorize physical motion, hardware freeze, Dataset V1, SmolVLA fine-tuning, teleoperation, `TASK-W1-001`, or `TASK-W1-002`.

---

## 5. Scope

This TASK must:

1. verify every mandatory predecessor acceptance artifact and required READY result;
2. verify acceptance-to-evidence hash bindings, reviewed revisions, and the SIM-010 accepted-source index;
3. reconstruct the qualification matrix from underlying accepted evidence rather than trusting self-reported `qualified=true`;
4. verify deterministic L0 contract/reconciliation coverage;
5. verify ROS 2 Jazzy + Gazebo Harmonic Navigation and normal system E2E coverage;
6. verify MuJoCo manipulation backend and required manipulation-failure coverage;
7. verify cross-simulator Verification and `uncertain` non-success behavior;
8. verify mandatory failure/recovery coverage, bounded cleanup, evidence reproducibility, regression, and observability;
9. verify `physical_dependency = false`;
10. verify the integrated L2 world authority is Gazebo and that no qualification criterion requires live dual-world Gazebo↔MuJoCo co-simulation;
11. produce machine-readable gate Evidence and human-readable report;
12. return exactly `SIM_E2E_QUALIFIED` or `SIM_E2E_NOT_QUALIFIED`.

This TASK must not implement remediation.

---

## 6. Non-goals

This TASK must not:

- modify SIM-003 through SIM-010 implementation or evidence;
- rerun implementation to fix a failed predecessor;
- install or repair simulation dependencies;
- add missing failure scenarios;
- alter the qualification matrix to force a pass;
- authorize hardware selection automatically;
- authorize original Week tasks, physical motion, Dataset V1, teleoperation, or fine-tuning;
- create live Gazebo↔MuJoCo co-simulation.

---

## 7. Target Areas

### Implementation

- `scripts/`
  - Create a fail-closed Simulation E2E qualification verifier if no repository-equivalent verifier exists.

- `docs/simulation/`
  - Create the human-readable Simulation qualification report.

### Tests

- `tests/test_simulation_e2e_qualification.py`

### Evidence

- `results/simulation/SIM-E2E_qualification.json`

---

## 8. Requirements

### R1 — Exact predecessor acceptance

All eight predecessor tasks must be independently accepted with their required READY outcome.

### R2 — Immutable binding validation

The gate must validate acceptance/evidence hashes, reviewed revisions, and the SIM-010 source index. Missing or stale binding is non-qualifying.

### R3 — Baseline qualification

`SIM_BASELINE_V1` and accepted L0 contract/smoke regression must be valid.

### R4 — Gazebo qualification

Accepted Evidence must prove ROS 2 Jazzy + Gazebo Harmonic Navigation, canonical normal system E2E, and required Navigation/system failure coverage.

### R5 — MuJoCo qualification

Accepted Evidence must prove the MuJoCo manipulation backend, required manipulation failures, and reproducible model/config provenance.

### R6 — Verification qualification

Accepted Evidence must prove cross-simulator Verification and the invariant that `uncertain` never becomes success without reconciliation.

### R7 — Failure/recovery qualification

All mandatory failure classes must have accepted outcomes for retry/reconcile/recover/HITL/fail-closed behavior.

### R8 — Process and state safety

Evidence must prove no forbidden state transition, no leaked task-started process, and bounded execution/cleanup.

### R9 — Regression and reproducibility

SIM-010 must establish reproducible evidence, green required regression, and sufficient observability.

### R10 — Physical isolation

Qualification must verify `physical_dependency = false` and must not reinterpret candidate hardware as selected/frozen targets.

### R11 — Single integrated world authority

Qualification must verify Gazebo is the L2 integrated world and `dual_world_cosimulation_required = false`.

### R12 — Decision reconstruction

`SIM_E2E_QUALIFIED` may be emitted only when every mandatory matrix predicate passes. Any failed, missing, ambiguous, or unverified mandatory predicate yields `SIM_E2E_NOT_QUALIFIED`.

### R13 — Authorization preservation

The gate output must explicitly preserve:

```text
TASK-W1-001 authorized = false
TASK-W1-002 authorized = false
Dataset V1 authorized = false
SmolVLA fine-tuning authorized = false
physical motion authorized = false
hardware target frozen = false
```

unless a separately accepted authoritative source outside this Simulation gate has legitimately changed one of those values.

---

## 9. Failure / Safety Behavior

- Fail closed on missing acceptance, BLOCKED predecessor, hash mismatch, stale evidence, contradictory provenance, incomplete scenario coverage, or qualification ambiguity.
- Self-reported PASS/READY/QUALIFIED fields are insufficient without independent accepted bindings.
- No failed qualification may be repaired in this TASK.
- A truthful `SIM_E2E_NOT_QUALIFIED` remains a valid implementation result.
- No gate action may start physical hardware or simulator remediation workloads beyond bounded read-only/evidence verification required by the verifier.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_e2e_qualification.py
```

Run the task-owned qualification verifier.

Expected proof:

- accepted READY predecessor chain validates;
- source index/hash bindings validate;
- every qualification-matrix predicate is reconstructed;
- tampered/missing/BLOCKED inputs fail closed;
- physical authorization invariants remain unchanged;
- `SIM_E2E_QUALIFIED` cannot be forged by changing a top-level field.

### Regression

```text
NOT REQUIRED
```

Reason:

- this TASK is an evidence-only gate;
- SIM-010 already owns the required full repository regression;
- if this TASK changes shared runtime/contract code, that change violates Scope and must be removed rather than justified with a new regression run.

### Additional checks

```bash
git diff --check
```

---

## 11. Evidence

```text
Evidence required: YES
```

Path:

```text
results/simulation/SIM-E2E_qualification.json
```

Evidence must prove:

- exact predecessor acceptances/results;
- acceptance/evidence/source-index hash bindings;
- reconstructed qualification matrix;
- final gate result;
- explicit preserved authorization snapshot;
- no physical dependency;
- Gazebo integrated-world authority;
- MuJoCo component-bench role;
- no required dual-world co-simulation;
- source Git SHA / verifier version / validation command provenance.

Human-readable companion:

```text
docs/simulation/simulation_e2e_qualification_v1.md
```

---

## 12. Exit Criteria

- EC1. All required predecessor tasks are independently accepted with their required READY outcome.
- EC2. Acceptance/evidence/source-index bindings and reviewed revisions are valid.
- EC3. Every mandatory deterministic, Gazebo, MuJoCo, Verification, failure, regression, observability, and reproducibility predicate is reconstructed from accepted evidence.
- EC4. Physical isolation and Gazebo-single-world authority are preserved; live dual-world co-simulation is not required.
- EC5. Required Evidence/report are internally consistent and tamper/fail-closed tests pass.
- EC6. The gate performs no remediation and modifies no predecessor Evidence.
- EC7. Final result is exactly `SIM_E2E_QUALIFIED` or `SIM_E2E_NOT_QUALIFIED`.
- EC8. Original Week/physical/training/hardware-freeze authorizations remain separately gated and are not elevated by this result.

Each criterion is evaluated as:

```text
PASS
FAIL
NOT APPLICABLE
```

---

## 13. Workflow Handoff

Implementation:

```text
prompts/codex/implement_task_v2.md
```

After successful implementation:

```text
Independent Read-only Review
```

Implementation completion does not imply Review acceptance.

Only post-review `ACCEPT + SIM_E2E_QUALIFIED` completes the Simulation First qualification stage.

It does not automatically authorize `TASK-HW-SELECT-001` or any original Week task; those remain subject to their own specification / architecture / authorization workflow.
