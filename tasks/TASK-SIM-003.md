# TASK-SIM-003 — Simulation Toolchain Strategy & Baseline Freeze

## 1. Objective

Create a reproducible `SIM_BASELINE_V1` that binds the accepted Simulation Lane foundation to measured ROS 2 Jazzy, Gazebo Harmonic, `ros_gz` / Nav2-facing, and MuJoCo runtime facts.

The completed TASK must freeze:

- exact accepted predecessor identities and hashes;
- measured simulation toolchain identities and runnable entry points;
- the Simulation fidelity policy;
- simulator authority and ownership rules;
- a bounded toolchain smoke baseline for downstream `TASK-SIM-004` and `TASK-SIM-005`.

This TASK freezes a Simulation development baseline only. It does not implement Navigation, VLA manipulation physics, Mission E2E, or physical behavior.

---

## 2. Dependencies

- `TASK-SIM-GATE`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_GO`
  - Required authorization: `simulation_lane_authorized = true`
  - Verify from:
    - `results/reviews/SIM-GATE_acceptance.json`
    - `results/simulation/SIM-GATE_readiness.json`

- `TASK-SIM-C01`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_CONTRACT_GAPS_RESOLVED`
  - Verify from: `results/reviews/SIM-C01_acceptance.json`

- `TASK-SIM-001`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_CONTRACT_PROFILE_READY`
  - Verify from: `results/reviews/SIM-001_acceptance.json`

- `TASK-SIM-002`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_SMOKE_READY`
  - Verify from: `results/reviews/SIM-002_acceptance.json`

Any missing, rejected, ambiguous, stale, or hash-inconsistent dependency must fail closed as `SIM_BASELINE_BLOCKED`.

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-GATE_acceptance.json`
  - Purpose: Verify independent acceptance of the gate and bind the exact reviewed gate evidence.

- `results/simulation/SIM-GATE_readiness.json`
  - Purpose: Verify `SIM_GO`, `simulation_lane_authorized = true`, and preserved physical / Week authorization values.

- `results/reviews/SIM-C01_acceptance.json`
  - Purpose: Bind the accepted executable-contract remediation revision.

- `results/reviews/SIM-001_acceptance.json`
  - Purpose: Bind the accepted contract-profile revision.

- `results/reviews/SIM-002_acceptance.json`
  - Purpose: Bind the accepted deterministic smoke revision.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Preserve the accepted Simulation Skill / Verification operations and lifecycle semantics while freezing the toolchain.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Purpose: Preserve the executable machine-readable contract schema used by downstream Simulation tasks.

### 3.2 Conditional

- `context/current_project_state.md`
  - Read when: `PREREQUISITE_UNCLEAR | SOURCE_CONFLICT`
  - Purpose: Resolve current authorization or accepted-state ambiguity without treating planning state as stronger than machine-readable evidence.

- `context/simulation_task_mapping_v2.md`
  - Read when: `REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve intended simulator-role or fidelity-policy wording not fully determined by this TASK.

