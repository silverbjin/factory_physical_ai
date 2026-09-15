# TASK-SIM-005 — VLA Skill MuJoCo Manipulation Backend

## 1. Objective

Implement an L1-VLA manipulation-physics Simulation backend behind the frozen VLA Skill contract using MuJoCo.

The completed TASK must prove contract-preserving manipulation execution and manipulation-specific failure semantics with measured MuJoCo physics, while explicitly avoiding SmolVLA fine-tuning, physical hardware, and any claim that Simulation success proves physical performance.

---

## 2. Dependencies

- `TASK-SIM-003`
  - Required state: `ACCEPTED`
  - Required task-specific result: `SIM_BASELINE_READY`
  - Verify from:
    - `results/reviews/SIM-003_acceptance.json`
    - `results/simulation/SIM-003_baseline.json`

No physical-device, Dataset, or training-resource task is a dependency.

---

## 3. Authoritative Sources

### 3.1 Required

- `results/reviews/SIM-003_acceptance.json`
  - Purpose: Verify the accepted Simulation baseline revision.

- `results/simulation/SIM-003_baseline.json`
  - Purpose: Bind the measured MuJoCo/Python runtime and the frozen simulator-authority policy.

- `docs/contracts/simulation_execution_contract_v1.md`
  - Purpose: Define the frozen `vla.execute` / `action_status.get` lifecycle and reconciliation semantics.

- `docs/contracts/schemas/simulation_execution_contract_v1.schema.json`
  - Purpose: Validate request/result/status structures and prevent MuJoCo-specific contract drift.

### 3.2 Conditional

- `context/simulation_task_mapping_v2.md`
  - Read when: `REQUIREMENT_AMBIGUITY`
  - Purpose: Resolve L1-VLA fidelity or MuJoCo role intent.

- `docs/architecture/adr/ADR-Simulation-Lane-v1.md`
  - Read when: `ARCHITECTURE_CONFLICT`
  - Purpose: Resolve Skill ownership or physical-isolation conflicts.

- `results/simulation/SIM-002_smoke_runtime.json`
  - Read when: `REGRESSION_FAILURE | CONTRACT_CONFLICT`
  - Purpose: Compare MuJoCo behavior against the accepted deterministic VLA lifecycle baseline.

- `context/current_project_state.md`
  - Read when: `PREREQUISITE_UNCLEAR | SOURCE_CONFLICT`
  - Purpose: Resolve current authorization ambiguity without overriding accepted evidence.

---

## 4. Frozen References

- `vla.execute` and `action_status.get`
  - Public fields, action identity, status lifecycle, and reconciliation semantics are frozen.

- Mandatory lifecycle invariants:
  - `UNKNOWN -> SUCCEEDED` directly is forbidden.
  - uncertain result is not success.
  - timeout/unknown requires authoritative reconciliation before completion or retry.

- MuJoCo role:
  - manipulation-physics engineering backend only;
  - not an integrated system world;
  - not a physical-performance claim;
  - not a training authorization.

- Model neutrality:
  - generic/contract-compatible manipulator model is permitted;
  - simulator model must not be labeled as the frozen myCobot target.

- `SIM_BASELINE_V1`
  - exact MuJoCo/runtime identity and authority policy must remain bound.

---

## 5. Scope

This TASK must:

1. implement a MuJoCo-backed VLA Skill Simulation backend behind the accepted contract;
2. use a generic/contract-compatible manipulator and simple task-owned scene sufficient to exercise manipulation physics;
3. use deterministic/scripted action generation or another non-trained task-owned policy that enters only through the accepted VLA Skill boundary;
4. represent observation identity, policy identity, action identity, model/scene identity, and initial-state identity explicitly;
5. execute bounded headless physics;
6. support at least:
   - nominal manipulation objective;
   - grasp miss;
   - object slip/contact loss;
   - joint/workspace limit;
   - invalid/ambiguous observation;
   - bounded timeout;
   - unknown outcome requiring `action_status.get`;
7. preserve deterministic L0 VLA contract tests as regression coverage;
8. record MuJoCo model/scene/config hashes, timestep/step settings, deterministic initialization/seed identity, and relevant source hashes;
9. produce machine-readable Evidence with:
   - `SIM_MANIPULATION_BACKEND_READY`; or
   - `SIM_MANIPULATION_BACKEND_BLOCKED`.

---

## 6. Non-goals

This TASK must not:

- fine-tune, load, or benchmark SmolVLA model weights;
- create Dataset V1 or demonstration data;
- use a physical camera or physical actuator;
- claim the MuJoCo model is the frozen myCobot target;
- integrate MuJoCo as a second live authoritative Gazebo world;
- implement Navigation, Mission E2E, or physical handoff;
- create a new direct actuator contract above `vla.execute`;
- modify the accepted Simulation contract/schema.

---

## 7. Target Areas

### Implementation

- `src/simulation_runtime/`
  - MuJoCo VLA backend and contract adapter.

