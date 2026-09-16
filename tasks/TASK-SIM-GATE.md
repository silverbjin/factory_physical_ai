# TASK-SIM-GATE — Simulation Lane Authorization Gate

> Lane: Simulation  
> Type: Readiness / Authorization Gate  
> Status: BLOCKED until accepted READY evidence exists for SIM-001 and SIM-002  
> Governing ADR: `docs/architecture/adr/ADR-Simulation-Lane-v1.md`  
> Governing Mapping: `context/simulation_task_mapping_v1.md`  
> Physical Authorization: NONE

---

# 1. Purpose

Determine whether downstream tasks in the `TASK-SIM-*` namespace may begin.

This gate evaluates already-existing accepted Simulation Lane evidence.

It shall not implement missing simulation behavior.

It shall not authorize existing Week tasks.

---

# 2. Core State Model

The following dimensions are distinct:

```text
TASK-SIM-GATE implementation
Gate result
Independent acceptance
Simulation-lane authorization
```

They shall be recorded separately.

Example valid state:

```text
TASK-SIM-GATE implementation = complete
Gate result = SIM_NO_GO
Independent acceptance = accepted
Simulation lane authorized = false
```

Another valid state after successful review:

```text
TASK-SIM-GATE implementation = complete
Gate result = SIM_GO
Independent acceptance = accepted
Simulation lane authorized = true
```

---

# 3. Required Context

The gate shall use exactly:

```text
docs/architecture/adr/ADR-Simulation-Lane-v1.md
context/simulation_task_mapping_v1.md
docs/architecture/system_architecture_v1.md
docs/contracts/contract_plan.md
docs/hardware/hardware_target_selection_status_v1.md

results/phase0/P0-004R_vla_readiness.json

docs/simulation/simulation_contract_profile_v1.md
results/simulation/SIM-001_contract_profile.json
results/reviews/SIM-001_acceptance.json

docs/simulation/simulation_smoke_runtime_v1.md
results/simulation/SIM-002_smoke_runtime.json
results/reviews/SIM-002_acceptance.json
```

Additional files may be inspected only as supporting context.

They shall not replace the named authoritative sources.

The authoritative existing Week-task and physical authorization source is:

```text
results/phase0/P0-004R_vla_readiness.json
```

The gate shall not obtain existing W authorization state from:

- prose summaries;
- task histories;
- implementation reports;
- self-reported fields inside SIM evidence.

---

# 4. Required Predecessor State

Before gate evaluation:

## 4.1 TASK-SIM-001

All must be true:

```text
review_decision = ACCEPT

task_specific_decision =
SIM_CONTRACT_PROFILE_READY

canonical evidence SHA =
SIM-001 acceptance.evidence_sha256

canonical profile SHA =
SIM-001 acceptance.profile_sha256

reviewed commit exists

source bindings valid
```

## 4.2 TASK-SIM-002

All must be true:

```text
review_decision = ACCEPT

task_specific_decision =
SIM_SMOKE_READY

canonical evidence SHA =
SIM-002 acceptance.evidence_sha256

canonical smoke report SHA =
SIM-002 acceptance.smoke_report_sha256

reviewed commit exists

SIM-002 remains bound to accepted SIM-001 revision
```

Any missing, ambiguous, rejected, blocked, stale, or mismatched predecessor state shall fail closed.

---

# 5. Acceptance Artifact Trust Rule

The gate shall not trust implementation-generated fields such as:

```text
accepted = true
review_status = accepted
ready_for_gate = true
```

as independent acceptance evidence.

Only:

```text
results/reviews/SIM-001_acceptance.json
results/reviews/SIM-002_acceptance.json
```

or a future explicitly versioned repository-policy equivalent may establish independent acceptance.

A recomputed payload hash is not a substitute for semantic validation or independent acceptance.

---

# 6. Relationship to P0-004R

Existing P0-004R evidence remains historical and authoritative for its evaluated scope.

This gate does not override:

```text
TASK-W1-001
TASK-W1-002
Dataset V1
SmolVLA fine-tuning
physical motion
```

authorization recorded by P0-004R.

`SIM_GO` may coexist with:

```text
P0-004R = NO_GO
```

because they authorize different namespaces and scopes.

---

# 7. Gate Decision

Return exactly one:

```text
SIM_GO
SIM_NO_GO
```

---

# 8. Meaning of SIM_GO

`SIM_GO` means only:

