# TASK-P0-005 — VLA Runtime Environment Enablement & CUDA/LeRobot/SmolVLA Verification

> Status: READY FOR EXECUTION
> Phase: Phase 0 / VLA Readiness Remediation
> Workstream: VLA Software Runtime
> Depends on: `TASK-P0-004 = NO_GO`
> Recommended Branch: `task/p0-005-vla-runtime`
> Preferred Environment: `.venv-vla`
> Physical Robot Authorized: **NO**
> Dataset V1 / Fine-tuning Authorized: **NO**
> Authorizes `TASK-W1-001`: **NO — a later `TASK-P0-004R` re-gate is required**

---

## 1. Goal

Resolve only the software/runtime blockers identified by `TASK-P0-004` and produce reproducible evidence that the selected WSL2 host either can or cannot provide the intended PyTorch CUDA + LeRobot + SmolVLA development runtime.

The task must:

1. create a project-local isolated VLA Python environment;
2. make and record an explicit Python-version decision;
3. manage the environment with `uv`;
4. verify the installed PyTorch CUDA runtime rather than infer it from the NVIDIA driver;
5. execute and verify a real CUDA tensor operation;
6. make and record an explicit LeRobot-version decision, then install that version with a direct pin;
7. validate required LeRobot imports;
8. discover the installed SmolVLA dependency, module, and configuration surfaces without training;
9. classify what the measured RTX 2060-class GPU with 6 GB VRAM does and does not prove; and
10. generate machine-readable runtime evidence.

This task must finish with exactly one runtime decision:

```text
RUNTIME_READY
CONDITIONAL_RUNTIME_READY
RUNTIME_BLOCKED
```

That decision applies only to the VLA software/runtime lane. It is not the overall VLA readiness decision and does not authorize `TASK-W1-001`.

---

## 2. Why

`TASK-P0-004` ended with `NO_GO` because the measured host had no working CUDA execution evidence, no isolated VLA environment, no LeRobot installation, and no SmolVLA module/config discovery. Those failures prevent a reproducible VLA learning loop even before physical devices, teleoperation, Dataset V1, or training are considered.

The environment has since changed, but the new observations are inputs, not accepted evidence. P0-005 exists to replace assumptions and stale measurements with a repeatable runtime verifier and an explicit dependency decision.

The historical `plans/next_tasks_after_phase0.md` entry labels P0-005 as a teleoperation/recording smoke slice after a P0-004 `GO`. This task specification explicitly supersedes that stale task-number assignment because P0-004 instead produced `NO_GO` and software/runtime remediation must occur before physical smoke work. P0-005 does not silently authorize the old scope: physical-device readiness and supervised teleoperation remain deferred to P0-006/P0-007, and the consolidated readiness decision remains P0-004R. Planning-index reconciliation is outside this task-authoring turn.

The runtime track remains independent of the Agent/MVP lane and must not expand the frozen Day-10 scope.

---

## 3. Inputs

Read completely before implementation:

- `AGENTS.md`;
- all files under `context/`;
- `docs/architecture/system_architecture_v1.md`;
- `docs/contracts/contract_plan.md`;
- `docs/architecture/adr/ADR-004-vla-stack.md`;
- other relevant ADRs, especially deployment and hardware-boundary decisions;
- `docs/vla/vla_readiness_v1.md`;
- `results/phase0/P0-004_vla_readiness.json`;
- `plans/vla_readiness_risks.md`;
- `plans/next_vla_task_after_p0_004.md`;
- `scripts/verify_vla_readiness.py`;
- current packaging, ignore, environment, and dependency files; and
- this task file in full.

Before changing files, run:

```bash
pwd
git branch --show-current
git status
git log --oneline -5
```

Expected repository context:

```text
working directory: /home/jinho/projects/factory_physical_ai_p0_005
branch: task/p0-005-vla-runtime
working tree: clean before task changes
```

### 3.1 Newly supplied observations

Treat the following only as unverified input observations. The P0-005 implementation must re-measure them and store the results as evidence:

```text
host: WSL2 / Ubuntu 24.04
nvidia-smi: succeeds
NVIDIA-SMI: 580.102.01
Driver Version: 581.57
driver-reported CUDA Version: 13.0
GPU: NVIDIA GeForce RTX 2060-class
VRAM: 6144 MiB
/dev/dxg: exists
active GPU processes at observation time: none
```

The `nvidia-smi` header field:

