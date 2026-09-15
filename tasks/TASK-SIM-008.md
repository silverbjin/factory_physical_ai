# TASK-SIM-008 — Canonical Normal Gazebo System E2E

## 1. Objective

Execute one canonical normal Factory Physical AI Simulation mission end to end with ROS 2 Jazzy orchestration and Gazebo Harmonic as the single authoritative L2 system world.

The completed TASK must prove a bounded normal mission path through Mission Executor, Navigation Skill, contract-preserving manipulation, Verification, and Mission completion without live MuJoCo world coupling or physical hardware.

---

## 2. Dependencies

- `TASK-SIM-007`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_MISSION_INTEGRATION_READY`
  - Verify from: `results/reviews/SIM-007_acceptance.json`

- `TASK-SIM-005`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_MANIPULATION_BACKEND_READY`
  - Verify from: `results/reviews/SIM-005_acceptance.json`
  - Reason: MuJoCo manipulation-physics Evidence remains a separately required component proof even though MuJoCo is not a live L2 system world.

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-007_acceptance.json`
  - Purpose: Bind the accepted Mission integration/profile runtime.

- `results/reviews/SIM-005_acceptance.json`
  - Purpose: Bind the accepted MuJoCo manipulation-physics component evidence required by the Simulation fidelity model.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Preserve Mission/Skill/Verification lifecycle semantics during system E2E.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Purpose: Validate canonical request/result/status evidence.

### 3.2 Conditional

- `results/simulation/SIM-007_mission_integration.json`
  - Read when: `VALIDATION_FAILURE | EVIDENCE_FAILURE`
  - Purpose: Resolve exact system-profile configuration or predecessor binding mismatch.

- `results/simulation/SIM-003_baseline.json`
  - Read when: `SOURCE_CONFLICT | VALIDATION_FAILURE`
  - Purpose: Resolve toolchain/world authority provenance conflicts.

- `context/project_context.md`
  - Read when: `REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve canonical business-mission intent if the bounded scenario cannot be derived from this TASK.

- `context/simulation_task_mapping_v2.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve L2 system-world authority or MuJoCo separation conflicts.

---

## 4. Frozen References

- Canonical business mission intent:
  - `Supply Brake ECU Type-B to Line B.`

- System authority:
  - Gazebo Harmonic = single authoritative integrated L2 world.
  - MuJoCo = separate accepted component physics evidence, not live L2 world state.

- System profile:
  - Navigation = accepted ROS 2 Jazzy + Gazebo backend.
  - VLA = Gazebo-side contract-preserving manipulation surrogate behind `vla.execute`.
  - Verification = Gazebo system observation adapter through `verification.verify`.

- Mission completion requires authoritative Verification.

- Simulation E2E is not physical E2E.

---

## 5. Scope

This TASK must:

1. define one bounded, versioned canonical normal Simulation scenario representing the parts-supply mission;
2. use the accepted `system` profile from SIM-007;
3. launch ROS 2 Jazzy / Gazebo Harmonic dependencies required by the scenario;
4. execute at least the bounded logical path:
   - mission creation;
   - navigation to the task/source region;
   - contract-preserving simulated manipulation;
   - Verification of the expected state;
   - delivery/navigation to the destination region when required by the task-owned scenario;
   - placement/state transition through the VLA Skill surrogate;
   - final Verification;
   - Mission success;
5. keep the exact world coordinates, object identity, source/destination identities, and initial state in task-owned versioned configuration rather than hard-coded prose;
6. use a Gazebo-side manipulation surrogate behind `vla.execute` to change only Simulation world state required by the canonical scenario;
7. keep accepted MuJoCo manipulation evidence separately bound but not live-coupled;
8. capture Mission/action lifecycle, Navigation/VLA/Verification results, correlation identity, simulation time, bounded duration, and source/config hashes;
9. prove bounded launch/execution/cleanup;
10. produce:
    - `SIM_NORMAL_E2E_READY`; or
    - `SIM_NORMAL_E2E_BLOCKED`.

---

## 6. Non-goals

This TASK must not:

- run live Gazebo↔MuJoCo co-simulation;
- claim Gazebo manipulation fidelity is equivalent to accepted MuJoCo contact physics;
- perform physical robot or camera execution;
- select/freeze myAGV, myCobot, D455, or Orin Nano;
- run failure injection beyond what is required to validate normal-path cleanup;
- implement new retry/recovery policy owned by SIM-009;
- create Dataset V1 or fine-tune SmolVLA;
- modify public Mission/Skill/Verification contracts.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - canonical system-scenario orchestration and Gazebo-side manipulation surrogate.

- `configs/`
  - versioned canonical scenario/profile configuration.

- `data/`
  - Gazebo world/model/object assets required by the canonical scenario.

- `scripts/`
  - bounded system E2E runner.

### Tests

- `tests/test_simulation_normal_system_e2e.py`

### Evidence

- `results/simulation/SIM-008_normal_system_e2e.json`

---

## 8. Requirements

### R1 — Canonical scenario identity

The normal scenario must have a stable scenario ID/version and bind its world, model, object, source/destination, and configuration hashes.

### R2 — Single Gazebo world authority

All L2 integrated world-state claims must originate from the accepted Gazebo system profile. MuJoCo must not participate as a live world.

### R3 — Contract-preserving manipulation surrogate

The Gazebo-side manipulation surrogate must be reachable only behind `vla.execute`, must preserve accepted lifecycle/result semantics, and must not create a new public actuator API.

### R4 — Navigation lifecycle

Navigation actions must preserve accepted action/result/status identity and complete through the accepted SIM-004 backend.

### R5 — Verification-before-completion

Source, manipulation/delivery, and final completion state required by the task-owned scenario must be checked through `verification.verify` before Mission success.

### R6 — Mission lifecycle evidence

Evidence must record initial/final Mission state and relevant intermediate action lifecycle transitions.

### R7 — Correlation provenance

Mission ID, request/action IDs, trace/correlation identity, backend profile, world/config identity, and source Git SHA must be linked.

### R8 — Bounded execution

Startup, canonical execution, timeout handling, and process cleanup must be explicitly bounded.

### R9 — MuJoCo evidence separation

Evidence must record the accepted SIM-005 acceptance/hash as supporting component proof and must explicitly state that it was not the live L2 system world.

### R10 — Normal-path only

The scenario must not silently exercise or depend on failure-injection behavior owned by SIM-009.

### R11 — Task-specific result

Evidence must report exactly:

```text
SIM_NORMAL_E2E_READY
SIM_NORMAL_E2E_BLOCKED
```

---

## 9. Failure / Safety Behavior

- Any unexpected timeout, missing dependency, malformed result, Verification uncertainty, or cleanup failure makes the normal run non-success.
- Mission success must not be inferred from Skill-reported success alone.
- Verification uncertainty is not success.
- Missing system-profile component must fail closed rather than fall back to a different profile.
- No physical API may be opened or commanded.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_mission_integration.py
```

