# TASK-SIM-E2E — Simulation Qualification Gate

## 1. Objective

Evaluate the accepted Simulation Week A/B evidence and decide whether the ROS 2 Jazzy + Gazebo Harmonic + MuJoCo Simulation First lane is substantively qualified.

This TASK is an evidence-consumption gate only.

The gate decision vocabulary is exactly:

```text
SIM_E2E_QUALIFIED
SIM_E2E_NOT_QUALIFIED
```

A truthful `SIM_E2E_NOT_QUALIFIED` is a valid gate-task completion outcome.

### 1.1 CLI decision contract

The task-owned verifier must expose an automation-safe CLI contract:

- `stdout`:
  - on a completed qualification evaluation, emit exactly one final decision line;
  - the line must be exactly `SIM_E2E_QUALIFIED` or `SIM_E2E_NOT_QUALIFIED`;
  - no additional diagnostic text may be written to `stdout`.
- `stderr`:
  - diagnostic, validation, and failure-detail output is allowed.
- exit code:
  - `0`: the verifier completed the gate evaluation and emitted either valid gate decision;
  - non-zero: verifier execution/internal failure prevented a trustworthy gate evaluation, for example invalid CLI invocation or verifier implementation error.

A negative gate decision is not a verifier execution failure. Missing, malformed, stale, contradictory, or non-qualifying task evidence that the verifier can evaluate must therefore produce `SIM_E2E_NOT_QUALIFIED` with exit code `0`.

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

### 3.1 Required acceptance and index sources

- `results/reviews/SIM-003_acceptance.json`
  - Purpose: Verify accepted Simulation baseline readiness and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-004_acceptance.json`
  - Purpose: Verify accepted ROS 2 Jazzy / Gazebo Navigation backend readiness and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-005_acceptance.json`
  - Purpose: Verify accepted MuJoCo manipulation backend readiness and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-006_acceptance.json`
  - Purpose: Verify accepted cross-simulator Verification readiness and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-007_acceptance.json`
  - Purpose: Verify accepted Mission/backend-profile integration readiness and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-008_acceptance.json`
  - Purpose: Verify accepted canonical Gazebo normal system E2E and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-009_acceptance.json`
  - Purpose: Verify accepted multi-layer failure/recovery suite and resolve its immutable accepted Evidence binding.

- `results/reviews/SIM-010_acceptance.json`
  - Purpose: Verify accepted observability/regression readiness and resolve the accepted SIM-010 Evidence binding.

- `results/simulation/SIM-010_observability_regression.json`
  - Purpose: Provide the canonical accepted-source/evidence/hash index and final regression/provenance summary consumed by this gate.

### 3.2 Required underlying accepted Evidence

The verifier must not reconstruct qualification only from top-level READY/PASS/QUALIFIED fields or from the SIM-010 normalized summary.

For every predecessor `SIM-003` through `SIM-010`, the verifier must:

1. read the authoritative acceptance artifact;
2. resolve the accepted Evidence artifact from the acceptance binding and, where applicable, the SIM-010 accepted-source index;
3. verify the current Evidence content/hash/revision binding against the immutable accepted values;
4. read the bound underlying Evidence needed to reconstruct every mandatory qualification predicate owned by that source.

The acceptance/index binding is authoritative for locating the accepted Evidence. The verifier must not silently substitute a similarly named file, newest file, current-HEAD artifact, or guessed canonical path when the recorded accepted binding is missing or contradictory.

If an acceptance or SIM-010 source-index record does not expose enough information to locate and validate its underlying accepted Evidence unambiguously, the affected mandatory predicate is unverified and the gate result is `SIM_E2E_NOT_QUALIFIED`.

### 3.3 Conditional diagnostic sources

- `results/simulation/SIM-003_baseline.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Diagnose baseline/toolchain provenance inconsistency when this file is not already the accepted Evidence resolved by Section 3.2.

- `results/simulation/SIM-004_navigation_backend.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Diagnose Gazebo Navigation qualification evidence inconsistency when this file is not already the accepted Evidence resolved by Section 3.2.

- `results/simulation/SIM-005_mujoco_vla_backend.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Diagnose MuJoCo manipulation qualification evidence inconsistency when this file is not already the accepted Evidence resolved by Section 3.2.

- `results/simulation/SIM-006_verification_backend.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Diagnose cross-simulator Verification qualification evidence inconsistency when this file is not already the accepted Evidence resolved by Section 3.2.