- `docs/architecture/adr/ADR-Simulation-Lane-v1.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve conflicts about Simulation Lane ownership, physical isolation, or Week-task separation.

- `docs/simulation/simulation_contract_profile_v1.md`
  - Read when: `CONTRACT_CONFLICT`
  - Purpose: Resolve a conflict between implementation assumptions and the accepted contract-profile interpretation.

---

## 4. Frozen References

- `docs/contracts/simulation_execution_contract_v1.md`
  - Frozen operations include `mission.execute`, `navigation.execute`, `vla.execute`, `action_status.get`, and `verification.verify`.
  - This TASK must not change their public semantics.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Existing schema fields, enums, status semantics, and validation behavior are frozen.

- Simulation authority policy:
  - `ROS 2 Jazzy` = system middleware / launch / Skill integration / Nav2-facing execution.
  - `Gazebo Harmonic` = authoritative integrated Simulation world.
  - `MuJoCo` = manipulation-physics engineering backend.
  - deterministic fixtures = L0 contract / lifecycle regression baseline.
  - `dual_world_cosimulation = prohibited_v1`.

- Fidelity identifiers:
  - `L0`
  - `L1-NAV`
  - `L1-VLA`
  - `L1-VERIFY`
  - `L2-SYSTEM`

- Authorization invariants:
  - `SIM_GO != W1 authorization`
  - simulation evidence is not physical evidence.
  - simulator models do not freeze myAGV, myCobot, D455, Orin Nano, or any other physical target.

---

## 5. Scope

This TASK must:

1. verify all mandatory predecessor acceptances and their canonical hash bindings;
2. measure the current repository Git revision and worktree state used for baseline generation;
3. measure the ROS 2 distribution/runtime identity and require `jazzy`;
4. measure the Gazebo runtime identity and require the Harmonic release line;
5. verify the bounded availability of the ROS/Gazebo integration needed by downstream work, including `ros_gz` or the repository-selected equivalent;
6. identify the Nav2-facing packages / executable entry points required by `TASK-SIM-004` without implementing Navigation behavior;
7. measure the MuJoCo package/runtime identity;
8. prove a bounded headless MuJoCo import, model load, and physics step suitable for `TASK-SIM-005`;
9. prove a bounded headless Gazebo startup / shutdown smoke suitable for downstream work without implementing a Navigation mission;
10. rerun the accepted deterministic contract/smoke baseline without altering its accepted evidence;
11. hash the contract, schema, relevant runner/source files, and measured simulator configuration inputs;
12. create `SIM_BASELINE_V1` with exact provenance and a task-specific result:
    - `SIM_BASELINE_READY`; or
    - `SIM_BASELINE_BLOCKED`.

Missing or incompatible toolchain facts must produce `SIM_BASELINE_BLOCKED`; this TASK must not install or upgrade dependencies to force readiness.

---

## 6. Non-goals

This TASK must not:

- implement `TASK-SIM-004` Gazebo Navigation behavior;
- implement `TASK-SIM-005` MuJoCo manipulation behavior;
- implement Mission integration or system E2E;
- install, upgrade, or repair ROS 2, Gazebo, Nav2, `ros_gz`, MuJoCo, CUDA, or other runtime dependencies;
- modify accepted SIM evidence or acceptance manifests;
- create real-time Gazebo↔MuJoCo co-simulation;
- select or freeze physical hardware;
- perform Dataset V1 collection, SmolVLA fine-tuning, teleoperation, or physical motion.

---

## 7. Target Areas

### Implementation

- `scripts/`
  - Create a bounded Simulation toolchain / baseline verifier if no repository-equivalent verifier already exists.

- `docs/simulation/`
  - Create the human-readable `SIM_BASELINE_V1` report.

- `results/simulation/`
  - Create the canonical machine-readable baseline evidence.

### Tests

- `tests/test_simulation_toolchain_baseline.py`
  - Create focused verifier / evidence-integrity tests.

### Evidence

- `results/simulation/SIM-003_baseline.json`

---

## 8. Requirements

### R1 — Accepted predecessor binding

The baseline must verify exact acceptance/evidence bindings for SIM-C01, SIM-001, SIM-002, and SIM-GATE before evaluating any toolchain fact.

### R2 — ROS 2 Jazzy identity

The baseline must record the measured ROS 2 distribution/runtime identity and must fail readiness if the active runtime is not Jazzy.

### R3 — Gazebo Harmonic identity

The baseline must record the measured Gazebo runtime identity and must fail readiness if the required Harmonic runtime cannot be verified.

### R4 — ROS/Gazebo and Nav2-facing availability

The baseline must identify and record the exact `ros_gz` / bridge and Nav2-facing package or executable identities required by downstream Navigation work. Availability checks must be bounded and non-mutating.

### R5 — MuJoCo identity and headless step

The baseline must record the measured MuJoCo version and prove a bounded headless import, minimal model load, and at least one physics step.

### R6 — Gazebo bounded smoke

The baseline must prove bounded headless Gazebo startup and cleanup without executing a Navigation Skill mission.

### R7 — Fidelity and authority freeze

The evidence must encode exactly:

```yaml
ros2_distro: jazzy
gazebo_release: harmonic
system_simulator: gazebo_harmonic
navigation_backend: ros2_jazzy_gazebo_harmonic
manipulation_physics_backend: mujoco
integrated_world_authority: gazebo_harmonic
dual_world_cosimulation: prohibited_v1
```

`mujoco_version` must be measured, never guessed.

### R8 — Deterministic baseline preservation

The accepted Simulation contract and deterministic smoke tests must remain valid. This TASK must not regenerate or rewrite their accepted evidence.

### R9 — Baseline provenance

The baseline must record Git SHA, worktree cleanliness, relevant source/config hashes, exact validation commands, simulator/runtime identities, and timestamps.

### R10 — Downstream eligibility

Only `ACCEPTED + SIM_BASELINE_READY` may make `TASK-SIM-004` and `TASK-SIM-005` eligible for implementation. `ACCEPTED + SIM_BASELINE_BLOCKED` remains non-authorizing.

---

## 9. Failure / Safety Behavior

- Any missing mandatory acceptance artifact, hash mismatch, runtime identity ambiguity, unsupported release, unbounded subprocess, or cleanup failure must fail closed.
- Toolchain probes must use explicit time bounds.
- No probe may execute physical hardware access or physical motion.
- No probe may install or mutate system dependencies.
- `SIM_BASELINE_BLOCKED` is a valid truthful task result and must not be converted to READY by disabling mandatory checks.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_toolchain_baseline.py \
  tests/test_simulation_execution_contract.py \
  tests/test_simulation_smoke.py
```