Run the task-owned bounded system E2E runner.

Expected proof:

- canonical scenario starts from the declared initial state;
- Navigation/VLA/Verification contract calls occur in the intended order;
- required world-state transitions are verified;
- Mission reaches success only after final Verification;
- Gazebo remains the only live integrated world;
- MuJoCo acceptance is bound but not co-simulated;
- all processes cleanly terminate.

### Regression

```text
CONDITIONAL
```

Run full repository regression when:

- Mission/runtime or public-contract code outside the Simulation-specific integration area changes; or
- canonical E2E implementation modifies shared Agent/factory-tool code; or
- focused validation exposes non-local regression.

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
results/simulation/SIM-008_normal_system_e2e.json
```

Evidence must prove:

- accepted SIM-007 and SIM-005 bindings;
- canonical scenario/version/world/config identities;
- full Mission/action lifecycle;
- Navigation/VLA/Verification results;
- final Verification-before-success;
- Gazebo-only L2 world authority;
- MuJoCo component-evidence separation;
- bounded duration, simulation time, cleanup, Git/source hashes;
- task-specific result `SIM_NORMAL_E2E_READY | SIM_NORMAL_E2E_BLOCKED`.

---

## 12. Exit Criteria

- EC1. Accepted SIM-007 system profile and SIM-005 manipulation-physics evidence are correctly bound.
- EC2. The canonical normal mission executes end to end in the Gazebo authoritative system world.
- EC3. All required Navigation, manipulation-surrogate, and Verification steps are contract-valid and correlated.
- EC4. Mission success occurs only after authoritative final Verification.
- EC5. MuJoCo remains separate component evidence and no dual-world co-simulation occurs.
- EC6. Execution and cleanup are bounded; required Evidence is reproducible and hash/provenance complete.
- EC7. No failure-campaign, physical execution, hardware freeze, Dataset/training, or other Non-goal was implemented.
- EC8. Final task result is exactly `SIM_NORMAL_E2E_READY` or `SIM_NORMAL_E2E_BLOCKED`.

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

`TASK-SIM-009` may proceed only after independent acceptance with `SIM_NORMAL_E2E_READY`.