```text
CUDA Version: 13.0
```

is a driver capability report. By itself it does **not** prove that:

- CUDA Toolkit 13.0 is installed;
- PyTorch is using CUDA 13.0;
- PyTorch CUDA works;
- LeRobot is compatible; or
- SmolVLA training fits in 6 GB VRAM.

The implementation must preserve these distinctions in both human-readable and machine-readable outputs.

---

## 4. Scope

P0-005 covers only the VLA software runtime on the intended WSL2 development/CUDA host.

### 4.1 Runtime setup

- select a Python version supported by the chosen PyTorch and LeRobot combination;
- install or use `uv` without mutating system Python;
- create `.venv-vla` as the preferred project-local environment;
- install directly pinned PyTorch and LeRobot packages into `.venv-vla`;
- record direct pins, resolved versions, package source/index information, and reproducible commands.

### 4.2 Runtime verification

- re-measure WSL/OS/kernel, `/dev/dxg`, GPU identity, driver, driver-reported CUDA compatibility, VRAM, and GPU process state;
- verify PyTorch import and its installed build/runtime metadata;
- verify `torch.cuda.is_available()`, device count/name, and device capability;
- execute a real CUDA tensor operation, synchronize it, return a result to CPU, and validate the numerical result;
- record memory information before and after the bounded tensor check;
- verify the selected LeRobot installation and required imports;
- discover the installed SmolVLA policy/config modules and inspect a non-training configuration surface;
- classify the 6 GB GPU capability without claiming unperformed inference or training.

### 4.3 Documentation and evidence

- explain the Python, PyTorch, CUDA-runtime, and LeRobot compatibility decision;
- record unresolved constraints and the precise downstream validation trigger;
- emit deterministic machine-readable evidence from a safe verification script.

---

## 5. Architecture Constraints

The accepted architecture remains unchanged.

1. P0-005 verifies a development runtime only. It does not create a VLA skill or physical execution path.
2. The LLM Agent must not issue raw motor, joint, trajectory, ROS, shell, or actuator commands.
3. The deterministic runtime retains authorization, timeout, retry, idempotency, reconciliation, and business-recovery ownership.
4. VLA remains a bounded sensorimotor policy behind a future typed skill boundary.
5. MoveIt and `ros2_control` retain their accepted motion-planning, collision, controller, and hardware authority where applicable.
6. WSL GPU visibility is not evidence of manipulator, camera, ROS-edge, or physical safety readiness.
7. No accepted ADR may be silently reinterpreted. If the dependency decision requires an architectural change, record it as an explicit review item; do not silently change the architecture in this task.
8. ADR-004 remains proposed until the complete readiness re-gate accepts the VLA stack. A successful P0-005 runtime result alone does not accept the full VLA architecture.

---

## 6. Environment Strategy

### 6.1 Isolation

Use the repository-local environment:

```text
.venv-vla
```

The implementation must explicitly prohibit and avoid mutation of system Python. It must not:

- run `sudo pip`, system `pip install`, or an equivalent privileged Python package installation;
- install VLA dependencies into `/usr/bin/python3` or the distribution-managed site-packages;
- use flags that bypass externally-managed-environment protection;
- replace the system `python3`, system CUDA libraries, WSL kernel, or NVIDIA driver; or
- install OS packages or drivers as an implicit side effect of the verifier.

If `uv` is absent, use an approved standalone/user-scoped `uv` installation path that does not mutate system Python. Record the installation source, `uv` version, executable path, and command. If that cannot be done safely, set the runtime decision according to the Final Decision Rules rather than falling back to system `pip`.

The environment directory must be ignored by Git. Updating `.gitignore` to add `.venv-vla/` is allowed if required.

### 6.2 Python version selection

Do not select Python merely because `/usr/bin/python3` exists. Determine the version from the compatibility intersection of:

- the selected LeRobot release;
- the selected PyTorch build;
- the SmolVLA extra and its resolved dependencies; and
- Ubuntu 24.04 / WSL2 execution constraints.

Record:

- candidates considered;
- authoritative compatibility sources or package metadata;
- selected exact Python major/minor version;
- interpreter source and path;
- why the version was selected; and
- any rejected candidate and the blocking reason.

If the system Python version is not the correct choice, use a `uv`-managed interpreter. Do not modify or replace system Python.

### 6.3 Dependency and version policy

