# TASK-SIM-006 — Cross-Simulator Verification Backend

## 1. Objective

Implement simulator-neutral Verification input adapters and Verification execution so that deterministic, Gazebo, and MuJoCo observations can be evaluated through the frozen `verification.verify` contract without simulator-specific hidden-state bypasses.

The completed TASK must preserve `pass | fail | uncertain` verdict semantics and produce executor routing input without independently committing Mission completion.

---

## 2. Dependencies

- `TASK-SIM-004`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_NAVIGATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-004_acceptance.json`

- `TASK-SIM-005`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_MANIPULATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-005_acceptance.json`

Both dependencies are mandatory. An accepted BLOCKED result does not authorize this TASK.

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-004_acceptance.json`
  - Purpose: Bind the accepted Gazebo Navigation backend revision consumed by Verification adapters.

- `results/reviews/SIM-005_acceptance.json`
  - Purpose: Bind the accepted MuJoCo manipulation backend revision consumed by Verification adapters.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Define frozen `verification.verify`, observation identity, verdict, and lifecycle semantics.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Purpose: Validate normalized verification input/output structures.

### 3.2 Conditional

- `results/simulation/SIM-004_navigation_backend.json`
  - Read when: `REQUIREMENT_AMBIGUITY | EVIDENCE_FAILURE`
  - Purpose: Resolve exact Gazebo observation/provenance shape referenced by its acceptance manifest.

- `results/simulation/SIM-005_mujoco_vla_backend.json`
  - Read when: `REQUIREMENT_AMBIGUITY | EVIDENCE_FAILURE`
  - Purpose: Resolve exact MuJoCo observation/provenance shape referenced by its acceptance manifest.

- `context/simulation_task_mapping_v2.md`
  - Read when: `ARCHITECTURE_CONFLICT | REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve cross-simulator authority or Verification-role intent.

- `docs/architecture/adr/ADR-Simulation-Lane-v1.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve ownership conflict between Verification, Mission Executor, and simulator backends.

---

## 4. Frozen References

- `verification.verify`
  - Allowed verdict semantics remain:
    - `pass`
    - `fail`
    - `uncertain`

- Routing interpretation:
  - `pass` -> eligible input for executor confirmation;
  - `uncertain` -> reconciliation, then bounded recovery or HITL if unresolved;
  - `fail` -> deterministic recovery or HITL policy.

- Verification must not commit Mission completion by itself.

- Simulator authority:
  - Gazebo and MuJoCo adapters may expose only normalized evidence required by the contract.
  - Verification must not bypass adapters to query hidden simulator state unavailable through the accepted evidence model.

- `uncertain` must never be auto-promoted to `pass` by confidence metadata.

---

## 5. Scope

This TASK must:

1. implement normalized Verification inputs for:
   - deterministic fixture observations;
   - Gazebo Navigation/system observations available from accepted SIM-004;
   - MuJoCo manipulation observations available from accepted SIM-005;
2. preserve immutable observation identity/version/hash and source provenance;
3. support exact-match, mismatch, insufficient, ambiguous, stale, and malformed observation cases;
4. execute Verification through the accepted `verification.verify` semantics;
5. produce routing input for:
   - `CONFIRMED`;
   - `RECONCILE`;
   - `RECOVERY`;
   - `HITL`;
6. keep routing decisions separate from Verification verdict values;
7. reject simulator-specific hidden-state shortcuts not represented in normalized evidence;
8. prove deterministic verdict behavior for equivalent normalized inputs;
9. produce machine-readable Evidence with:
   - `SIM_VERIFICATION_BACKEND_READY`; or
   - `SIM_VERIFICATION_BACKEND_BLOCKED`.

---

## 6. Non-goals

This TASK must not:

- implement Mission orchestration or Mission completion;
- add new Verification verdict values;
- alter Navigation or MuJoCo physics behavior;
- create Gazebo↔MuJoCo live world synchronization;
- access physical sensors or physical robots;
- implement Dataset V1, model training, or physical validation;
- modify the accepted public Simulation contract/schema.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - Verification normalization/adapters and contract-preserving Verification execution.

### Tests

- `tests/test_simulation_verification_backend.py`

### Evidence

- `results/simulation/SIM-006_verification_backend.json`

---

## 8. Requirements

### R1 — Normalized evidence model

Deterministic, Gazebo, and MuJoCo observations must be converted into one contract-valid Verification input shape with explicit source/provenance identity.

### R2 — Exact match

Equivalent expected and observed state must produce `pass` when all mandatory evidence is present and valid.

### R3 — Mismatch

A material expected/observed mismatch must not produce `pass`.

### R4 — Insufficient / ambiguous evidence

Insufficient or ambiguous mandatory evidence must produce `uncertain` or a frozen contract-valid non-success outcome; it must never become `pass`.

### R5 — Stale evidence

Stale observation identity/version/timestamp outside task-defined validity must not produce `pass`.

### R6 — Malformed evidence

Schema-invalid or contradictory normalized evidence must fail closed.

### R7 — Immutable identity

Verification must preserve and validate observation identity/version/hash and backend provenance.

### R8 — No hidden-state bypass

Verification outcome must be computable from normalized contract evidence. Direct simulator introspection that bypasses the adapter is forbidden.

### R9 — Routing separation

`CONFIRMED | RECONCILE | RECOVERY | HITL` are executor routing inputs, not new Verification verdicts.

### R10 — Uncertain invariant

No confidence metadata, simulator source, or fallback may convert `uncertain` directly into `pass`.

### R11 — Cross-backend determinism

Equivalent normalized inputs from different backends must produce equivalent Verification verdict semantics.

### R12 — Task-specific result

Evidence must report exactly:

```text
SIM_VERIFICATION_BACKEND_READY
SIM_VERIFICATION_BACKEND_BLOCKED
```

---

## 9. Failure / Safety Behavior

- Missing, malformed, stale, or contradictory evidence fails closed.
- `uncertain` must remain non-success until reconciliation or a later executor policy resolves it.
- Verification must not trigger physical activity.
- Backend-specific adapter failure must not silently fall back to another simulator.
- No retry loop may be introduced inside Verification unless already frozen by the accepted contract.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_verification_backend.py \
  tests/test_simulation_execution_contract.py
```

