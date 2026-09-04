# TASK-P0-007 — VLA Training Compute / Storage / Budget Readiness

> Phase: Phase 0 — Readiness Blocker Resolution
> Type: Implementation Task Specification / Resource Readiness Verification
> Status: READY_FOR_IMPLEMENTATION
> Predecessors:
>
> * `TASK-P0-005` — ACCEPTED
> * `TASK-P0-006` — ACCEPTED, task-specific outcome `DEVICE_IO_BLOCKED`
>   Downstream Gate: `TASK-P0-004R`
>   Week 1 Authorization: NOT GRANTED BY THIS TASK

---

# 1. Purpose

Establish a truthful, reproducible, and budget-aware compute strategy for future SmolVLA training/fine-tuning work without performing the actual training.

This task shall determine whether the project has at least one credible compute/storage/budget path for later VLA experimentation and fine-tuning.

The task answers:

> "When an authorized downstream task needs to run SmolVLA training or fine-tuning, do we already know where it will run, what resources it requires, what cost constraints apply, and what fallback path will be used if the primary path is insufficient?"

This task does **not** answer:

> "Has SmolVLA already been successfully fine-tuned?"

---

# 2. Background

`TASK-P0-005` established and independently accepted the local VLA software runtime.

Accepted runtime facts include:

```text
Python       3.12.3
LeRobot      0.4.4
PyTorch      2.10.0+cu130
torchvision  0.25.0+cu130
GPU          RTX 2060 Max-Q
VRAM         6144 MiB
CUDA runtime READY
```

However, the accepted P0-005 evidence explicitly classified:

```text
SmolVLA training fit in 6 GB:
NOT_VERIFIED
```

`TASK-P0-006` subsequently established a trustworthy physical-I/O readiness verifier, but the current physical environment remains:

```text
DEVICE_IO_BLOCKED
```

The P0-006 physical blockers remain open and are not resolved by P0-007.

P0-007 addresses only the separate training-resource readiness dimension.

---

# 3. Core Principles

This task shall obey the following principles.

## 3.1 Readiness, Not Training

The task may inspect, measure, classify, and plan compute resources.

It shall not perform actual model fine-tuning.

---

## 3.2 No Unsupported VRAM Claims

The existence of:

```text
6144 MiB VRAM
```

must not by itself be interpreted as proof that SmolVLA training fits in 6 GB.

Synthetic CUDA allocation success must not by itself be interpreted as proof of model-training feasibility.

If model-specific training fit is not directly proven by evidence authorized by this task, retain:

```text
NOT_VERIFIED
```

---

## 3.3 Fail Closed

Missing mandatory resource, budget, or provenance information must not silently become READY.

---

## 3.4 No Forced READY Result

A truthful:

```text
TRAINING_RESOURCE_BLOCKED
```

is a valid task outcome.

The purpose is accurate readiness assessment, not obtaining a preferred result.

---

# 4. Primary Decision

The task shall produce exactly one top-level decision:

```text
TRAINING_RESOURCE_READY
```

or:

```text
TRAINING_RESOURCE_BLOCKED
```

---

## 4.1 Meaning of TRAINING_RESOURCE_READY

`TRAINING_RESOURCE_READY` means:

> At least one future training execution path has been selected and sufficiently evidenced with compatible compute, storage, environment, budget policy, and fallback assumptions to support the final Phase 0 readiness evaluation.

It does **not** mean:

* SmolVLA training has been executed;
* the model has been fine-tuned;
* a particular quality metric has been achieved;
* the local RTX 2060 6 GB has been proven sufficient for training unless direct evidence establishes that fact;
* Dataset V1 exists;
* physical robot readiness exists;
* Week 1 has been authorized.

---

## 4.2 Meaning of TRAINING_RESOURCE_BLOCKED

`TRAINING_RESOURCE_BLOCKED` means that no sufficiently evidenced training path currently satisfies the required resource and budget conditions.

This is an acceptable implementation result if supported by evidence.

---

# 5. Candidate Training Execution Modes

The task shall classify the intended future execution mode as exactly one of:

```text
LOCAL_TRAINING
REMOTE_TRAINING
HYBRID_TRAINING
UNRESOLVED
```