- `results/simulation/SIM-008_normal_system_e2e.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Diagnose canonical normal E2E evidence inconsistency when this file is not already the accepted Evidence resolved by Section 3.2.

- `results/simulation/SIM-009_failure_recovery.json`
  - Read when: `EVIDENCE_FAILURE | SOURCE_CONFLICT`
  - Purpose: Diagnose failure-suite evidence inconsistency when this file is not already the accepted Evidence resolved by Section 3.2.

- `results/reviews/SIM-GATE_acceptance.json`
  - Read when: `PREREQUISITE_UNCLEAR | SOURCE_CONFLICT`
  - Purpose: Diagnose original Simulation Lane authorization ambiguity.

- `context/simulation_task_mapping_v2.md`
  - Read when: `REQUIREMENT_AMBIGUITY | ARCHITECTURE_CONFLICT`
  - Purpose: Diagnose qualification-matrix or simulator-authority ambiguity.

Conditional diagnostic sources are diagnostic-only after an immutable acceptance/Evidence/revision/source-index binding has failed.

They may explain a failure or conflict, but they must not:

- replace a missing authoritative acceptance binding;
- rebind an acceptance to different Evidence;
- promote a hash/revision/source-index mismatch back to qualifying;
- repair stale Evidence;
- override a BLOCKED or wrong READY predecessor;
- change a failed or unverified mandatory predicate to PASS.

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

### 4.1 Predicate-source reconstruction contract

Every matrix predicate must be reconstructed from an immutable accepted source chain:

```text
required predecessor acceptance
  -> accepted Evidence binding
  -> SIM-010 accepted-source/index consistency, where applicable
  -> underlying accepted Evidence
  -> predicate-specific proof
  -> normalized matrix predicate