> Downstream tasks in the `TASK-SIM-*` namespace may begin within the simulation-only authorization envelope.

It does not authorize:

- `TASK-W1-*`;
- physical robot work;
- gripper actuation;
- physical teleoperation;
- physical Dataset V1 collection;
- physical camera dependency;
- fine-tuning;
- paid compute;
- hardware selection;
- blanket hardware execution.

---

# 9. No Blanket HW_GO

This gate shall not produce:

```text
HW_GO
```

or any equivalent blanket physical authorization.

Future physical state shall remain represented through separate decisions such as:

```text
device_io_ready
camera_acquisition_authorized
physical_motion_authorized
physical_gripper_authorized
physical_teleop_authorized
demonstration_collection_authorized
fine_tuning_authorized
```

Device readiness is only a prerequisite and never blanket execution authority.

---

# 10. P0-004R Authorization Binding

The gate shall directly read the authoritative values from:

```text
results/phase0/P0-004R_vla_readiness.json
```

At minimum bind and preserve explicit booleans for:

```text
TASK-W1-001
TASK-W1-002
Dataset V1
SmolVLA fine-tuning
physical motion
```

The gate shall record these exact booleans in its output.

It shall not merely state:

```text
unchanged
```

---

# 11. Required Authorization Snapshot

Machine-readable evidence and the human-readable report shall include:

```text
authorization_snapshot:

  simulation_lane_authorized:
    true | false

  task_w1_001_authorized:
    <exact boolean verified from P0-004R>

  task_w1_002_authorized:
    <exact boolean verified from P0-004R>

  dataset_v1_authorized:
    <exact boolean verified from P0-004R>

  fine_tuning_authorized:
    <exact boolean from the applicable authoritative source>

  physical_motion_authorized:
    <exact boolean verified from P0-004R>

  physical_gripper_authorized:
    false unless independently authorized elsewhere

  physical_teleop_authorized:
    false unless independently authorized elsewhere

  physical_dataset_collection_authorized:
    false unless independently authorized elsewhere
```

`SIM_GO` may change only:

```text
simulation_lane_authorized
```

It shall not modify other authoritative values.

If the applicable authoritative training-resource source says fine-tuning is blocked, preserve that result.

---

# 12. Dataset Boundary

Invariant:

```text
SIM_FIXTURE_SET_V1
!=
Dataset V1
```

The gate must verify that no simulation artifact is represented as the existing Dataset V1 deliverable.

---

# 13. Hardware Selection Boundary

The gate shall not assume that:

```text
myCobot 280 Pi
myAGV JN 2023
RealSense D455
Jetson Orin Nano
```

are frozen physical targets.

`hardware_target_selection_status_v1.md` is informational only.

Candidate hardware shall not become a gate prerequisite merely because it is owned or available.

---

# 14. Contract Boundary

The gate must verify that accepted SIM-001/SIM-002 evidence preserves:

```text
Deterministic Mission Executor
Navigation Skill
VLA Skill
Verification
```

ownership/boundaries.

It must reject evidence that introduced new direct actuator ownership without the required separate contract/ADR process.

---

# 15. Mandatory Gate Checks

## C01 — Governing ADR

`ADR-Simulation-Lane-v1` is FROZEN and its hash matches the accepted predecessor bindings.

## C02 — Simulation Mapping

`simulation_task_mapping_v1` is FROZEN and its hash matches accepted bindings.

## C03 — SIM-001 Independent Acceptance

SIM-001 acceptance artifact exists and says:

```text
review_decision = ACCEPT
```

## C04 — SIM-001 READY State

SIM-001 says:

```text
SIM_CONTRACT_PROFILE_READY
```

An accepted BLOCKED result fails this check.

## C05 — SIM-001 Immutable Binding

Canonical profile/evidence hashes match the independent acceptance artifact.

## C06 — SIM-002 Independent Acceptance

SIM-002 acceptance artifact exists and says:

```text
review_decision = ACCEPT
```

## C07 — SIM-002 READY State

SIM-002 says:

```text
SIM_SMOKE_READY
```

An accepted BLOCKED result fails this check.

## C08 — SIM-002 Immutable Binding

Canonical smoke report/evidence hashes match independent acceptance.

## C09 — SIM-002 → SIM-001 Binding

SIM-002 remains bound to the same accepted SIM-001 revision.

## C10 — Bounded Smoke Execution

Accepted smoke evidence proves bounded execution.