Definitions:

### LOCAL_TRAINING

The accepted local environment is intended to execute future training/fine-tuning.

This mode may be selected only when local training feasibility is supported by sufficient model-specific evidence.

Do not infer LOCAL_TRAINING readiness from CUDA availability alone.

---

### REMOTE_TRAINING

A remote GPU/compute environment is intended to execute training.

The local environment may still be used for:

* code development;
* dataset preparation;
* configuration;
* validation;
* artifact inspection.

Remote resource availability and budget assumptions must be evidenced.

---

### HYBRID_TRAINING

Local resources are used for bounded development/testing while training executes on a separate higher-resource compute environment.

The split of responsibilities must be explicitly documented.

---

### UNRESOLVED

No sufficiently supported training execution mode has been selected.

`UNRESOLVED` shall result in:

```text
TRAINING_RESOURCE_BLOCKED
```

---

# 6. Preconditions

Before implementation:

1. `TASK-P0-005` must remain accepted.
2. Accepted P0-005 evidence must remain unchanged.
3. `TASK-P0-006` implementation/evidence must be accepted.
4. P0-006's `DEVICE_IO_BLOCKED` result does not prevent P0-007 from executing.
5. P0-006 physical blockers remain unresolved unless separately changed by an authorized task.
6. `TASK-W1-001` remains unauthorized.
7. `TASK-P0-004R` has not yet authorized downstream work.
8. No model fine-tuning may begin as part of this task.

---

# 7. Scope

## 7.1 Local Compute Measurement

Measure and record the local compute environment relevant to future VLA work.

At minimum include:

* GPU identity;
* GPU VRAM;
* CUDA availability;
* PyTorch CUDA compatibility;
* host RAM;
* relevant filesystem capacity;
* relevant free disk capacity;
* current VLA environment location;
* environment/package footprint where practical;
* intended Hugging Face/model cache location where defined.

Reuse accepted P0-005 facts where appropriate, but independently distinguish:

```text
prior accepted evidence
```

from:

```text
newly measured P0-007 evidence
```

---

## 7.2 Local Training Role Classification

Explicitly classify the local RTX 2060 Max-Q environment as one of:

```text
TRAINING_VERIFIED
TRAINING_NOT_VERIFIED
TRAINING_UNSUITABLE
```

Do not classify:

```text
TRAINING_VERIFIED
```

unless model-specific evidence authorized by this task justifies the claim.

If actual SmolVLA training is required to establish the claim, retain:

```text
TRAINING_NOT_VERIFIED
```

and select an appropriate external/fallback strategy instead.

---

## 7.3 Bounded Synthetic Resource Probe

A bounded, non-destructive CUDA memory/resource probe may be implemented to characterize the local host.

Such a probe may measure:

* available CUDA memory;
* bounded allocation behavior;
* allocation/release correctness;
* CUDA synchronization;
* cleanup behavior.

It must:

* use explicit upper bounds;
* terminate automatically;
* free allocated resources;
* avoid intentional host instability;
* avoid model training;
* avoid interpreting generic allocation success as model-specific training proof.

The probe is optional when accepted evidence already provides sufficient host characterization.

---

## 7.4 Host RAM and Storage Readiness

Measure and classify:

* system RAM;
* available RAM where practical;
* filesystem capacity;
* free storage;
* VLA environment storage location;
* planned dataset/model/checkpoint storage path where known.

Identify risks related to:

* model cache size;
* dataset growth;
* checkpoint growth;
* temporary artifacts;
* insufficient disk capacity.

Do not invent future dataset size.

If dataset size is not yet defined, record the storage estimate as:

```text
NOT_VERIFIED
```

or an explicitly documented planning assumption.

---

## 7.5 Training Compute Path

Define the primary future training path.

Record:

* execution mode;
* local or remote role;
* expected GPU class/resource class if defined;
* expected VRAM class if defined;
* software/runtime compatibility;
* how code/dataset/checkpoints will move between environments;
* reproducibility strategy;
* environment reconstruction strategy.

Do not provision infrastructure merely to satisfy this task unless explicitly authorized elsewhere.

---

## 7.6 Remote / External Compute Readiness