```

The SIM-010 accepted-source index is the canonical source locator/index for this gate, but a normalized PASS/true value in that index is not sufficient proof by itself. The verifier must validate the referenced immutable binding and read the underlying accepted Evidence required for the predicate. The index must provide an unambiguous accepted source chain for every mandatory predicate; this TASK intentionally does not guess predicate ownership from filenames or task numbering.

For each matrix predicate, the verifier must record in its output Evidence:

- predicate name;
- expected value;
- reconstructed actual value;
- source task(s);
- acceptance artifact(s);
- underlying Evidence path(s);
- verified accepted hash/revision binding(s);
- reconstruction status: `PASS | FAIL | UNVERIFIED`;
- concise reason when not `PASS`.

If the accepted-source index does not identify a unique authoritative source chain for a mandatory predicate, or if multiple accepted sources conflict, that predicate is `UNVERIFIED` and the final gate result is `SIM_E2E_NOT_QUALIFIED`.

The verifier must use the canonical fields/schema present in the accepted artifacts. It must not invent missing fields, infer success from filenames, derive PASS from prose-only similarity, or substitute a different semantic criterion. If a predicate cannot be mapped unambiguously from the repository's accepted Evidence schema, it is `UNVERIFIED`.

### 4.2 Binding freshness definition

For this TASK, `stale evidence` does not mean merely that a predecessor was reviewed on a Git commit older than the current repository `HEAD`.

Evidence is stale when its current immutable identity no longer matches the values recorded by its authoritative accepted binding, including any required combination of:

- accepted Evidence path/identity;
- Evidence SHA-256 or accepted payload SHA-256;
- reviewed revision / reviewed commit;
- SIM-010 accepted-source/index binding;
- other immutable provenance values required by the predecessor acceptance schema.

A predecessor reviewed at an older commit remains potentially qualifying when its accepted Evidence and immutable bindings still validate exactly. Current repository `HEAD` alone must not be used as a freshness test.

### 4.3 Authorization invariant

`SIM_E2E_QUALIFIED` remains Simulation-only evidence.

This gate must always emit and preserve the following authorization snapshot as `false`:

```text
TASK-W1-001 authorized = false
TASK-W1-002 authorized = false
Dataset V1 authorized = false
SmolVLA fine-tuning authorized = false
physical motion authorized = false
hardware target frozen = false
```

This TASK does not discover, consume, or apply external authorization overrides. A later separately specified and accepted authoritative gate may supersede these values independently; SIM-E2E itself has no authority to do so.

It therefore does not authorize physical motion, hardware freeze, Dataset V1, SmolVLA fine-tuning, teleoperation, `TASK-W1-001`, or `TASK-W1-002`.

---

## 5. Scope

This TASK must:

1. verify every mandatory predecessor acceptance artifact and required READY result;
2. verify acceptance-to-Evidence hash bindings, reviewed revisions, and the SIM-010 accepted-source index;
3. resolve and read underlying accepted Evidence through immutable acceptance/index bindings;
4. reconstruct the qualification matrix from underlying accepted Evidence rather than trusting self-reported `qualified=true`, READY, PASS, or normalized summary fields;
5. verify deterministic L0 contract/reconciliation coverage;
6. verify ROS 2 Jazzy + Gazebo Harmonic Navigation and normal system E2E coverage;
7. verify MuJoCo manipulation backend and required manipulation-failure coverage;
8. verify cross-simulator Verification and `uncertain` non-success behavior;
9. verify mandatory failure/recovery coverage, bounded cleanup, Evidence reproducibility, regression, and observability;
10. verify `physical_dependency = false`;
11. verify the integrated L2 world authority is Gazebo and that no qualification criterion requires live dual-world Gazebo↔MuJoCo co-simulation;
12. preserve the fixed non-authorization snapshot in Section 4.3;
13. produce machine-readable gate Evidence and human-readable report;
14. return exactly `SIM_E2E_QUALIFIED` or `SIM_E2E_NOT_QUALIFIED` under the CLI contract in Section 1.1.

This TASK must not implement remediation.

---

## 6. Non-goals

This TASK must not:

- modify SIM-003 through SIM-010 implementation or Evidence;
- rerun implementation to fix a failed predecessor;
- install or repair simulation dependencies;
- add missing failure scenarios;
- alter the qualification matrix to force a pass;
- rebind an accepted predecessor to different Evidence;
- treat a conditional diagnostic source as replacement accepted Evidence;
- authorize hardware selection automatically;
- discover or apply external authorization overrides;
- authorize original Week tasks, physical motion, Dataset V1, teleoperation, or fine-tuning;
- create live Gazebo↔MuJoCo co-simulation.

---

## 7. Target Areas

### 7.1 Implementation

- `scripts/`
  - Reuse a repository-equivalent Simulation E2E qualification verifier only when it already satisfies this TASK contract.
  - Otherwise create `scripts/verify_simulation_e2e_qualification.py`.
  - Use a pure evaluation core callable with an explicit repository root/input root, plus a thin CLI wrapper implementing Section 1.1.
  - The evaluator must not depend on mutating canonical Evidence to perform validation.

- `docs/simulation/`
  - Create the human-readable Simulation qualification report.

### 7.2 Tests

- `tests/test_simulation_e2e_qualification.py`
  - Use isolated temporary repository/input fixtures for tamper, missing, BLOCKED, stale, contradictory, and forged-top-level cases.
  - Tests must not mutate canonical predecessor acceptance or Evidence artifacts in place.

### 7.3 Evidence

- `results/simulation/SIM-E2E_qualification.json`

### 7.4 Task-owned change allowlist

Allowed task-owned additions/modifications are limited to:

```text
scripts/verify_simulation_e2e_qualification.py
tests/test_simulation_e2e_qualification.py
results/simulation/SIM-E2E_qualification.json
docs/simulation/simulation_e2e_qualification_v1.md
```

An existing repository-equivalent verifier may be minimally extended only if the change remains exclusively within the qualification-verifier concern and does not modify shared runtime/contract/simulation behavior.

Any modification to predecessor implementation/Evidence, shared simulation runtime, mission runtime, contract behavior, backend behavior, or unrelated production code is a Scope violation and must be removed rather than justified by additional regression testing.

---

## 8. Requirements

### R1 — Exact predecessor acceptance

All eight predecessor tasks must be independently accepted with their required READY outcome.

A missing acceptance, wrong READY result, or accepted BLOCKED predecessor is non-qualifying.

### R2 — Immutable binding validation

The gate must validate acceptance/Evidence hashes, reviewed revisions, and the SIM-010 source index.

Missing, contradictory, or stale immutable binding is non-qualifying.

Conditional diagnostic sources must not repair a failed immutable binding.

### R3 — Underlying Evidence consumption

The verifier must read the underlying accepted Evidence required for every mandatory matrix predicate through the immutable accepted binding chain defined in Sections 3.2 and 4.1.

A top-level `PASS`, `READY`, `qualified=true`, or normalized SIM-010 predicate value is insufficient by itself.

### R4 — Baseline qualification

`SIM_BASELINE_V1` and accepted L0 contract/smoke regression must be valid.

### R5 — Gazebo qualification

Accepted Evidence must prove ROS 2 Jazzy + Gazebo Harmonic Navigation, canonical normal system E2E, and required Navigation/system failure coverage.

### R6 — MuJoCo qualification

Accepted Evidence must prove the MuJoCo manipulation backend, required manipulation failures, and reproducible model/config provenance.

### R7 — Verification qualification

Accepted Evidence must prove cross-simulator Verification and the invariant that `uncertain` never becomes success without reconciliation.

### R8 — Failure/recovery qualification

All mandatory failure classes must have accepted outcomes for retry/reconcile/recover/HITL/fail-closed behavior.

### R9 — Process and state safety

Evidence must prove no forbidden state transition, no leaked task-started process, and bounded execution/cleanup.

### R10 — Regression and reproducibility

SIM-010 must establish reproducible Evidence, green required regression, and sufficient observability, with its accepted-source/index bindings validated against the underlying accepted sources.

### R11 — Physical isolation

Qualification must verify `physical_dependency = false` and must not reinterpret candidate hardware as selected/frozen targets.

### R12 — Single integrated world authority

Qualification must verify Gazebo is the L2 integrated world and `dual_world_cosimulation_required = false`.

### R13 — Decision reconstruction

`SIM_E2E_QUALIFIED` may be emitted only when every mandatory matrix predicate is independently reconstructed as qualifying from its validated accepted source chain.

Any failed, missing, ambiguous, contradictory, stale, or unverified mandatory predicate yields `SIM_E2E_NOT_QUALIFIED`.

### R14 — Authorization preservation

The gate output must explicitly preserve the fixed Section 4.3 authorization snapshot as `false`.

The verifier must not search for or apply external authorization overrides.

### R15 — Pure evaluation and non-mutation

Qualification evaluation must be read-only with respect to all predecessor acceptance and Evidence artifacts.

The verifier should separate evaluation logic from CLI/report writing so isolated fixtures can prove fail-closed behavior without altering canonical accepted inputs.

### R16 — Deterministic decision interface

A completed evaluation must obey Section 1.1 exactly so automation can distinguish:

- `SIM_E2E_QUALIFIED`;
- `SIM_E2E_NOT_QUALIFIED`;
- verifier execution/internal failure.

---

## 9. Failure / Safety Behavior

- Fail closed on missing acceptance, wrong READY outcome, BLOCKED predecessor, hash mismatch, stale Evidence, contradictory provenance, incomplete scenario coverage, source-index ambiguity, predicate ambiguity, or qualification ambiguity.
- Self-reported PASS/READY/QUALIFIED fields are insufficient without independent accepted bindings and underlying Evidence reconstruction.
- No failed immutable binding may be repaired, rebound, or promoted to PASS by reading a conditional diagnostic source.
- No failed qualification may be remediated in this TASK.
- A truthful `SIM_E2E_NOT_QUALIFIED` remains a valid implementation result and must use verifier exit code `0` when evaluation completed normally.
- No gate action may start physical hardware or simulator remediation workloads beyond bounded read-only/Evidence verification required by the verifier.
- The verifier must not mutate predecessor acceptance/Evidence during normal execution or test execution.

---

## 10. Validation

### 10.1 Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_e2e_qualification.py
```

