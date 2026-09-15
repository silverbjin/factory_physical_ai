# TASK-SIM-009 — Multi-layer Failure / Recovery Scenario Suite

## 1. Objective

Implement and execute a bounded Simulation failure/recovery suite spanning deterministic contract faults, Gazebo Navigation/system faults, MuJoCo manipulation faults, and Verification mismatches.

The completed TASK must prove the intended retry, reconciliation, recovery, HITL, or fail-closed behavior without inventing new recovery policy or exercising physical hardware.

---

## 2. Dependencies

- `TASK-SIM-008`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_NORMAL_E2E_READY`
  - Verify from: `results/reviews/SIM-008_acceptance.json`

- `TASK-SIM-004`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_NAVIGATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-004_acceptance.json`

- `TASK-SIM-005`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_MANIPULATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-005_acceptance.json`

- `TASK-SIM-006`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_VERIFICATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-006_acceptance.json`

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-008_acceptance.json`
  - Purpose: Bind the accepted canonical normal E2E baseline.

- `results/reviews/SIM-004_acceptance.json`
  - Purpose: Bind the accepted Gazebo Navigation failure-capable backend.

- `results/reviews/SIM-005_acceptance.json`
  - Purpose: Bind the accepted MuJoCo manipulation failure-capable backend.

- `results/reviews/SIM-006_acceptance.json`
  - Purpose: Bind the accepted Verification semantics used by mismatch/uncertainty scenarios.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Preserve retry/timeout/unknown/status/Verification lifecycle semantics.

### 3.2 Conditional

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Read when: `CONTRACT_CONFLICT | VALIDATION_FAILURE`
  - Purpose: Resolve schema-level malformed/contradictory response behavior.

- `context/project_context.md`
  - Read when: `REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve intended representative business failure semantics.

- `results/simulation/SIM-008_normal_system_e2e.json`
  - Read when: `VALIDATION_FAILURE | EVIDENCE_FAILURE`
  - Purpose: Compare failure runs to the accepted normal E2E baseline.