If `REMOTE_TRAINING` or `HYBRID_TRAINING` is selected, document the intended external compute path.

Evidence may include:

* approved existing resource;
* organizational GPU server;
* existing cloud account/resource;
* documented candidate resource class;
* authoritative provider/project pricing evidence;
* explicitly declared procurement policy.

Do not:

* create a paid account;
* purchase compute;
* start a paid GPU instance;
* enter payment information;
* commit credentials;
* store secrets;
* silently assume unlimited cloud availability.

If remote access or pricing cannot be verified, classify it accurately.

---

## 7.7 Budget Policy

Define the budget policy for future training.

The policy must be one of:

```text
LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET
APPROVED_NUMERIC_BUDGET_CEILING
EXISTING_PREPAID_RESOURCE
UNRESOLVED
```

If a numeric budget is required but no approved value exists, do not invent one.

Use:

```text
UNRESOLVED
```

and determine its blocking impact.

For numeric budgets record, when available:

* currency;
* approved ceiling;
* source/provenance;
* resource unit;
* expected runtime assumption;
* estimated cost;
* contingency;
* estimation date/source.

---

## 7.8 Cost Estimation

When sufficient inputs exist, calculate a bounded planning estimate.

Conceptually:

```text
estimated_compute_cost
=
unit_price
×
estimated_training_hours
```

Optionally include:

```text
storage
+
data transfer
+
contingency
```

when evidence supports those inputs.

Every value must have explicit provenance.

An estimated training duration must not be represented as measured unless actually measured in an authorized task.

---

## 7.9 Fallback Strategy

Define what happens when the primary compute path fails.

Examples:

```text
LOCAL training insufficient
→ REMOTE GPU fallback

REMOTE quota unavailable
→ alternate approved remote resource

Budget ceiling exceeded
→ stop / obtain new approval
```

The fallback must not silently bypass budget or architectural constraints.

---

## 7.10 Reproduction Strategy

Document how the future training environment will be recreated.

Include, where applicable:

* Python version;
* LeRobot version;
* PyTorch version;
* CUDA compatibility;
* dependency installation method;
* environment isolation;
* relevant configuration;
* artifact/cache locations;
* source revision expectations.

Do not silently upgrade the accepted VLA software baseline.

---

# 8. Explicitly Out of Scope

The following are prohibited.

## VLA Execution

* actual fine-tuning;
* training epochs;
* optimizer execution over SmolVLA training data;
* evaluation benchmark runs;
* autonomous hyperparameter search.

## Model Application

* production model inference;
* robot action generation;
* VLA-to-robot execution;
* ROS/VLA integration;
* Agent integration.

## Dataset

* Dataset V1 implementation;
* demonstration collection;
* data labeling;
* episode recording;
* Hugging Face dataset publication.

## Physical Robot

* robot motion;
* gripper motion;
* teleoperation;
* camera/robot remediation belonging to P0-006R.

## Procurement

* paid cloud purchase;
* GPU rental activation;
* billing configuration;
* credential creation/storage;
* hardware purchase.

## Downstream Tasks

* `TASK-P0-006R`;
* `TASK-P0-004R`;
* `TASK-W1-001` or later Week 1 implementation.

---

# 9. Evidence Provenance

Every material resource and budget fact shall use explicit provenance.

Allowed provenance values:

```text
MEASURED
DECLARED_INPUT
DERIVED
DOCUMENTED
NOT_VERIFIED
```

Definitions:

### MEASURED

Directly observed by the verifier on the local or explicitly available environment.

### DECLARED_INPUT

Explicitly supplied by the user/operator but not independently verified.

### DERIVED

Calculated from other evidenced inputs.

### DOCUMENTED

Obtained from an accepted project document or authoritative resource definition.

### NOT_VERIFIED

Insufficient evidence exists.

Do not upgrade:

```text
DECLARED_INPUT
DOCUMENTED
DERIVED
```

into:

```text
MEASURED
```

without actual measurement evidence.

---

# 10. Required Artifacts

## 10.1 Canonical Verifier

```text
scripts/verify_training_resource_readiness.py
```

The verifier shall be:

* bounded;
* non-destructive;
* fail-closed;
* deterministic where practical;
* explicit about unavailable facts;
* capable of atomic JSON output.