## C11 — Physical Independence

The accepted smoke path requires no physical robot.

## C12 — Camera Independence

The accepted smoke path requires no physical camera.

## C13 — No Physical Motion

No physical motion was authorized or executed.

## C14 — No Week Authorization Rewrite

Existing Week authorization values match P0-004R exactly.

## C15 — Dataset Boundary

No simulation fixture is represented as Dataset V1.

## C16 — Training Boundary

No actual fine-tuning is required for the Simulation Lane unless separately authorized.

## C17 — Contract Boundary

Simulation uses only accepted skill/verification boundaries.

## C18 — No Direct Actuator Contract

No incompatible direct actuator ownership has been introduced.

## C19 — Historical P0 Evidence Preserved

P0 evidence referenced by the gate remains unchanged.

## C20 — Decision Reconstruction

The final result is reconstructed from underlying accepted evidence and authorization bindings.

---

# 16. SIM_GO Predicate

Return:

```text
SIM_GO
```

only when all mandatory checks pass.

At minimum:

```text
SIM-001 independent review = ACCEPT
SIM-001 decision = SIM_CONTRACT_PROFILE_READY
SIM-001 immutable bindings valid

SIM-002 independent review = ACCEPT
SIM-002 decision = SIM_SMOKE_READY
SIM-002 immutable bindings valid

SIM-002 binds to accepted SIM-001 revision

physical dependency = false
physical motion executed = false
physical camera dependency = false

W-task authorization mutation = false

Dataset V1 aliasing = false

new direct actuator contract = false

P0-004R authorization snapshot preserved

source/predecessor hashes valid

evidence integrity = PASS
```

---

# 17. SIM_NO_GO Predicate

Return:

```text
SIM_NO_GO
```

if any mandatory check fails.

Examples:

- SIM-001 acceptance missing;
- SIM-001 accepted but `SIM_CONTRACT_PROFILE_BLOCKED`;
- SIM-001 acceptance points to stale evidence;
- SIM-002 acceptance missing;
- SIM-002 accepted but `SIM_SMOKE_BLOCKED`;
- SIM-002 bound to a different SIM-001 revision;
- physical dependency detected;
- Week authorization mutated;
- Dataset V1 alias detected;
- direct actuator contract introduced;
- source hash mismatch.

Do not weaken a failed mandatory condition to obtain SIM_GO.

---

# 18. Non-blockers

The following do not automatically force `SIM_NO_GO`:

```text
P0-006 = DEVICE_IO_BLOCKED
```

provided accepted smoke evidence requires no physical I/O.

Likewise:

```text
P0-007 = TRAINING_RESOURCE_BLOCKED
```

does not block simulation tasks that perform no actual training.

It continues to block tasks that require unresolved training compute.

---

# 19. Required Artifacts

## 19.1 Gate Verifier

```text
scripts/verify_simulation_lane_gate.py
```

## 19.2 Machine-readable Evidence

```text
results/simulation/SIM-GATE_readiness.json
```

## 19.3 Human-readable Report

```text
docs/simulation/simulation_lane_gate_v1.md
```

## 19.4 Task History

Per repository convention.

Independent review history is recorded separately after read-only review.

---

# 20. Required Gate Evidence Schema

The gate evidence shall contain at least:

```text
task_id
implementation_complete
gate_result
generation_timestamp
generation_git_head
worktree_state

required_context_bindings

sim_001:
  evidence_path
  evidence_sha256
  profile_path
  profile_sha256
  acceptance_path
  acceptance_sha256
  review_decision
  task_specific_decision
  reviewed_commit

sim_002:
  evidence_path
  evidence_sha256
  report_path
  report_sha256
  acceptance_path
  acceptance_sha256
  review_decision
  task_specific_decision
  reviewed_commit
  bound_sim_001_acceptance_sha256

p0_004r:
  path
  sha256

authorization_snapshot

material_predicates

unresolved_blockers

payload_sha256
```

Allowed gate results:

```text
SIM_GO
SIM_NO_GO
```

---

# 21. Validator Trust Requirements

The gate validator shall not merely trust:

```text
check.status = PASS
decision = SIM_GO
```

or any self-reported acceptance field.

It must independently reconstruct material predicates from:

- exact Required Context;
- canonical predecessor evidence;
- independent acceptance artifacts;
- immutable hashes;
- P0-004R authorization state.

A recomputed payload hash cannot substitute for semantic correctness.