Run the task-owned qualification verifier against the canonical repository inputs.

Expected proof:

- accepted READY predecessor chain validates;
- every accepted Evidence path/hash/revision binding validates;
- SIM-010 accepted-source/index bindings validate;
- every qualification-matrix predicate is reconstructed from underlying accepted Evidence;
- tampered inputs fail closed;
- missing acceptance/Evidence/index inputs fail closed;
- wrong READY and accepted BLOCKED inputs fail closed;
- stale immutable bindings fail closed without using current repository `HEAD` as the sole freshness criterion;
- contradictory source/index provenance fails closed;
- a conditional diagnostic source cannot repair a failed immutable binding;
- physical authorization invariants remain unchanged and false;
- `SIM_E2E_QUALIFIED` cannot be forged by changing a top-level PASS/READY/QUALIFIED field;
- canonical predecessor acceptance/Evidence files remain unmodified by tests;
- CLI stdout/exit-code behavior matches Section 1.1.

### 10.2 Regression

```text
NOT REQUIRED
```

Reason:

- this TASK is an Evidence-only gate;
- SIM-010 already owns the required full repository regression;
- if this TASK changes shared runtime/contract/backend code, that change violates Scope and must be removed rather than justified with a new regression run.

### 10.3 Additional checks

```bash
git diff --check
```