- `configs/`
  - MuJoCo task/scenario configuration.

- `data/`
  - Task-owned MuJoCo model/scene/assets when required.

- `scripts/`
  - Bounded headless runner when required.

### Tests

- `tests/test_simulation_mujoco_vla_backend.py`

### Evidence

- `results/simulation/SIM-005_mujoco_vla_backend.json`

---

## 8. Requirements

### R1 — Contract-preserving VLA backend

MuJoCo implementation details must remain behind the accepted VLA Skill boundary. Callers must observe only frozen request/result/status semantics.

### R2 — Generic model neutrality

The arm/scene must be explicitly marked as a Simulation proxy and must not be represented as selected physical hardware.

### R3 — Deterministic initialization

Every scenario must use an explicit initial-state identity and deterministic initialization/seed policy sufficient for reproducible evaluation.

### R4 — Nominal manipulation

At least one bounded manipulation objective must produce schema-valid success and evidence of the expected simulated state transition.

### R5 — Grasp miss

A failed grasp must return a non-success result and must not be promoted to success through confidence metadata.

### R6 — Slip / contact loss

Object slip or contact loss after attempted manipulation must be detectable and must produce the expected non-success or uncertain outcome.

### R7 — Joint / workspace limit

A task-owned joint/workspace limit violation must fail closed and must not issue an unbounded or invalid physics command sequence.

### R8 — Invalid / ambiguous observation

Malformed, missing, stale, or ambiguous required observation identity must be rejected or classified according to the accepted contract; it must never silently become success.

### R9 — Timeout / unknown reconciliation

Bounded timeout or unknown execution outcome must preserve `pending/unknown` semantics and use `action_status.get` before completion/retry.

### R10 — Provenance

Evidence must bind MuJoCo version, model/scene/config hashes, timestep/step settings, deterministic initialization identity, source hashes, and the accepted SIM-003 baseline.

### R11 — L0 regression

Existing deterministic VLA lifecycle/contract regression must remain green.

### R12 — Task-specific result

Evidence must report exactly:

```text
SIM_MANIPULATION_BACKEND_READY
SIM_MANIPULATION_BACKEND_BLOCKED
```

---

## 9. Failure / Safety Behavior

- Invalid or ambiguous observations fail closed.
- Joint/workspace limit cases must not generate uncontrolled stepping or unbounded control loops.
- Timeout and unknown outcomes are distinct from success.
- Unknown outcomes require authoritative status reconciliation.
- Cleanup of MuJoCo runtime/resources must be bounded.
- No physical device API may be opened or commanded.
- No training or model-loading fallback may occur if a scripted policy is unavailable; the task must fail rather than expand scope.

---

## 10. Validation

### Focused

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_simulation_mujoco_vla_backend.py \
  tests/test_simulation_execution_contract.py \
  tests/test_simulation_smoke.py
```

Run the task-owned bounded MuJoCo runner if one is created.

Expected proof:

- nominal objective;
- grasp miss;
- slip/contact loss;
- joint/workspace limit;
- invalid/ambiguous observation;
- bounded timeout;
- unknown/status reconciliation;
- deterministic initialization and clean shutdown;
- schema-valid Evidence.

### Regression

```text
CONDITIONAL
```

Run full repository regression when:

- shared code outside the task-owned Simulation runtime/config/assets is modified; or
- a public contract/schema changes; or
- focused validation exposes non-local regressions.

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
results/simulation/SIM-005_mujoco_vla_backend.json
```

Evidence must prove:

- accepted SIM-003 baseline binding;
- MuJoCo version/runtime identity;
- model/scene/config/timestep/initial-state provenance;
- required nominal/failure/timeout/unknown scenario results;
- stable action/status identity;
- no model training, Dataset V1, physical camera, or physical actuator;
- L0 regression status;
- task-specific result `SIM_MANIPULATION_BACKEND_READY | SIM_MANIPULATION_BACKEND_BLOCKED`.

---

## 12. Exit Criteria

- EC1. The MuJoCo backend remains behind the frozen VLA Skill contract and binds the accepted SIM-003 baseline.
- EC2. Nominal, grasp-miss, slip/contact-loss, limit, invalid/ambiguous observation, timeout, and unknown/reconciliation cases are proven.
- EC3. Physics execution and cleanup are bounded and reproducible from recorded initialization/model/config provenance.
- EC4. Existing deterministic contract/smoke regression remains green.
- EC5. Required Evidence is valid and contains no physical/training/Dataset claim.
- EC6. No dual-world co-simulation, physical target freeze, model fine-tuning, or other Non-goal was implemented.
- EC7. Final task result is exactly `SIM_MANIPULATION_BACKEND_READY` or `SIM_MANIPULATION_BACKEND_BLOCKED`.

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

`TASK-SIM-006` may consume this backend only after independent acceptance with `SIM_MANIPULATION_BACKEND_READY`.
