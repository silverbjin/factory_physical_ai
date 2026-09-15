# TASK-SIM-004 — Navigation Skill ROS 2 Jazzy + Gazebo Harmonic Backend

## 1. Objective

Implement an L1-NAV Simulation backend behind the frozen Navigation Skill contract using ROS 2 Jazzy, Gazebo Harmonic, and Nav2-facing execution.

The completed TASK must prove bounded Navigation Skill success, failure, timeout, abort/unavailable, and reconciliation behavior in a Gazebo-based proxy mobile-robot world without selecting or controlling physical hardware.

---

## 2. Dependencies

- `TASK-SIM-003`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_BASELINE_READY`
  - Verify from:
    - `results/reviews/SIM-003_acceptance.json`
    - `results/simulation/SIM-003_baseline.json`

No physical readiness task is a dependency.

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-003_acceptance.json`
  - Purpose: Verify independent acceptance of the exact Simulation baseline used by this backend.

- `results/simulation/SIM-003_baseline.json`
  - Purpose: Bind the measured ROS 2 Jazzy / Gazebo Harmonic / bridge / Nav2-facing toolchain identities and hashes.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Define the frozen `navigation.execute` and `action_status.get` lifecycle semantics.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Purpose: Validate request/result/status Evidence and prevent simulator-specific contract drift.

### 3.2 Conditional

- `context/simulation_task_mapping_v2.md`
  - Read when: `REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve L1-NAV fidelity or simulator-role intent not fully specified here.

- `docs/architecture/adr/ADR-Simulation-Lane-v1.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve boundary ownership, physical isolation, or Simulation Lane conflicts.

- `results/simulation/SIM-002_smoke_runtime.json`
  - Read when: `REGRESSION_FAILURE | CONTRACT_CONFLICT`
  - Purpose: Compare new Navigation behavior against the accepted deterministic L0 lifecycle baseline.

- `context/current_project_state.md`
  - Read when: `PREREQUISITE_UNCLEAR | SOURCE_CONFLICT`
  - Purpose: Resolve authorization ambiguity without overriding accepted evidence.

---

## 4. Frozen References

- `navigation.execute` and `action_status.get`
  - Public request/result/status fields and lifecycle semantics must not change.

- Timeout / unknown semantics:
  - timeout may yield `pending/unknown`;
  - ambiguous outcome must reconcile through authoritative status lookup;
  - unknown must never be silently converted to success.

- Simulator authority:
  - Gazebo Harmonic is the L1-NAV world authority.
  - ROS 2 Jazzy is the middleware / launch / Nav2-facing integration layer.
  - the robot model is a Simulation proxy, not a frozen myAGV target.

- `SIM_BASELINE_V1`
  - Exact runtime identities and hashes must remain bound.

---

## 5. Scope

This TASK must:

1. implement a Navigation Skill Simulation backend behind the accepted Navigation contract;
2. run with the ROS 2 Jazzy + Gazebo Harmonic toolchain frozen by SIM-003;
3. use a generic/proxy mobile base sufficient to exercise the contract;
4. provide a bounded, reproducible Gazebo world and model/config identity;
5. use a fixed deterministic navigation test environment; custom SLAM research is not required;
6. integrate the Nav2-facing execution path required by the accepted baseline;
7. expose contract-level results for:
   - success;
   - invalid goal;
   - dependency unavailable / lifecycle-not-ready;
   - blocked or aborted execution;
   - bounded timeout;
   - unknown outcome requiring reconciliation;
8. preserve action/idempotency/correlation identity across execution and status lookup;
9. prove bounded startup, execution, timeout handling, and process cleanup;
10. preserve deterministic L0 Navigation contract tests as regression coverage;
11. create machine-readable backend Evidence with versioned world/model/launch/config hashes.

---

## 6. Non-goals

This TASK must not:

- select or claim myAGV as the frozen physical target;
- implement custom SLAM, localization research, or Nav2 algorithm research;
- implement VLA/MuJoCo behavior;
- implement Mission-level E2E;
- create direct actuator APIs above the existing Navigation Skill boundary;
- access or command a physical robot;
- create Dataset V1, fine-tune a model, or perform physical teleoperation;
- modify the accepted Simulation contract/schema.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - Navigation Simulation backend and contract adapter.

- `configs/`
  - Task-owned Gazebo / Nav2 / bridge configuration.

- `data/`
  - Task-owned Gazebo world/model assets when required.

- `scripts/`
  - Bounded launch/run helper when required.

### Tests

- `tests/test_simulation_navigation_backend.py`

### Evidence

- `results/simulation/SIM-004_navigation_backend.json`

---