Also verify the changed-file set is consistent with the Section 7.4 task-owned change allowlist. Any out-of-scope production/runtime/predecessor-Evidence change is a task failure until removed.

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
- acceptance/Evidence/source-index hash and revision bindings;
- resolved underlying accepted Evidence identities;
- per-predicate source chain and reconstruction result;
- reconstructed qualification matrix;
- final gate result;
- explicit preserved authorization snapshot;
- no physical dependency;
- Gazebo integrated-world authority;
- MuJoCo component-bench role;
- no required dual-world co-simulation;
- verifier and evaluation provenance.

### 11.1 Required provenance fields

The gate Evidence must distinguish at least:

```text
evaluation_repo_head
verifier_identity_or_version
verifier_sha256_or_equivalent_immutable_identity
predecessor_reviewed_revisions
accepted_evidence_bindings
sim010_source_index_binding
validation_commands
```

`evaluation_repo_head` is contextual provenance only. It must not replace predecessor reviewed revisions or accepted Evidence hash bindings and must not be used alone to declare Evidence stale.

If the verifier is not yet committed when validation is performed, the Evidence/report must truthfully record the available immutable verifier identity and must not fabricate a Git commit SHA.

Human-readable companion:

```text
docs/simulation/simulation_e2e_qualification_v1.md
```

The human-readable report and machine-readable Evidence must agree on the final decision, failed/unverified predicates, source-binding status, authorization snapshot, and provenance.

---

## 12. Exit Criteria

- EC1. All required predecessor tasks are independently accepted with their required READY outcome.
- EC2. Acceptance/Evidence/source-index bindings and reviewed revisions are valid under the Section 4.2 freshness definition.
- EC3. Every mandatory deterministic, Gazebo, MuJoCo, Verification, failure, regression, observability, and reproducibility predicate is reconstructed from underlying accepted Evidence through a unique validated source chain.
- EC4. No conditional diagnostic source has repaired or replaced a failed immutable accepted binding.
- EC5. Physical isolation and Gazebo-single-world authority are preserved; live dual-world co-simulation is not required.
- EC6. Required Evidence/report are internally consistent and tamper/missing/BLOCKED/stale/contradiction/fail-closed tests pass.
- EC7. The gate performs no remediation and modifies no predecessor implementation, acceptance, or Evidence.
- EC8. Changed files remain within the task-owned Scope/allowlist.
- EC9. Final result is exactly `SIM_E2E_QUALIFIED` or `SIM_E2E_NOT_QUALIFIED`, and CLI behavior satisfies Section 1.1.
- EC10. Original Week/physical/training/hardware-freeze authorizations remain false within this gate and are not elevated by this result.

Each criterion is evaluated as:

```text
PASS
FAIL
NOT APPLICABLE
```

No mandatory qualification predicate may use `NOT APPLICABLE` to obtain `SIM_E2E_QUALIFIED`. `NOT APPLICABLE` is permitted only for an explicitly non-mandatory reporting criterion whose non-applicability is defined by this TASK or an already accepted authoritative contract.

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

A post-review `ACCEPT + SIM_E2E_NOT_QUALIFIED` may confirm that the gate implementation is correct while the Simulation First lane itself is not qualified; it does not complete the qualification stage.

This gate does not automatically authorize `TASK-HW-SELECT-001` or any original Week task; those remain subject to their own specification / architecture / authorization workflow.
