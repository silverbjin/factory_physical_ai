# TASK-SIM-007 — Mission Integration / Backend Profiles

## 1. Objective

Integrate the Mission Executor with the accepted Simulation Navigation, VLA manipulation, and Verification backends through explicit backend profiles while preserving the frozen public contract and one authoritative integrated world.

The completed TASK must provide bounded integration smoke evidence for deterministic, navigation-physics, manipulation-physics, and system profiles without yet claiming canonical normal system E2E completion.

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

- `TASK-SIM-006`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_VERIFICATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-006_acceptance.json`

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-004_acceptance.json`
  - Purpose: Bind the accepted Gazebo Navigation backend revision.

- `results/reviews/SIM-005_acceptance.json`
  - Purpose: Bind the accepted MuJoCo manipulation backend revision.

- `results/reviews/SIM-006_acceptance.json`
  - Purpose: Bind the accepted cross-simulator Verification revision.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Preserve Mission/Skill/Verification operation ownership and lifecycle semantics.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Purpose: Validate profile-independent request/result/status structures.

### 3.2 Conditional

- `results/simulation/SIM-003_baseline.json`
  - Read when: `PREREQUISITE_UNCLEAR | VALIDATION_FAILURE`
  - Purpose: Resolve exact toolchain identities/hashes if runtime profile validation disagrees with predecessor bindings.

- `context/simulation_task_mapping_v2.md`
  - Read when: `REQUIREMENT_AMBIGUITY | ARCHITECTURE_CONFLICT`
  - Purpose: Resolve profile-authority or system-world intent.

- `docs/architecture/system_architecture_v1.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve Mission Executor / Skill ownership conflicts.

- `docs/architecture/adr/ADR-Simulation-Lane-v1.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve Simulation Lane or physical-boundary conflicts.

---

## 4. Frozen References

- Public operations:
  - `mission.execute`
  - `navigation.execute`
  - `vla.execute`
  - `action_status.get`
  - `verification.verify`

- Backend profiles:

```text
deterministic:
  Navigation = deterministic fixture
  VLA = deterministic fixture
  Verification = deterministic/normalized fixture

navigation_physics:
  Navigation = ROS 2 Jazzy + Gazebo Harmonic
  VLA = deterministic fixture/proxy
  Verification = normalized evidence

manipulation_physics:
  Navigation = deterministic fixture
  VLA = MuJoCo
  Verification = normalized evidence

system:
  integrated world = Gazebo Harmonic
  Navigation = ROS 2 Jazzy + Gazebo Harmonic
  VLA = Gazebo-side contract-preserving manipulation surrogate
  Verification = Gazebo system observation adapter
```

- `system` profile must not run MuJoCo as a second live authoritative world.

- Profile selection must never change the public Skill/Verification contract.

---

## 5. Scope

This TASK must:

1. implement explicit configuration/profile selection for the four frozen backend profiles;
2. wire Mission Executor calls through the accepted Navigation, VLA, and Verification boundaries;
3. preserve Mission/action/correlation identity through every backend;
4. use ROS 2 Jazzy for system-facing orchestration required by Navigation/system profiles;
5. ensure `system` profile uses Gazebo Harmonic as the only integrated world authority;
6. implement a Gazebo-side contract-preserving manipulation surrogate for the `system` profile if no accepted existing equivalent exists;
7. keep MuJoCo limited to the `manipulation_physics` component profile;
8. fail closed when a requested profile or required backend is unavailable;
9. prove bounded integration smoke for each profile;
10. preserve authoritative Verification before Mission completion eligibility;
11. create machine-readable Evidence with:
    - `SIM_MISSION_INTEGRATION_READY`; or
    - `SIM_MISSION_INTEGRATION_BLOCKED`.

This TASK prepares integrated runtime profiles; `TASK-SIM-008` owns canonical normal Gazebo E2E qualification.

---

## 6. Non-goals

This TASK must not:

- claim canonical normal system E2E success;
- run a full failure/recovery campaign;
- synchronize live Gazebo and MuJoCo world state;
- change Mission/Skill/Verification public contracts;
- select or freeze physical hardware;
- run Dataset V1, fine-tuning, physical teleoperation, or physical motion;
- replace accepted executor ownership with simulator-specific orchestration logic.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - backend-profile configuration, adapters, and integration runtime.

