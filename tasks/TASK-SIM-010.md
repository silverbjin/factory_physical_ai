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

---

## 14. Addendum — Accepted Q01-MIN Additive Qualification Binding

This addendum is the minimum Q01 integration clarification authorized by
`docs/task_history/TASK-SIM-010/13_diagnosis.md`. It does not change the
objective, acceptance intent, requirements, exit criteria, or task-specific
result tokens of this TASK. It adds an immutable qualification input and the
fail-closed rules required to consume it.

The authority model is:

```text
Historical accepted predecessor truth
+
Accepted Q01 qualification truth
↓
Explicit downstream binding
↓
TASK-SIM-010 regression decision
```

Q01 is additive qualification authority. It MUST NOT rewrite historical
predecessor truth, fill a missing field in a historical accepted run, become a
replacement predecessor, be interpreted as the original SIM-008/SIM-009 run,
or silently repair SIM-004/SIM-005/SIM-007 historical Evidence.

### 14.1 Immutable Q01 binding

SIM-010 MUST resolve Q01 through this pinned chain:

```text
acceptance_recording_commit:
  a1f1539c27f61fb2ce52aed33ceaf1bfe343912c
acceptance_path:
  results/reviews/SIM-Q01-MIN_acceptance.json
acceptance_task_id:
  TASK-SIM-Q01-MIN
acceptance_status:
  ACCEPT
acceptance_workflow_complete:
  true
accepted_commit:
  b55bc4fc2435e83c3761457b92d9e14892e39435
evidence_path:
  results/simulation/SIM-Q01_provenance_qualification.json
evidence_sha256:
  dbd2fc20f6072f8889466fff29b80ec874d105b37c5633e909c633facdb2eb6a
compatibility_evidence_task_id:
  TASK-SIM-Q01
expected_task_specific_result:
  SIM_PROVENANCE_QUALIFICATION_READY
```

The Acceptance task ID and compatibility Evidence task ID are intentionally
different. Validation MUST check each against its pinned value and MUST NOT
apply a generic equality rule between them. The Acceptance must have
`status = ACCEPT` and `workflow_complete = true`. The exact Evidence blob must
be read from `accepted_commit`, its SHA256 must be recomputed, and its result
must equal `SIM_PROVENANCE_QUALIFICATION_READY`. Missing or conflicting Git
objects, fields, hashes, paths, task IDs, status, workflow state, or result
MUST fail closed. Q01 history MUST NOT be merged merely to expose the artifact.

### 14.2 Frozen operation-subject set

The authorized Q01 operation-subject set is exactly:

```text
q01-sim008-normal-system-authority

q01-sim009-SIM009-NAV-BLOCKED
q01-sim009-SIM009-NAV-ABORTED
q01-sim009-SIM009-NAV-TIMEOUT-RETRY
q01-sim009-SIM009-NAV-TF-UNAVAILABLE

q01-sim009-SIM009-VLA-GRASP-MISS
q01-sim009-SIM009-VLA-CONTACT-LOSS
q01-sim009-SIM009-VLA-WORKSPACE-LIMIT
q01-sim009-SIM009-VLA-TIMEOUT
q01-sim009-SIM009-VLA-AMBIGUOUS
q01-sim009-SIM009-VLA-UNKNOWN
```

Set equality, not subset inclusion, is required. A missing, extra, or duplicate
operation subject fails closed. Q01 data for SIM-004, SIM-005, and SIM-007 is
supporting immutable authority only and MUST NOT become an additional
regression operation subject.

### 14.3 Authority split and namespaces

Historical source authority and Q01 qualification observations MUST remain
separately namespaced:

```text
historical_oracle
qualification_observation
```

`historical_oracle` supplies accepted predecessor truth, accepted scenario
semantics, expected outcomes/decisions/lifecycles, invariants, and declared
tolerances. `qualification_observation` supplies a new bounded run-local
observation authorized by the pinned Q01 Evidence.

For an authorized scenario, downstream normalization MUST retain one explicit
reference to each authority rather than flattening them into a replacement
run. Equal fields MUST be compared, not coalesced. A mismatch or contradiction
MUST fail closed. Neither authority may be relabeled as the other.

### 14.4 `claim_scope`

Every authorized Q01 operation subject MUST declare:

```text
claim_scope = run_local
```

A `run_local` observation applies only to its own qualification execution,
subject, scenario, correlation identity, configuration, timing/applicability,
and actual outcome. It MUST NOT fill or amend a field in a historical accepted
run.

Every supporting immutable authority entry MUST declare:

```text
claim_scope = immutable_accepted_authority
```

Supporting immutable authority may provide only the claims in its explicit
claim allowlist. It MUST NOT provide request/action/trace identity, timing,
actual outcome, or any other run-local observation. An unknown scope, an
undeclared claim, or use outside the declared scope fails closed.

### 14.5 `predecessor_binding`

Each frozen predecessor MUST first be resolved independently through:

```text
frozen predecessor Acceptance
→ accepted_commit
→ task-declared Evidence blob at accepted_commit
→ recomputed Evidence SHA256
→ expected predecessor result
```