The repository currently contains an older documented LeRobot baseline in ADR-004/P0-004. It must not be silently replaced by the latest upstream release.

Before installation, make an explicit LeRobot dependency decision that records:

```text
repository baseline version
upstream/current candidate considered
selected exact version or source revision
selected installation extra(s)
Python compatibility
PyTorch compatibility
reason for retaining or changing the baseline
known trade-offs
reproduction command
```

Use primary/official package metadata and documentation for compatibility decisions. Install the chosen LeRobot release with an exact pin. Record the exact PyTorch version and build source/index as well. Do not use an unbounded `latest`, an unpinned Git branch, or a floating package specification.

If the repository assumption and current upstream guidance differ, document an explicit dependency/version decision. If the difference changes an accepted architecture decision, stop that design change and raise an ADR review item.

### 6.4 CUDA interpretation

Keep these facts separate:

```text
NVIDIA driver and its reported CUDA compatibility ceiling
CUDA Toolkit / nvcc installation, if any
PyTorch package build version
PyTorch-reported CUDA runtime version
actual CUDA device execution
LeRobot/SmolVLA dependency compatibility
```

The task does not require a system CUDA Toolkit if the selected official PyTorch package supplies the required CUDA runtime. It does require measured PyTorch CUDA execution.

---

## 7. Implementation Requirements

### IR-01 — Safe environment bootstrap

Create `.venv-vla` with `uv` using the selected Python version. Document every setup/install command. The commands must be safe to rerun or must fail with an actionable explanation.

The bootstrap must not be embedded in `scripts/verify_vla_runtime.py`; verification and installation are separate operations. The verifier must never install packages, drivers, toolkits, models, or OS dependencies.

### IR-02 — PyTorch CUDA runtime verification

Inside `.venv-vla`, measure and record at minimum:

- Python executable and version;
- PyTorch version;
- PyTorch build metadata;
- `torch.version.cuda`;
- `torch.cuda.is_available()`;
- CUDA device count;
- selected device index and exact name;
- device compute capability as reported by PyTorch;
- total/free VRAM visible to the runtime;
- cuDNN version/availability where exposed; and
- any import or initialization error with a structured failure category.

Do not infer the PyTorch CUDA runtime from `nvidia-smi` or `nvcc`.

### IR-03 — Actual CUDA tensor execution

Run one bounded, deterministic CUDA operation that:

1. allocates input tensors on the selected CUDA device;
2. performs arithmetic or a small matrix operation on the GPU;
3. explicitly synchronizes the CUDA device;
4. copies the result to CPU;
5. validates the numerical result against an expected value; and
6. records PASS/FAIL, elapsed time as diagnostic-only data, and allocated/reserved/peak memory.

This is a runtime proof, not a performance benchmark. Do not present its timing as model latency or production evidence.

### IR-04 — LeRobot version decision and pinned installation

Determine and record the LeRobot version explicitly before installation. Install exactly that version/source revision into `.venv-vla` with the required SmolVLA extra or an explicitly justified equivalent.

Record:

- direct dependency pins;
- resolved LeRobot version/source revision;
- resolved PyTorch version/build;
- relevant resolved SmolVLA dependencies;
- dependency resolver output or conflict summary;
- package source/index; and
- an environment package snapshot sufficient to reproduce or diagnose the runtime.

A successful resolver exit alone is not import validation.

### IR-05 — LeRobot import validation

Verify at minimum the installed-version equivalents of:

```text
lerobot
lerobot.datasets.lerobot_dataset
lerobot.policies.smolvla
SmolVLA modeling module
SmolVLA configuration module
```

Module paths may differ by the selected pinned release. If they differ, record the authoritative installed paths and why; do not mark a nonexistent historical path as a package failure when the supported API moved.

Capture each import independently so one failure does not hide the others. Record module name, PASS/FAIL, resolved file path where safe, and a bounded error string.

### IR-06 — SmolVLA dependency/module/config discovery

Without downloading model weights or starting training:

- discover the installed SmolVLA policy, modeling, preprocessing/processing, and configuration surfaces available in the selected LeRobot release;
- instantiate or inspect a non-training config when supported without network/model download;
- record the planned model identifier separately from installed code;
- record key config metadata relevant to compatibility/capacity when available;
- identify missing optional dependencies or API changes; and
- distinguish package/module discovery from model load, inference, fine-tuning, and evaluation.