---

## 10.2 Machine-readable Evidence

```text
results/phase0/P0-007_training_resource_readiness.json
```

At minimum include:

* task identity;
* generation provenance;
* accepted predecessor evidence hashes;
* local hardware facts;
* GPU/VRAM;
* RAM/storage facts;
* local training classification;
* selected execution mode;
* primary training path;
* budget policy;
* cost inputs where applicable;
* fallback path;
* unresolved blockers;
* deferred items;
* overall decision;
* authorization fields.

---

## 10.3 Human-readable Readiness Document

```text
docs/vla/training_compute_readiness_v1.md
```

Include:

* executive decision;
* local host role;
* training execution mode;
* local resource measurements;
* local-training limitation;
* remote/hybrid strategy when applicable;
* storage strategy;
* budget policy;
* fallback;
* reproduction procedure;
* explicitly unverified claims.

---

## 10.4 Training Compute / Budget Plan

```text
plans/vla_training_compute_budget_plan.md
```

Include:

* primary resource;
* fallback resource;
* resource requirements;
* cost assumptions;
* budget ceiling/policy;
* stop conditions;
* approval dependencies;
* future-task ownership.

---

## 10.5 Risk Register

```text
plans/vla_training_resource_risks.md
```

Each risk shall be classified as:

```text
RESOLVED
DEFERRED
BLOCKING
OUT_OF_SCOPE
```

Record:

* ID;
* description;
* evidence;
* impact;
* disposition;
* future owner/task.

---

## 10.6 Task History

Create/update:

```text
docs/task_history/TASK-P0-007/01_implementation.md
docs/task_history/TASK-P0-007/README.md
docs/task_history/README.md
```

Independent review history shall not be created during implementation.

---

# 11. Minimum Verification Dimensions

The evidence shall explicitly contain results for:

```text
C01 Accepted VLA runtime preserved
C02 Local GPU identity measured
C03 Local VRAM measured
C04 CUDA execution remains available
C05 Host RAM characterized
C06 Storage capacity characterized
C07 Local training role explicitly classified
C08 Training execution mode selected
C09 Primary training resource identified
C10 Software/runtime compatibility documented
C11 Model/dataset/checkpoint storage strategy defined
C12 Budget policy defined
C13 Cost inputs provenance validated when applicable
C14 Primary-path budget feasibility classified
C15 Fallback compute strategy defined
C16 Reproduction strategy documented
C17 Unsupported training-fit claims rejected
C18 No actual fine-tuning/training executed
C19 No downstream task leakage
C20 Final readiness decision and authorization consistent
```

Mandatory checks shall remain mandatory.

A verifier or evidence consumer must not be able to demote a failed mandatory check to obtain READY.

---

# 12. Exit Criteria

## EC-01 — Correct Context

The task correctly recognizes:

```text
TASK-P0-005 = ACCEPTED
TASK-P0-006 = ACCEPTED
P0-006 physical outcome = DEVICE_IO_BLOCKED
TASK-W1-001 authorized = false
TASK-P0-004R required = true
```

---

## EC-02 — Runtime Preservation

Accepted P0-005 evidence remains unchanged.

No accepted dependency/runtime baseline is silently upgraded.

---

## EC-03 — Local Hardware Measurement

GPU and host resource facts required by this task are measured or explicitly classified as unavailable.

---

## EC-04 — Local Training Classification

The local environment is classified as exactly one:

```text
TRAINING_VERIFIED
TRAINING_NOT_VERIFIED
TRAINING_UNSUITABLE
```

The classification is supported by evidence.

---

## EC-05 — No False 6 GB Claim

The task does not claim that SmolVLA training fits within 6 GB solely because:

* CUDA works;
* free VRAM exists;
* synthetic allocations succeed;
* imports succeed;
* configuration instantiation succeeds.

---

## EC-06 — Execution Mode

The intended training execution mode is exactly one of:

```text
LOCAL_TRAINING
REMOTE_TRAINING
HYBRID_TRAINING
UNRESOLVED
```

---

## EC-07 — Primary Resource

The selected execution mode has a concrete primary compute path or is explicitly blocked.