Run the task-owned baseline verifier using its repository path after implementation.

Expected proof:

- accepted predecessor bindings validate;
- ROS 2 Jazzy is measured;
- Gazebo Harmonic is measured and bounded smoke exits cleanly;
- required ROS/Gazebo / Nav2-facing identities are recorded;
- MuJoCo headless step succeeds;
- baseline JSON validates its own internal bindings;
- existing contract/smoke regression remains green.

### Regression

```text
CONDITIONAL
```

Run when:

- implementation modifies shared runtime code under `src/`; or
- implementation changes any accepted contract/schema; or
- focused validation exposes a regression outside the new baseline verifier.

### Additional checks

```bash
git diff --check
git status --short
```

No accepted predecessor evidence may be modified.

---

## 11. Evidence

```text
Evidence required: YES
```

Path:

```text
results/simulation/SIM-003_baseline.json
```

Evidence must prove:

- dependency acceptance and hash bindings;
- exact Git/source/config provenance;
- measured ROS 2 Jazzy identity;
- measured Gazebo Harmonic identity;
- `ros_gz` / Nav2-facing availability needed by downstream work;
- measured MuJoCo identity and bounded headless physics step;
- bounded Gazebo startup/cleanup;
- frozen fidelity/authority policy;
- deterministic contract/smoke regression status;
- task-specific result `SIM_BASELINE_READY | SIM_BASELINE_BLOCKED`.

Human-readable companion:

```text
docs/simulation/simulation_baseline_v1.md
```

---

## 12. Exit Criteria

- EC1. All required predecessor acceptances and canonical hash bindings are valid.
- EC2. ROS 2 Jazzy, Gazebo Harmonic, ROS/Gazebo integration, Nav2-facing prerequisites, and MuJoCo identities are measured and recorded without dependency mutation.
- EC3. Bounded Gazebo and MuJoCo toolchain smoke validation completes with bounded cleanup.
- EC4. `SIM_BASELINE_V1` records the frozen L0/L1/L2 fidelity and simulator-authority policy, including `dual_world_cosimulation = prohibited_v1`.
- EC5. Required evidence and human-readable report are internally consistent and hash/provenance complete.
- EC6. Existing Simulation contract/smoke regression remains green and accepted evidence is unchanged.
- EC7. No Non-goal has been implemented.
- EC8. The final task-specific result is exactly `SIM_BASELINE_READY` or `SIM_BASELINE_BLOCKED`, and downstream eligibility reflects that result.

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

Only post-review `ACCEPT + SIM_BASELINE_READY` authorizes `TASK-SIM-004` and `TASK-SIM-005` to proceed to implementation.