If safe config discovery would trigger a model download, stop that check, record it as deferred, and do not download the model implicitly.

### IR-07 — RTX 2060-class 6 GB capability classification

Re-measure the actual GPU identity and VRAM. Classify the host using measured facts and explicit inference, covering at minimum:

- NVIDIA/WSL device visibility;
- working PyTorch CUDA tensor execution;
- LeRobot/SmolVLA import and config-discovery capability;
- VRAM total/free at verification time;
- whether local SmolVLA model loading was tested;
- whether local SmolVLA inference was tested;
- whether local SmolVLA fine-tuning was tested; and
- whether SmolVLA training fit in 6 GB is `PROVEN`, `DISPROVEN`, or `NOT_VERIFIED`.

Because model loading, inference, and fine-tuning are not required by P0-005, do not elevate import/config success into a claim that SmolVLA runs or trains locally. `PROVEN` or `DISPROVEN` requires direct, authorized, configuration-specific measured evidence; otherwise use `NOT_VERIFIED`.

Document likely constraints and candidate mitigations only as `INFERRED`, for example reduced batch size, precision, gradient accumulation/checkpointing, parameter-efficient tuning, or a remote CUDA host. Do not present them as verified feasibility.

### IR-08 — Verification script

Create `scripts/verify_vla_runtime.py` as a safe, non-destructive, bounded verifier.

It must:

- verify it is running from the intended project-local VLA interpreter or record a clear failure;
- perform the host, NVIDIA, PyTorch CUDA, tensor, LeRobot import, and safe SmolVLA discovery checks;
- use timeouts for external diagnostic commands;
- redact secrets and avoid recording sensitive environment-variable values;
- avoid unbounded stack traces or command output in evidence;
- distinguish `MEASURED`, `INFERRED`, `DEFERRED`, and `NOT_AVAILABLE`;
- write valid JSON atomically or otherwise avoid leaving a false-success partial result;
- return non-zero for runtime-blocking verification failures; and
- remain safe to rerun.

It must not:

- install or upgrade anything;
- invoke `sudo`;
- modify system Python, CUDA, drivers, WSL, or devices;
- download a model or dataset;
- open a robot or camera device;
- command an actuator;
- start inference, training, fine-tuning, or evaluation; or
- emit secrets, tokens, or credentials.

### IR-09 — Runtime documentation and risks

Document the exact environment reproduction procedure, compatibility decision, measured checks, limitations, and rollback/removal procedure for `.venv-vla` without deleting unrelated environments or user data.

Update the runtime risk plan with owner, impact, evidence, mitigation, trigger, and blocking status for every unresolved software/runtime risk. Preserve P0-004 hardware, camera, teleoperation, and budget blockers as deferred to their own tasks rather than marking them resolved.

---

## 8. Required Outputs

Create exactly these required task artifacts:

### O1 — Runtime environment report

```text
docs/vla/vla_runtime_environment_v1.md
```

Minimum contents:

```text
Decision
Input Observations vs Re-measured Evidence
Environment Strategy
Python Version Decision
uv Setup
NVIDIA Driver vs Toolkit vs PyTorch CUDA
PyTorch CUDA Verification
CUDA Tensor Execution
LeRobot Version Decision
LeRobot Import Validation
SmolVLA Module/Config Discovery
RTX 2060 6 GB Capability Classification
Limitations
Reproduction Commands
Deferred Readiness Blockers
```

### O2 — Machine-readable runtime evidence

```text
results/phase0/P0-005_vla_runtime.json
```

Minimum structure:

```json
{
  "schema_version": "1.0",
  "task": "TASK-P0-005",
  "runtime_decision": "RUNTIME_READY | CONDITIONAL_RUNTIME_READY | RUNTIME_BLOCKED",
  "generated_at": "ISO-8601 UTC",
  "git": {},
  "host": {},
  "input_observations": {},
  "python_decision": {},
  "uv": {},
  "environment": {},
  "nvidia": {},
  "cuda_toolkit": {},
  "torch": {},
  "cuda_tensor_test": {},
  "lerobot_version_decision": {},
  "lerobot": {},
  "smolvla": {},
  "gpu_capability_classification": {},
  "checks": [],
  "runtime_blockers": [],
  "deferred_non_runtime_blockers": [],
  "safety": {},
  "task_w1_001_authorized": false,
  "p0_004r_regate_required": true
}
```

### O3 — Runtime verification script

```text
scripts/verify_vla_runtime.py
```