## 8. Requirements

### R1 — Contract-preserving Navigation backend

The backend must expose only the accepted Navigation Skill semantics to callers. Gazebo, Nav2, ROS topics/actions, and model details remain implementation details below that boundary.

### R2 — Proxy model neutrality

The mobile-base model must be explicitly labeled as a Simulation proxy and must not be represented as the selected myAGV target.

### R3 — Successful navigation

A canonical reachable goal must complete with schema-valid success and verifiable arrival evidence.

### R4 — Invalid goal fail-closed

Malformed or contract-invalid goals must be rejected before simulated execution and must not produce success.

### R5 — Unavailable / not-ready behavior

A missing or not-ready navigation dependency must produce the contract-approved unavailable/failure semantics without hanging or silently falling back.

### R6 — Blocked / aborted behavior

A blocked or explicitly aborted route must produce a non-success terminal result consistent with the accepted contract and Navigation policy.

### R7 — Timeout and unknown reconciliation

A bounded execution timeout must not become success. If the final physical-simulator outcome is not authoritative at timeout, return the accepted pending/unknown form and reconcile through `action_status.get`.

### R8 — Identity preservation

`action_id`, request/correlation identity, result identity, and status lookup must remain stable across execution and reconciliation.

### R9 — Bounded process lifecycle

Gazebo, ROS 2, bridge, and Nav2-facing processes started by tests/runners must have explicit startup, execution, timeout, and cleanup bounds.

### R10 — Asset provenance

Evidence must bind the Gazebo release, ROS 2 distribution, world/model assets, bridge configuration, Nav2-facing configuration, launch/run configuration, and relevant source hashes.

### R11 — L0 regression

Existing deterministic contract and smoke semantics for Navigation must remain green.

### R12 — Task-specific result

Evidence must report exactly:

```text
SIM_NAVIGATION_BACKEND_READY
SIM_NAVIGATION_BACKEND_BLOCKED
```

READY requires all mandatory Navigation scenarios and bounded cleanup to pass.

---

## 9. Failure / Safety Behavior

- Invalid input fails before simulator execution.
- Unavailable dependencies fail closed; no implicit alternate backend is allowed.
- Timeout is bounded and distinct from success.
- Unknown outcome requires status reconciliation before completion or retry.
- Retries, if exercised by existing runtime policy, must remain within the accepted retry budget.
- Process cleanup failure is a task failure.
- No physical device path may be opened or commanded.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_execution_contract.py \
  tests/test_simulation_smoke.py
```

Run the task-owned bounded Navigation/Gazebo runner if one is created.

Expected proof:

- canonical success;
- invalid-goal rejection;
- unavailable/not-ready failure;
- blocked/aborted failure;
- bounded timeout;
- unknown/reconciliation path;
- stable action/status identity;
- clean process shutdown;
- schema-valid Evidence.

### Regression

```text
CONDITIONAL
```

Run full repository regression when:

- code outside `src/simulation_runtime/`, task-owned `configs/`, `data/`, `scripts/`, or focused tests is modified; or
- a shared public contract/schema changes; or
- focused validation reveals behavior outside the Navigation backend has regressed.

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
results/simulation/SIM-004_navigation_backend.json
```

Evidence must prove:

- accepted SIM-003 baseline binding;
- measured ROS 2 Jazzy / Gazebo Harmonic runtime identity;
- proxy world/model/config hashes;
- success/failure/timeout/reconciliation scenario results;
- bounded startup/execution/cleanup;
- stable action/status identities;
- no physical-device dependency;
- L0 regression status;
- task-specific result `SIM_NAVIGATION_BACKEND_READY | SIM_NAVIGATION_BACKEND_BLOCKED`.

---

## 12. Exit Criteria

- EC1. The backend remains behind the frozen Navigation Skill contract and uses the accepted SIM-003 baseline.
- EC2. Required success, invalid, unavailable, blocked/aborted, timeout, and unknown/reconciliation scenarios are proven.
- EC3. ROS 2 / Gazebo / Nav2-facing process lifecycle is bounded and cleanup passes.
- EC4. World/model/bridge/launch/config provenance is complete and the model is explicitly non-physical-target.
- EC5. Focused contract/smoke regression passes and required Evidence is valid.
- EC6. No physical access, custom SLAM/Nav2 research, VLA implementation, or other Non-goal was introduced.
- EC7. Final task result is exactly `SIM_NAVIGATION_BACKEND_READY` or `SIM_NAVIGATION_BACKEND_BLOCKED`.

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

`TASK-SIM-006` may consume this backend only after independent acceptance with `SIM_NAVIGATION_BACKEND_READY`.