---

## EC-08 — Runtime Compatibility

The training path documents compatibility with the accepted Python/LeRobot/PyTorch runtime strategy.

Unknown compatibility remains unresolved.

---

## EC-09 — Storage Readiness

Model/dataset/checkpoint/cache storage strategy is documented.

Unknown dataset-size-dependent requirements remain explicitly unverified.

---

## EC-10 — Budget Policy

Exactly one budget policy is recorded:

```text
LOCAL_ONLY_ZERO_INCREMENTAL_BUDGET
APPROVED_NUMERIC_BUDGET_CEILING
EXISTING_PREPAID_RESOURCE
UNRESOLVED
```

No numeric budget is invented.

---

## EC-11 — Cost Provenance

When cost estimation is performed, every material input has provenance.

Estimated values are not represented as measured values.

---

## EC-12 — Budget Feasibility

The primary training path is classified against the budget policy as:

```text
WITHIN_POLICY
OUTSIDE_POLICY
NOT_VERIFIED
```

---

## EC-13 — Fallback

A fallback path exists or its absence is explicitly blocking.

---

## EC-14 — Reproducibility

The future training environment has a reproducible reconstruction strategy.

---

## EC-15 — No Procurement

No paid compute resource or hardware is purchased or activated.

---

## EC-16 — No Training

No actual SmolVLA training/fine-tuning is executed.

---

## EC-17 — Scope Preservation

No:

* Dataset V1;
* robot/camera remediation;
* physical teleoperation;
* VLA/robot integration;
* Agent integration;
* P0-006R;
* P0-004R;
* Week 1 implementation

is introduced.

---

## EC-18 — Validation

Focused tests and full repository regression pass.

---

## EC-19 — Evidence Integrity

Verifier output, evidence, documentation, budget plan, risk register, and task history agree on all material decisions.

---

## EC-20 — Final Decision

Return exactly one:

```text
TRAINING_RESOURCE_READY
TRAINING_RESOURCE_BLOCKED
```

and explicitly state:

```text
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

---

# 13. Decision Rules

Return:

```text
TRAINING_RESOURCE_READY
```

only when all mandatory conditions are satisfied.

At minimum:

1. accepted P0-005 runtime remains valid;
2. local resource facts are characterized;
3. local training role is honestly classified;
4. an execution mode is selected;
5. a credible primary training path exists;
6. software compatibility is documented;
7. storage strategy exists;
8. budget policy exists;
9. cost feasibility is sufficiently classified;
10. fallback exists or is demonstrably unnecessary;
11. reproducibility strategy exists;
12. no unsupported training-fit claim is required.

---

Return:

```text
TRAINING_RESOURCE_BLOCKED
```

if any mandatory condition remains unresolved.

Examples:

* execution mode remains `UNRESOLVED`;
* remote training is required but no credible resource exists;
* numeric budget is required but no approved ceiling exists;
* runtime compatibility is unknown;
* storage path is insufficient;
* no fallback exists when the primary path is unverified;
* readiness requires an unsupported assumption about 6 GB training feasibility.

---

# 14. Important Decision Example

The following may legitimately produce READY:

```text
Local GPU:
RTX 2060 Max-Q / 6 GB

Local training:
TRAINING_NOT_VERIFIED

Execution mode:
HYBRID_TRAINING

Local role:
development / configuration / bounded validation

Training role:
verified external compute path

Budget:
approved / evidenced

Fallback:
defined
```

Therefore:

```text
TRAINING_RESOURCE_READY
```

does not require local 6 GB training to be proven.

Conversely:

```text
Local training:
TRAINING_NOT_VERIFIED

Remote resource:
UNRESOLVED