### O4 — Runtime risk plan

```text
plans/vla_runtime_risks.md
```

At minimum include:

```text
risk ID
risk
impact
evidence
mitigation
trigger / exit signal
owner
blocking for P0-005 runtime decision?
blocking for later P0-004R readiness?
```

### 8.1 Allowed auxiliary change

Only if needed, `.gitignore` may be updated to exclude `.venv-vla/`. Do not commit the environment directory, package cache, model weights, Hugging Face cache, credentials, or machine-local binary artifacts.

Do not create application source code in this task.

---

## 9. Validation Plan

Run validation from the expected branch and project-local VLA environment.

### 9.1 Repository and isolation checks

```bash
pwd
git branch --show-current
git status
uv --version
.venv-vla/bin/python --version
.venv-vla/bin/python -c "import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix)"
```

Verify that:

- the interpreter resolves inside `.venv-vla`;
- `sys.prefix != sys.base_prefix`;
- system site-packages were not mutated by the task;
- `.venv-vla/` is ignored; and
- no environment/cache/model artifact is tracked.

### 9.2 Static and structured-output checks

```bash
.venv-vla/bin/python -m compileall -q scripts/verify_vla_runtime.py
.venv-vla/bin/python scripts/verify_vla_runtime.py
.venv-vla/bin/python -m json.tool results/phase0/P0-005_vla_runtime.json >/dev/null
git diff --check
```

Use repository-defined lint/type/test commands if they exist and apply to the new script. Do not install unrelated tooling solely to satisfy this task.

### 9.3 Required measured checks

The validation evidence must include PASS/FAIL/DEFERRED results for:

1. WSL2/OS/kernel re-measurement;
2. `/dev/dxg` visibility;
3. `nvidia-smi` executable and bounded query;
4. GPU model, driver, driver-reported CUDA compatibility, total/free VRAM, and process state;
5. selected Python interpreter and isolated environment;
6. `uv` version and executable;
7. PyTorch import/version/build;
8. PyTorch CUDA availability/device/capability;
9. actual synchronized CUDA tensor execution and numerical assertion;
10. LeRobot installed version/source and independent imports;
11. SmolVLA module/config discovery without model download;
12. 6 GB capability classification and training-fit evidence status;
13. required JSON fields and enum values;
14. all safety flags remaining false; and
15. `task_w1_001_authorized = false` plus `p0_004r_regate_required = true`.

If network/package installation is unavailable, preserve the measured failure and select the appropriate runtime decision. Do not substitute a globally installed package, mocked import, or fabricated result.

---

## 10. Evidence Rules

1. Evidence must distinguish:

   ```text
   MEASURED
   INFERRED
   DEFERRED
   NOT_AVAILABLE
   ```

2. Re-measure every supplied environment observation. Store supplied values separately from measured values so changes and mismatches are visible.
3. Record actual command return codes and bounded/sanitized output where useful.
4. Record timestamp, Git commit SHA, branch, script version/schema, Python/`uv`/PyTorch/LeRobot versions, and selected dependency sources.
5. Do not record secrets, tokens, private package credentials, full environment dumps, or unnecessary personal paths.
6. Do not fabricate compatibility, performance, memory, inference, training, or benchmark results.
7. A successful `nvidia-smi` is not a substitute for the CUDA tensor test.
8. A successful package install is not a substitute for import/config validation.
9. Successful SmolVLA imports/config discovery are not evidence that weights load, inference succeeds, or fine-tuning fits in 6 GB.
10. Tensor-test timing is diagnostic only and must not be reported as a benchmark.
11. Input observations must never be relabeled as measured results without rerunning the corresponding check.
12. If a check cannot run, use `DEFERRED` or `NOT_AVAILABLE` with a concrete reason and trigger; do not infer PASS.

---

## 11. Explicit Out-of-Scope

P0-005 must not implement, execute, authorize, or claim completion of:

- manipulator or other physical device I/O;
- camera enumeration, capture, calibration, or observation streaming;
- physical teleoperation or robot motion;
- Dataset V1 collection or dataset episode creation;
- model-weight download unless separately and explicitly authorized outside this task;
- SmolVLA model loading or inference as a required acceptance check;
- SmolVLA fine-tuning or any training run;
- VLA evaluation, benchmark, success-rate, or latency claim;
- VLA Skill Server;
- ROS 2, Nav2, MoveIt, or `ros2_control` integration;
- Agent integration;
- WMS, Fleet, PHM, MES, or factory integration;
- training budget/provider/limit approval;
- CUDA Toolkit, NVIDIA driver, WSL kernel, or system Python mutation;
- application feature code under `src/**`;
- architecture changes unrelated to recording an explicit dependency review item;
- `TASK-P0-006`;
- `TASK-P0-007`; or
- `TASK-W1-001`.