---

# 22. Required Negative Tests

At minimum test:

```text
SIM-001 ACCEPT + SIM_CONTRACT_PROFILE_BLOCKED

SIM-001 READY without independent acceptance

SIM-001 acceptance pointing to stale evidence

SIM-001 profile hash mismatch

SIM-002 ACCEPT + SIM_SMOKE_BLOCKED

SIM-002 READY without independent acceptance

SIM-002 acceptance pointing to stale evidence

SIM-002 evidence bound to a different SIM-001 revision

self-reported accepted=true without acceptance artifact

P0-004R W1 authorization mutation

missing P0-004R authorization source

Dataset V1 aliasing

physical_motion_authorized flipped true

new direct actuator contract detected

forged SIM_GO with recomputed payload hash
```

Every case must fail closed.

---

# 23. Implementation vs Acceptance vs Authorization

Initial implementation output shall record separately:

```text
TASK-SIM-GATE implementation:
complete | incomplete

Gate result:
SIM_GO | SIM_NO_GO

Independent acceptance:
pending

Simulation lane authorized:
false
```

Important:

During initial implementation:

```text
Independent acceptance = pending
```

Therefore even if the computed gate result is:

```text
SIM_GO
```

the authoritative downstream authorization remains:

```text
simulation_lane_authorized = false
```

until a separate Independent Review returns ACCEPT and a post-review acceptance/authorization recording step binds that review to the exact gate evidence.

---

# 24. Post-review Gate Acceptance

After independent READ-ONLY review, record gate acceptance separately according to repository policy.

Recommended artifact:

```text
results/reviews/SIM-GATE_acceptance.json
```

Minimum fields:

```text
task_id: TASK-SIM-GATE

review_decision:
  ACCEPT
  or
  REJECT

reviewed_commit

gate_evidence_path
gate_evidence_sha256

gate_report_path
gate_report_sha256

review_record_path
review_record_sha256

gate_result:
  SIM_GO
  or
  SIM_NO_GO

recorded_at
recording_commit
```

Only when:

```text
review_decision = ACCEPT
AND
gate_result = SIM_GO
```

with valid hashes may:

```text
simulation_lane_authorized = true
```

be recorded in the authoritative post-review authorization record.

An accepted `SIM_NO_GO` keeps the lane unauthorized.

---

# 25. Independent Review Requirements

A separate READ-ONLY review shall verify:

- Required Context authority;
- SIM-001 acceptance and READY binding;
- SIM-002 acceptance and READY binding;
- SIM-002 → SIM-001 revision binding;
- gate decision reconstruction;
- P0-004R authorization preservation;
- no physical authorization;
- no hardware freeze assumption;
- no Dataset V1 alias;
- no direct actuator contract;
- evidence integrity;
- negative-test adequacy.

The READ-ONLY reviewer shall not create acceptance or history artifacts.

---

# 26. Required Implementation Report

Return:

```markdown
# Implementation Result — TASK-SIM-GATE

## Required Context

## Predecessor Bindings

## P0-004R Authorization Snapshot

## Gate Checks

## Negative / Tampering Validation

## Evidence

## Gate Result

## Independent Acceptance

## Simulation Lane Authorization

## Repository Check

## Final Status
```

Required output:

```text
TASK-SIM-GATE implementation:
complete | incomplete

Gate result:
SIM_GO | SIM_NO_GO

Independent acceptance:
pending

Simulation lane authorized:
false

TASK-W1-001 authorized:
<explicit boolean from P0-004R>

TASK-W1-002 authorized:
<explicit boolean from P0-004R>

Dataset V1 authorized:
<explicit boolean from P0-004R>

Fine-tuning authorized:
<explicit boolean from authoritative training source>

Physical motion authorized:
<explicit boolean from P0-004R>
```

---

# 27. Downstream Effect

Only after:

```text
ACCEPT TASK-SIM-GATE
+
SIM_GO
+
valid post-review acceptance/authorization binding
```

may future:

```text
TASK-SIM-003+
```

begin.

This still does not authorize:

```text
TASK-W1-001
```

or any other existing Week task.

---

# 28. Final Invariants

```text
SIM_GO != W1 authorization

ACCEPT + BLOCKED != downstream authorization

candidate hardware != frozen hardware

device readiness != physical motion authorization

SIM fixture != Dataset V1

payload hash != semantic trust

implementation completion != independent acceptance
```

These invariants are mandatory.