- `configs/`
  - explicit Simulation backend-profile configuration.

- `scripts/`
  - bounded profile smoke runner when required.

### Tests

- `tests/test_simulation_mission_integration.py`

### Evidence

- `results/simulation/SIM-007_mission_integration.json`

---

## 8. Requirements

### R1 — Explicit profile selection

Profile selection must be explicit and validated. Unknown profiles fail closed; no implicit fallback is allowed.

### R2 — Public-contract invariance

Switching profiles must not change public Mission/Navigation/VLA/Verification request or result schemas.

### R3 — Deterministic profile

The deterministic profile must continue to execute through accepted L0 fixtures and preserve accepted lifecycle semantics.

### R4 — Navigation-physics profile

The Navigation Skill must use the accepted Gazebo backend while VLA remains a contract-preserving fixture/proxy.

### R5 — Manipulation-physics profile

The VLA Skill must use the accepted MuJoCo backend while Navigation remains deterministic.

### R6 — System profile

The integrated world must be Gazebo Harmonic. Navigation must use accepted Gazebo/ROS 2 behavior, and manipulation must use a Gazebo-side contract-preserving surrogate behind `vla.execute`.

### R7 — No dual-world authority

The `system` profile must not start or synchronize MuJoCo as a live world authority.

### R8 — Identity correlation

Mission, request, action, tool/skill, trace/correlation, and Verification identities must be preserved across profile execution.

### R9 — Verification-before-completion

No integrated path may mark Mission success before authoritative Verification produces a success-eligible result.

### R10 — Bounded lifecycle

Profile startup, required simulator/process startup, execution smoke, and cleanup must be bounded.

### R11 — Dependency failure

Unavailable requested backend/profile must produce explicit non-success; the runtime must not silently switch to a different profile.

### R12 — Task-specific result

Evidence must report exactly:

```text
SIM_MISSION_INTEGRATION_READY
SIM_MISSION_INTEGRATION_BLOCKED
```

---

## 9. Failure / Safety Behavior

- Unknown/unsupported profile fails closed.
- Backend startup failure must not trigger fallback to another simulator.
- Unknown action outcome must reconcile through accepted status semantics.
- Verification uncertainty is non-success.
- No profile may open or command physical devices.
- Any detected dual-authority Gazebo↔MuJoCo live-state coupling is a task failure.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_mission_integration.py \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_mujoco_vla_backend.py \
  tests/test_simulation_verification_backend.py
```

Expected proof:

- all four profiles validate;
- public schemas remain identical across profiles;
- system profile has Gazebo-only integrated world authority;
- Mission/action/trace identities remain correlated;
- Verification gates completion;
- unavailable/invalid profile fails closed;
- cleanup is bounded.

### Regression

```text
CONDITIONAL
```

Run full repository regression when:

- core `src/mission_runtime/`, `src/contracts/`, factory-agent/tool code, or public schemas change; or
- profile integration requires modifying code outside `src/simulation_runtime/` and task-owned config/scripts; or
- focused validation reveals non-local regression.

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
results/simulation/SIM-007_mission_integration.json
```

Evidence must prove:

- accepted SIM-004/005/006 bindings;
- exact backend-profile definitions;
- bounded profile-smoke results;
- stable correlation identities;
- Verification-before-completion;
- Gazebo-only integrated system-world authority;
- no live dual-world co-simulation;
- task-specific result `SIM_MISSION_INTEGRATION_READY | SIM_MISSION_INTEGRATION_BLOCKED`.

---

## 12. Exit Criteria

- EC1. Accepted SIM-004/005/006 revisions are bound and all four backend profiles are explicitly defined.
- EC2. Deterministic, navigation-physics, manipulation-physics, and system profile smoke validation passes or truthfully blocks.
- EC3. Public contract semantics and correlation identities remain invariant across profiles.
- EC4. System profile uses Gazebo as the single integrated world and does not run live MuJoCo co-simulation.
- EC5. Verification remains mandatory before Mission success eligibility.
- EC6. Required Evidence is valid, cleanup is bounded, and no physical activity occurs.
- EC7. Final task result is exactly `SIM_MISSION_INTEGRATION_READY` or `SIM_MISSION_INTEGRATION_BLOCKED`.

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

`TASK-SIM-008` may proceed only after independent acceptance with `SIM_MISSION_INTEGRATION_READY`.