Each Q01 `predecessor_binding` MUST match the resulting task ID, accepted
commit, Evidence path, and recomputed Evidence SHA256 tuple exactly. The bound
scenario MUST exist uniquely in that predecessor Evidence, and its component
and backend identity MUST agree with the subject. A wrong or incomplete tuple,
ambiguous scenario, component/backend disagreement, or unexpected predecessor
result fails closed.

Association by mutable worktree data, array position, timestamp proximity,
backend name alone, or execution order is forbidden.

### 14.6 Physics and timing applicability

Each applicable Q01 physics/timing claim MUST explicitly declare its state.

```text
REQUIRED
```

requires an actual structured observation from the current qualification
execution.

```text
NOT_APPLICABLE
```

is permitted only when the accepted structured execution state proves both
that the simulator did not start and that physics did not start. The
justification and execution state MUST be retained in normalized provenance.

Missing data, expected values, wall time, filesystem/log timestamps,
historical values, or version-wide supporting authority cannot substitute for
a required current qualification observation. Absence alone cannot establish
`NOT_APPLICABLE`. Any substitution or unsupported applicability state fails
closed.

### 14.7 Duplicate-authority prevention

SIM-010 MUST enforce uniqueness for:

- subject ID;
- qualification run identity;
- qualification scenario identity; and
- the fixed subject-to-predecessor scenario mapping.

A historical row relabeled as Q01, a Q01 row relabeled as historical, two Q01
subjects claiming the same authorized mapping, cross-scenario value reuse, or
cross-run value reuse is ambiguous duplicate authority and MUST fail closed.

### 14.8 Deterministic replay authority

Q01 creates no deterministic replay authority. All eleven Q01 operation
subjects MUST be excluded from deterministic replay authority. Historical,
validated L0 deterministic inputs remain the sole source for R6 replay and
must reproduce equivalent decisions and lifecycle outcomes for equivalent
inputs/state.

Q01 retry or reconciliation observations may be checked for semantic
traceability, but they MUST NOT create, replace, or independently satisfy a
deterministic replay result.

### 14.9 Physics semantic regression linkage

R7 physics semantic regression MUST link, without coalescing:

```text
historical accepted oracle
        ↕ comparison
Q01 qualified actual observation
```

The comparison MUST validate scenario and component identity, semantic
outcome, decision/status, required lifecycle, retry/reconciliation semantics,
state invariants, declared tolerances, provenance, and applicability. A
disagreement fails closed.

Gazebo and MuJoCo MUST each have at least one validated applicable physics
observation. An explicit, valid pre-physics `NOT_APPLICABLE` subject remains
traceable but does not count as a physics observation. Physics comparison is
semantic/tolerance-based and MUST NOT require bitwise-identical traces or
create a physical/production performance claim.

### 14.10 Immutable full-repository regression comparison

R11 MUST compare:

```text
immutable current SIM-010 candidate commit
vs
6909c6cceb727598570f6e170ae8d1d293418c9a
```

Both sides MUST run in equivalent clean detached worktrees, with the same
interpreter/environment and the identical declared repository regression
command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
```

A current PASS is `PASS`. A current failure may be classified
`PROVEN_PREEXISTING` only when the complete failed-node set and every non-empty
stable failure signature match the baseline exactly. Equal failure counts,
similar names, or node IDs without matching non-empty signatures are
insufficient. Checkout, execution, parsing, or cleanup failure; an empty
signature; an added or removed node; or a changed signature MUST produce
`POSSIBLY_TASK_RELATED` and block READY.

The resume base `ff48f751489800132099b7c3e8ac2ad7435c9b73` remains the
frozen SIM-010 handoff boundary. It MUST NOT be substituted for the regression
baseline.

### 14.11 Authorized correction boundary

Implementation of this addendum may change only:

```text
tasks/TASK-SIM-010.md
src/simulation_runtime/observability_regression.py
scripts/run_simulation_observability_regression.py
tests/test_simulation_observability_regression.py
```

Only after all pre-Evidence gates pass may it also regenerate:

```text
results/simulation/SIM-010_observability_regression.json
docs/simulation/simulation_observability_regression_v1.md
```

The correction MUST NOT modify accepted Q01 artifacts; SIM-003 through SIM-009
accepted artifacts; predecessor Acceptance or Evidence; accepted commits;
historical task records; orchestrator source; simulator behavior; or physics
implementation. It MUST NOT create a replacement TASK-SIM-010.

### 14.12 Ordered staged gates

The required sequence is:

```text
S10-G0 Q01_ACCEPTANCE_BINDING
S10-G1 SUBJECT_MAPPING
S10-G2 NORMAL_FAILURE_TRACEABILITY
S10-G3 DETERMINISTIC_REPLAY
S10-G4 PHYSICS_SEMANTIC_REGRESSION
S10-G5 FULL_REGRESSION_CLASSIFICATION
S10-G6 CANONICAL_SIM010_EVIDENCE
S10-G7 REPEATABILITY_AND_FINALIZATION
S10-G8 INDEPENDENT_REVIEW
```

A failed gate prevents entry to every later gate. G6 may publish READY Evidence
only after G0 through G5 pass. G7 must prove repeatability from the same
immutable candidate and finalize the canonical artifact. G8 remains an
independent review; implementation completion or Evidence generation does not
imply acceptance.