Budget:
UNRESOLVED
```

must produce:

```text
TRAINING_RESOURCE_BLOCKED
```

---

# 15. Test Requirements

At minimum implement and/or run tests for:

## Positive Paths

* valid resource evidence;
* valid execution-mode classification;
* valid budget-policy classification;
* valid fallback;
* valid READY aggregate when all mandatory conditions are satisfied.

## Negative Paths

* missing execution mode;
* unsupported local-training claim;
* missing required resource;
* missing budget policy;
* malformed numeric budget;
* cost outside policy;
* missing fallback;
* unknown compatibility;
* invalid provenance;
* mandatory-check demotion attempt;
* mismatched unresolved blockers;
* manipulated READY artifact.

## Boundary Paths

* exactly-at-budget-ceiling;
* zero incremental local budget;
* zero/invalid storage;
* missing cost estimate where numeric estimate is required;
* `NOT_VERIFIED` training fit;
* unavailable remote resource.

## Evidence Integrity

Verify:

* check identity;
* ordering;
* uniqueness;
* mandatory flags;
* allowed status enums;
* allowed provenance enums;
* blocker projection;
* final decision consistency;
* source hashes;
* predecessor hashes.

---

# 16. Validation Requirements

Run:

1. canonical verifier;
2. safe verifier rerun;
3. focused P0-007 tests;
4. evidence-tampering tests;
5. full repository regression;
6. JSON/schema/invariant validation;
7. relevant syntax/static checks;
8. `git diff --check`.

Verify that:

```text
P0-005 accepted evidence
```

and accepted P0-006 evidence/source history remain unchanged unless explicitly permitted by repository policy.

---

# 17. Required Implementation Report

At completion return:

```markdown
# Implementation Result — TASK-P0-007

## Scope

## Files Changed

## Local Compute

## Local Training Classification

## Training Execution Mode

## Primary Training Resource

## Storage Readiness

## Budget Policy

## Cost / Budget Classification

## Fallback Strategy

## Tests Run

## Exit Criteria

## Evidence

## Risks / Deferred Items

## Repository Check

## Readiness and Authorization

## Recommended Commit Message

## Final Status
```

The report shall explicitly include:

```text
TASK-P0-007 is complete.
```

or:

```text
TASK-P0-007 is NOT complete.
```

separately from:

```text
TRAINING_RESOURCE_READY
```

or:

```text
TRAINING_RESOURCE_BLOCKED
```

and:

```text
TASK-W1-001 authorized: false
TASK-P0-004R required: true
```

---

# 18. Independent Review Policy

Implementation completion does not imply acceptance.

After implementation, execute a separate READ-ONLY Independent Review.

The review shall verify:

* requirement traceability;
* compute-resource facts;
* local 6 GB training claims;
* provenance;
* budget calculations;
* cost assumptions;
* readiness aggregation;
* tamper resistance;
* scope preservation;
* regression safety;
* evidence integrity.

Findings shall be classified:

```text
BLOCKER
HIGH
MEDIUM
LOW
```

Only independently accepted P0-007 evidence may be consumed by `TASK-P0-004R`.

---

# 19. Completion Definition

Implementation is complete when:

1. all required artifacts exist;
2. all ECs have explicit outcomes;
3. canonical readiness evidence exists;
4. focused validation is complete;
5. regression is green;
6. evidence integrity is validated;
7. task history is recorded;
8. no downstream implementation was started.

The Task becomes:

```text
ACCEPTED
```

only after Independent Review.

A task may be:

```text
ACCEPTED
```

while its task-specific result remains:

```text
TRAINING_RESOURCE_BLOCKED
```

if that blocked result is truthful and correctly evidenced.

---

# 20. Phase 0 Relationship

```text
TASK-P0-005
VLA Runtime
ACCEPTED
       │
       ├─────────────────────┐
       │                     │
       ▼                     ▼
TASK-P0-006              TASK-P0-007
Device I/O               Training Compute /
ACCEPTED                 Budget Readiness
       │                     │
DEVICE_IO_BLOCKED            │
       │                     │
       ▼                     ▼
Physical remediation     Independent Review
       │                     │
       ▼                     ▼
TASK-P0-006R            Accepted P0-007 Evidence
       │                     │
DEVICE_IO_READY              │
       └──────────┬──────────┘
                  │
                  ▼
       Outstanding Finding
          Remediation
                  │
                  ▼
            TASK-P0-004R
        Consolidated Re-Gate
                  │
             ┌────┴────┐
             │         │
           NO_GO      GO
                       │
                       ▼
              Baseline Promotion
                       │
                       ▼
                Week 1 Authorization
```

P0-007 shall never bypass `TASK-P0-004R`.