Expected proof:

- exact match;
- mismatch;
- insufficient/ambiguous;
- stale;
- malformed;
- identity/hash validation;
- equivalent cross-backend verdict behavior;
- `uncertain` never auto-promotes to `pass`;
- no hidden-state bypass.

### Regression

```text
CONDITIONAL
```

Run full repository regression when:

- shared Mission/runtime code outside the task-owned Verification implementation changes; or
- a public contract/schema changes; or
- focused tests expose non-local regressions.

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
results/simulation/SIM-006_verification_backend.json
```

Evidence must prove:

- accepted SIM-004 and SIM-005 bindings;
- normalized evidence shape and source provenance;
- required pass/fail/uncertain scenarios;
- identity/hash/staleness handling;
- cross-backend deterministic verdict semantics;
- absence of hidden-state bypass;
- task-specific result `SIM_VERIFICATION_BACKEND_READY | SIM_VERIFICATION_BACKEND_BLOCKED`.

---

## 12. Exit Criteria

- EC1. SIM-004 and SIM-005 accepted READY bindings are valid.
- EC2. Deterministic, Gazebo, and MuJoCo observations are normalized through the frozen Verification contract.
- EC3. Exact-match, mismatch, insufficient/ambiguous, stale, and malformed cases produce the required verdict semantics.
- EC4. `uncertain` never auto-promotes to `pass`, and Verification does not commit Mission completion.
- EC5. Focused validation and required Evidence pass with complete provenance.
- EC6. No hidden simulator-state bypass, dual-world synchronization, physical access, or other Non-goal was introduced.
- EC7. Final task result is exactly `SIM_VERIFICATION_BACKEND_READY` or `SIM_VERIFICATION_BACKEND_BLOCKED`.

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

`TASK-SIM-007` may proceed only after independent acceptance with `SIM_VERIFICATION_BACKEND_READY`.