Expected downstream separation:

- `TASK-P0-006`: native physical device/manipulator and camera readiness, including identity/connectivity and no-motion safety prerequisites;
- `TASK-P0-007`: supervised teleoperation/recording smoke readiness and remaining operational/training-budget prerequisites, under its own explicit authorization; and
- `TASK-P0-004R`: aggregate P0-005/P0-006/P0-007 evidence, rerun the complete VLA readiness gate, review ADR-004 status, and explicitly decide whether `TASK-W1-001` is authorized.

The exact implementation scope of P0-006 and P0-007 must be defined in their own task specifications. P0-005 must not pre-implement them.

---

## 12. Exit Criteria

P0-005 is complete only when every applicable criterion is explicitly reported as PASS, FAIL, or BLOCKED.

- [ ] **EC-01 Repository context:** working directory and branch match the task; pre-change Git state was inspected.
- [ ] **EC-02 Isolation:** `.venv-vla` exists, is managed with `uv`, resolves to the selected interpreter, is Git-ignored, and system Python was not mutated.
- [ ] **EC-03 Python decision:** exact Python version, compatibility evidence, rationale, interpreter source, and rejected alternatives are recorded.
- [ ] **EC-04 Dependency decision:** exact LeRobot and PyTorch versions/build sources are explicitly selected and directly pinned; the older repository baseline was retained or changed with recorded rationale rather than silently replaced.
- [ ] **EC-05 NVIDIA facts:** WSL, `/dev/dxg`, GPU, driver, driver-reported CUDA compatibility, VRAM, and process state are re-measured.
- [ ] **EC-06 CUDA distinction:** driver capability, Toolkit presence, PyTorch build/runtime, and actual execution are recorded separately.
- [ ] **EC-07 PyTorch CUDA:** PyTorch imports and reports CUDA availability/device facts from `.venv-vla`.
- [ ] **EC-08 Tensor execution:** the bounded CUDA tensor operation synchronizes, returns to CPU, and passes a numerical assertion, or the exact blocking failure is recorded.
- [ ] **EC-09 LeRobot imports:** installed LeRobot version/source and each required installed-version import are independently validated.
- [ ] **EC-10 SmolVLA discovery:** dependency/module/config discovery is completed without implicit model download or training, or the exact runtime blocker is recorded.
- [ ] **EC-11 6 GB classification:** capability and limitations are evidence-backed; training fit is marked `PROVEN`, `DISPROVEN`, or `NOT_VERIFIED` without overclaiming.
- [ ] **EC-12 Required outputs:** all four required artifacts exist and agree on versions, checks, blockers, and decision.
- [ ] **EC-13 Evidence integrity:** evidence kinds, provenance, timestamps, Git state, bounded errors, and safety flags are present; no secret or invented result is included.
- [ ] **EC-14 Safe verifier:** the script is non-destructive, bounded, safe to rerun, and returns non-zero for runtime-blocking failures.
- [ ] **EC-15 Scope control:** no application code, device I/O, camera work, teleoperation, dataset, model load, inference, training, evaluation, service, ROS, Agent, or budget-approval work was started.
- [ ] **EC-16 Validation:** compile/JSON validation, applicable repository checks, and `git diff --check` pass.
- [ ] **EC-17 Single decision:** the report and JSON contain exactly one allowed `runtime_decision` value under the Final Decision Rules.
- [ ] **EC-18 Authorization boundary:** every output states that `TASK-W1-001` remains unauthorized and `TASK-P0-004R` remains required.

Failed runtime checks do not make the task incomplete if they are measured, correctly evidenced, and result in `RUNTIME_BLOCKED`. Missing required artifacts, fabricated evidence, unsafe mutation, or scope expansion do make the task incomplete.

---

## 13. Final Decision Rules

Emit exactly one `runtime_decision` in the report and JSON.

### `RUNTIME_READY`

Use only when:

- the project-local `uv` environment and selected Python version are reproducible;
- direct PyTorch and LeRobot versions are explicitly pinned;
- PyTorch imports and actual CUDA tensor execution pass;
- required LeRobot imports pass;
- required SmolVLA installed-code/module/config discovery passes without an unresolved software dependency conflict;
- the 6 GB capability classification is recorded without claiming unperformed model load, inference, or training; and
- no P0-005 software/runtime blocker remains.

This means the software runtime is ready for later gated work. It does **not** mean local SmolVLA fine-tuning fits in 6 GB and does not authorize `TASK-W1-001`.

### `CONDITIONAL_RUNTIME_READY`

Use only when:

- the isolated environment is reproducible;
- PyTorch CUDA tensor execution and core LeRobot imports pass;
- limited SmolVLA installed-code discovery is usable;
- one or more non-core runtime constraints remain, such as an optional dependency/config surface, explicitly version-bounded workaround, or 6 GB restriction;
- each constraint has an exact allowed activity, prohibited activity, owner, and resolution trigger; and
- proceeding with later readiness remediation would not require fabricated evidence or unsafe behavior.

This decision authorizes no physical, dataset, inference, training, or `TASK-W1-001` work.

### `RUNTIME_BLOCKED`

Use when any core runtime condition fails, including:

- a safe project-local `uv` environment cannot be established;
- no defensible compatible Python/LeRobot/PyTorch version set can be selected;
- PyTorch cannot import or actual CUDA tensor execution fails;
- pinned LeRobot core imports fail;
- SmolVLA required installed-code/module/config discovery is blocked by an unresolved dependency incompatibility; or
- evidence is insufficient to distinguish a real runtime from input assumptions.

Do not substitute CPU-only success, `nvidia-smi`, a system-Python install, a mocked import, or an unmeasured remote host for a blocked runtime.

### 13.1 Authorization invariant

For all three decisions:

```text
TASK-W1-001 authorized = false
TASK-P0-004R re-gate required = true
```

Only a later P0-004R review, after the other readiness blockers are resolved, may change the VLA implementation authorization.

---

## 14. Recommended Commit

After implementation, all required outputs, and validation are complete:

```text
chore(vla): enable and verify isolated CUDA runtime
```

Do not combine P0-006, P0-007, P0-004R, Dataset V1, training, or integration work with this commit. Do not commit unless explicitly requested.

---

## 15. Codex Execution Prompt

```text
Implement TASK-P0-005 only.

First read:
- AGENTS.md
- all files under context/
- tasks/TASK-P0-005.md
- docs/architecture/system_architecture_v1.md
- docs/contracts/contract_plan.md
- relevant ADRs, especially ADR-004
- docs/vla/vla_readiness_v1.md
- results/phase0/P0-004_vla_readiness.json
- plans/vla_readiness_risks.md
- plans/next_vla_task_after_p0_004.md
- scripts/verify_vla_readiness.py

Before changing files, verify pwd, branch, git status, and recent Git history.

Create only the isolated VLA software runtime and the four required P0-005
artifacts. Use .venv-vla managed by uv. Never mutate system Python. Make an
explicit Python/PyTorch/LeRobot version decision before installation; do not
silently replace the repository's older LeRobot baseline with latest upstream.

Re-measure all supplied NVIDIA/WSL observations. Keep the driver-reported CUDA
compatibility value separate from CUDA Toolkit presence, PyTorch build/runtime,
actual CUDA tensor execution, LeRobot compatibility, and SmolVLA capacity.

Run a bounded synchronized CUDA tensor calculation with a numerical assertion.
Validate pinned LeRobot imports and discover SmolVLA installed modules/config
without downloading weights, running inference, or training. Classify the 6 GB
GPU conservatively and never claim SmolVLA training fits unless directly proven
by separately authorized configuration-specific evidence.

Do not touch manipulator/device I/O, camera, physical teleoperation, Dataset V1,
model loading, inference, fine-tuning, evaluation, VLA Skill Server, ROS, Agent
integration, training-budget approval, P0-006, P0-007, P0-004R, or W1-001.

Finish with exactly one runtime decision:
RUNTIME_READY, CONDITIONAL_RUNTIME_READY, or RUNTIME_BLOCKED.

For every decision, keep TASK-W1-001 unauthorized and require the later P0-004R
re-gate after the remaining readiness blockers are resolved. Run the validation
plan, report EC-01 through EC-18, do not stage or commit, and do not start the
next task.
```
