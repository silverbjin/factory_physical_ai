# TASK-SIM-010 — Simulator-aware Observability / Evidence / Regression

## 1. Objective

Create a unified, auditable Simulation observability and regression layer for deterministic, Gazebo, MuJoCo, Verification, normal E2E, and failure/recovery results.

The completed TASK must make Simulation runs reproducible and traceable by binding Mission/action/correlation identities, backend provenance, simulator configuration, source hashes, replay/regression results, and accepted predecessor artifacts into one evidence index for `TASK-SIM-E2E`.

---

## 2. Dependencies

- `TASK-SIM-009`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_FAILURE_SUITE_READY`
  - Verify from: `results/reviews/SIM-009_acceptance.json`

- `TASK-SIM-008`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_NORMAL_E2E_READY`
  - Verify from: `results/reviews/SIM-008_acceptance.json`

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-008_acceptance.json`
  - Purpose: Bind the accepted normal system E2E evidence.

- `results/reviews/SIM-009_acceptance.json`
  - Purpose: Bind the accepted multi-layer failure/recovery evidence.

- `results/reviews/SIM-003_acceptance.json`
  - Purpose: Bind the accepted Simulation toolchain/baseline revision used for provenance.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Preserve identity/lifecycle semantics while defining common trace and regression correlation.

### 3.2 Conditional

- `results/simulation/SIM-008_normal_system_e2e.json`
  - Read when: `EVIDENCE_FAILURE | VALIDATION_FAILURE`
  - Purpose: Resolve missing/ambiguous normal-run provenance referenced by its acceptance artifact.

- `results/simulation/SIM-009_failure_recovery.json`
  - Read when: `EVIDENCE_FAILURE | VALIDATION_FAILURE`
  - Purpose: Resolve missing/ambiguous failure-run provenance referenced by its acceptance artifact.

- `results/simulation/SIM-004_navigation_backend.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve Gazebo/Navigation provenance missing from higher-level accepted evidence.

- `results/simulation/SIM-005_mujoco_vla_backend.json`
  - Read when: `EVIDENCE_FAILURE`
  - Purpose: Resolve MuJoCo/model provenance missing from higher-level accepted evidence.