- `context/simulation_task_mapping_v2.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve fault-layer ownership or simulator-authority conflict.

---

## 4. Frozen References

- Existing timeout/retry/reconciliation/idempotency semantics are owned by accepted runtime/contracts.
- Unknown outcome must not become success without reconciliation.
- Verification `uncertain` is non-success.
- Gazebo = integrated Navigation/system fault world.
- MuJoCo = manipulation-physics fault bench.
- No failure scenario may create live Gazebo↔MuJoCo dual-world authority.
- Failure injection must not create new public contract states or failure enums without separate contract change.

---

## 5. Scope

This TASK must:

1. create a versioned failure-scenario manifest with stable scenario IDs, layer, injection method, expected outcome, and bounded execution budget;
2. exercise the minimum required classes:

   **L0 contract/dependency**
   - malformed response;
   - dependency timeout/unavailable;
   - unknown or contradictory result/status;

   **L1-NAV Gazebo**
   - blocked path / obstacle;
   - navigation abort or timeout;
   - sensor / TF / dependency unavailable when supported by the accepted backend;

   **L1-VLA MuJoCo**
   - grasp miss;
   - slip/contact loss;
   - joint/workspace limit;
   - timeout;
   - ambiguous observation;
   - unknown outcome;

   **L2 Mission / Verification**
   - Skill-reported success but observed state mismatch;
   - stale observation;
   - uncertain Verification leading to reconciliation and bounded recovery/HITL;

3. prove, per scenario, the expected:
   - retry;
   - reconcile;
   - recover;
   - HITL;
   - fail-closed decision;
4. preserve Mission/action/idempotency identity across retry/reconciliation paths;
5. enforce bounded retries, execution time, and cleanup;
6. reuse existing recovery ownership/policy rather than inventing new production policy;
7. create machine-readable Evidence with:
   - `SIM_FAILURE_SUITE_READY`; or
   - `SIM_FAILURE_SUITE_BLOCKED`.

---

## 6. Non-goals

This TASK must not:

- redesign retry/recovery/HITL policy;
- add new public contract states merely to make a scenario pass;
- implement new business workflows unrelated to the canonical mission;
- run physical fault injection;
- run long-duration Chaos/Soak validation;
- create real-time Gazebo↔MuJoCo world synchronization;
- fine-tune a VLA or create Dataset V1;
- claim Simulation failure rates as physical/production reliability metrics.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - task-owned fault-injection adapters/scenario execution where required.

- `configs/`
  - versioned failure-scenario manifest/configuration.

- `scripts/`
  - bounded failure-suite runner when required.

### Tests

- `tests/test_simulation_failure_recovery.py`

### Evidence

- `results/simulation/SIM-009_failure_recovery.json`

---

## 8. Requirements

### R1 — Versioned scenario manifest

Every fault must have stable ID, layer, backend/profile, injection description, expected non-success/recovery outcome, and execution budget.

### R2 — Contract/dependency faults

Malformed, unavailable, timed-out, unknown, or contradictory dependency results must fail closed according to accepted contract semantics.

### R3 — Gazebo Navigation faults

Blocked/aborted/timeout and task-supported sensor/TF dependency faults must produce the expected bounded Navigation and Mission behavior.

### R4 — MuJoCo manipulation faults

Grasp miss, slip/contact loss, joint/workspace limit, timeout, ambiguous observation, and unknown outcomes must preserve accepted VLA lifecycle and reconciliation semantics.

### R5 — Verification mismatch

Skill success must not commit Mission success when normalized observed state fails or remains uncertain.

### R6 — Retry budget

Every retryable scenario must remain within the accepted retry budget. No scenario may use unbounded retries or sleeps.

### R7 — Reconciliation identity

Unknown/pending paths must preserve action identity and reconcile through authoritative status lookup.

### R8 — Idempotency

Retry/recovery must not duplicate a completed side effect within the Simulation scenario.

### R9 — HITL reachability

Scenarios whose accepted policy requires HITL must prove a reachable escalation state rather than silently failing or auto-succeeding.

### R10 — Bounded cleanup

Each scenario must terminate all task-started simulator/process resources within its cleanup bound.

### R11 — No policy invention

If a required expected outcome cannot be derived from accepted runtime/contract behavior, mark the scenario BLOCKED rather than inventing policy.

### R12 — Task-specific result

Evidence must report exactly:

```text
SIM_FAILURE_SUITE_READY
SIM_FAILURE_SUITE_BLOCKED
```

---

## 9. Failure / Safety Behavior

- Fault injection itself must be deterministic or explicitly seeded/configured.
- No injected failure may access physical devices.
- No scenario may convert timeout, unknown, uncertain, or contradictory state to success without accepted reconciliation/verification.
- Cleanup failure, retry-budget overrun, or leaked process fails the scenario.
- A scenario with ambiguous expected policy must be BLOCKED, not guessed.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_failure_recovery.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_mujoco_vla_backend.py \
  tests/test_simulation_verification_backend.py
```

Run the task-owned bounded failure-suite runner.

Expected proof:

- every mandatory scenario ID executes or truthfully reports a prerequisite limitation;
- expected retry/reconcile/recover/HITL/fail-closed decision is recorded;
- retry budgets and idempotency hold;
- unknown/uncertain never silently succeeds;
- simulator/process cleanup is bounded.

### Regression

```text
CONDITIONAL
```

Run full repository regression when:

- recovery/runtime policy code outside task-owned Simulation adapters is modified; or
- public contract/schema changes; or
- focused suite reveals non-local regressions.

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
results/simulation/SIM-009_failure_recovery.json
```

Evidence must prove:

- accepted predecessor bindings;
- versioned scenario manifest/hash;
- per-scenario layer/backend/injection/expected result;
- actual result and recovery decision;
- retry/reconciliation/idempotency/HITL facts where applicable;
- bounded duration/cleanup;
- no physical dependency or dual-world authority;
- task-specific result `SIM_FAILURE_SUITE_READY | SIM_FAILURE_SUITE_BLOCKED`.

---

## 12. Exit Criteria

- EC1. The mandatory L0, Gazebo, MuJoCo, and Mission/Verification fault classes have versioned scenarios.
- EC2. Each scenario proves its expected retry/reconcile/recover/HITL/fail-closed behavior or truthfully blocks on an unresolved accepted-policy gap.
- EC3. Retry budget, reconciliation identity, idempotency, and Verification-before-success invariants hold.
- EC4. All scenario execution and cleanup are bounded; no process leaks remain.
- EC5. Required Evidence is reproducible and binds accepted normal/backend revisions.
- EC6. No new recovery policy, physical fault injection, dual-world co-simulation, or other Non-goal was introduced.
- EC7. Final task result is exactly `SIM_FAILURE_SUITE_READY` or `SIM_FAILURE_SUITE_BLOCKED`.

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

`TASK-SIM-010` may proceed only after independent acceptance with `SIM_FAILURE_SUITE_READY`.