- `context/simulation_task_mapping_v2.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve simulator-specific provenance separation or qualification intent.

---

## 4. Frozen References

- Common identity/provenance:
  - Mission ID;
  - request/action/correlation/trace identity;
  - Skill and Verification result;
  - failure code;
  - recovery decision;
  - contract version;
  - Git SHA/source hashes;
  - backend profile.

- Gazebo provenance where applicable:
  - ROS 2 identity;
  - Gazebo release/version;
  - world/model hash;
  - `ros_gz` bridge/config hash;
  - launch/config hash;
  - simulation time / wall time / bounded execution indicator.

- MuJoCo provenance where applicable:
  - MuJoCo version;
  - model/scene/config hash;
  - deterministic seed/initialization identity;
  - timestep/step settings;
  - initial-state identity.

- Simulation metrics must remain separate from physical/production claims.

---

## 5. Scope

This TASK must:

1. define one normalized Simulation run-evidence envelope for deterministic/Gazebo/MuJoCo/system results without altering existing public execution contracts;
2. collect or index provenance from accepted SIM-003 through SIM-009 artifacts;
3. create a canonical accepted-source index containing exact acceptance/evidence paths and hashes for downstream gate evaluation;
4. correlate Mission/action/Skill/Verification/failure/recovery timelines;
5. record backend-profile and simulator-specific provenance;
6. implement deterministic replay/regression comparison where exact replay is meaningful;
7. implement semantic regression comparison for physics runs where bitwise trace identity is not required;
8. compare current required Simulation scenarios to their accepted expected outcomes;
9. run the required Simulation-focused regression suite;
10. produce a machine-readable regression/evidence artifact with:
    - `SIM_OBSERVABILITY_REGRESSION_READY`; or
    - `SIM_OBSERVABILITY_REGRESSION_BLOCKED`.

---

## 6. Non-goals

This TASK must not:

- add new Mission/Skill/Verification behavior;
- alter simulator physics to make regression pass;
- generate physical latency, safety, reliability, or production claims;
- perform 24/72-hour production soak tests;
- fine-tune or benchmark VLA model quality;
- create live Gazebo↔MuJoCo world synchronization;
- remediate failures owned by SIM-004 through SIM-009 within this TASK.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - common Simulation provenance / replay / regression helpers when required.

- `scripts/`
  - regression/evidence aggregator and replay runner.

- `docs/simulation/`
  - human-readable observability/regression report.

### Tests

- `tests/test_simulation_observability_regression.py`

### Evidence

- `results/simulation/SIM-010_observability_regression.json`

---

## 8. Requirements

### R1 — Accepted-source index

Evidence must include an exact acceptance/evidence/hash index for `TASK-SIM-003` through `TASK-SIM-009`.

### R2 — Common correlation

Every indexed run must preserve Mission, action/request, Skill, Verification, failure/recovery, and trace/correlation identity sufficient to reconstruct the execution path.

### R3 — Backend profile provenance

Every run must identify the backend profile and its exact relevant source/config hashes.

### R4 — Gazebo provenance

Gazebo runs must record ROS 2 identity, Gazebo release/version, world/model/config/bridge/launch hashes, and simulation/wall-time fields required for reproduction.

### R5 — MuJoCo provenance

MuJoCo runs must record MuJoCo version, model/scene/config hashes, initialization/seed identity, timestep/step settings, and initial-state identity.

### R6 — Deterministic replay

L0 deterministic runs must reproduce equivalent decisions and lifecycle outcomes for equivalent inputs/state.

### R7 — Physics semantic regression

Gazebo/MuJoCo regression must compare stable scenario outcome, contract lifecycle, required state invariants, and declared tolerance-based measurements rather than require bitwise-identical physics traces.

### R8 — Normal/failure suite coverage

The regression index must include accepted normal E2E and all mandatory accepted failure/recovery scenario IDs.

### R9 — Simulation-only labeling

Every metric/result exposed by this task must be labeled as Simulation evidence and must not imply physical/production performance.

### R10 — Evidence integrity

Missing source hash, stale acceptance, contradictory run identity, or unbound scenario must fail the regression evidence closed.

### R11 — Full regression result

The repository regression command declared in this TASK must be executed and recorded.

### R12 — Task-specific result

Evidence must report exactly:

```text
SIM_OBSERVABILITY_REGRESSION_READY
SIM_OBSERVABILITY_REGRESSION_BLOCKED
```

---

## 9. Failure / Safety Behavior

- Missing or hash-mismatched accepted artifacts fail closed.
- Regression must not auto-update expected outcomes to make failures disappear.
- Physics nondeterminism must be handled only through explicit semantic/tolerance criteria, never by ignoring failed invariants.
- Replay/regression tools must not start physical hardware.
- No failed predecessor behavior may be repaired in this task; report the blocking source task/scenario instead.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_observability_regression.py
```

Run the task-owned regression/evidence aggregator.

Expected proof:

- accepted-source index is complete;
- normal and failure scenarios are traceable;
- deterministic replay is stable;
- Gazebo/MuJoCo semantic regression is evaluated from frozen provenance;
- stale/mutated evidence fails;
- Simulation-only labeling is preserved.

### Regression

```text
REQUIRED
```

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
```

The command, exit code, test count/result, and Git SHA must be recorded in Evidence.

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
results/simulation/SIM-010_observability_regression.json
```

Evidence must prove:

- exact accepted-source index for SIM-003 through SIM-009;
- common Mission/action/Skill/Verification/failure/recovery correlation;
- Gazebo and MuJoCo provenance;
- deterministic replay result;
- physics semantic regression result;
- normal/failure suite coverage;
- full repository regression result;
- Simulation-only claim labeling;
- task-specific result `SIM_OBSERVABILITY_REGRESSION_READY | SIM_OBSERVABILITY_REGRESSION_BLOCKED`.

Human-readable companion:

```text
docs/simulation/simulation_observability_regression_v1.md
```

---

## 12. Exit Criteria

- EC1. Accepted-source/evidence/hash index for SIM-003 through SIM-009 is complete and valid.
- EC2. Mission/action/Skill/Verification/failure/recovery traces are reconstructable from structured evidence.
- EC3. Required Gazebo and MuJoCo provenance fields are recorded for applicable runs.
- EC4. Deterministic replay and physics semantic regression pass according to declared criteria.
- EC5. Normal E2E and mandatory failure scenarios are all represented in the regression evidence.
- EC6. Full repository regression and focused validation pass, or the task truthfully returns BLOCKED.
- EC7. No physical/production claim, behavior remediation, or other Non-goal was introduced.
- EC8. Final task result is exactly `SIM_OBSERVABILITY_REGRESSION_READY` or `SIM_OBSERVABILITY_REGRESSION_BLOCKED`.

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

`TASK-SIM-E2E` may proceed only after independent acceptance with `SIM_OBSERVABILITY_REGRESSION_READY`.
