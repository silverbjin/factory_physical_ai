# TASK-P0-001 — Phase 0 Technical Validation and Development Environment Freeze

> Phase: 0 — Foundation
> Task type: architecture + technical validation + environment freeze
> Priority: P0
> Owner: Lead Engineer / Codex implementation partner
> Application feature code: **NOT ALLOWED in this task**

## 1. Goal

Create a verified, reproducible `Physical AI Project Development Environment v1.0` and freeze the initial architecture choices required to start the Day-10 MVP and VLA/Agent workstreams.

The task must convert currently open technology choices into:

1. selected options or explicitly unresolved decisions;
2. evidence-backed compatibility checks;
3. Architecture Decision Records;
4. a development/robot runtime topology;
5. a reproducible environment verification script;
6. an executable next-task backlog recommendation.

This task is not complete when a technology list is written. The chosen stack must have enough proof-of-life evidence to justify implementation.

---

## 2. Why this task exists

The project combines technologies with different hardware/runtime constraints:

- LeRobot / VLA training and inference;
- manipulator teleoperation/data collection;
- ROS 2 navigation/execution;
- LLM Agent orchestration;
- WMS/Fleet/PHM services;
- database/persistence;
- tracing/metrics;
- Docker/service deployment.

If these choices are made ad hoc during later tasks, integration risk and rework will consume the six-week schedule.

Phase 0 must therefore establish stable boundaries and verify the riskiest assumptions first.

---

## 3. Required inputs

Read completely before starting:

- `/AGENTS.md`
- `/context/project_context.md`
- `/context/business_context.md`
- `/context/jd_gap_analysis.md`
- `/context/engineering_principles.md`
- `/context/portfolio_goals.md`

Also inspect:

- current repository structure;
- current host/WSL/Linux environment;
- available GPU and drivers;
- connected/available robot hardware only through non-destructive inspection;
- current Git state.

Do not assume hardware or dependency versions that cannot be verified.

---

## 4. Decisions that Phase 0 must address

Evaluate and either **ACCEPT**, **REJECT**, or **DEFER with a clear validation trigger** for each area.

### D1. Manipulator

Choose the manipulator strategy for direct VLA demonstration/fine-tuning.

Evaluate:

- actual hardware availability;
- LeRobot compatibility or adapter effort;
- teleoperation stability;
- camera/observation integration;
- action representation;
- ROS 2 integration requirement;
- safety/limits;
- dataset collection speed.

### D2. AMR

Choose MVP and final AMR strategy.

Candidates may include:

- simulation-only AMR for MVP;
- existing AMR/myAGV/TurtleBot platform if available;
- a minimal ROS 2 Nav2 simulation.

Do not spend Phase 0 tuning navigation.

### D3. Simulation environment

Select the minimum simulator(s) needed for:

- integration;
- robot execution dry-run;
- failure scenarios;
- optional policy work.

Prefer reuse and speed over visual fidelity.

### D4. VLA / LeRobot stack

Validate:

- LeRobot installation path;
- chosen Python/runtime version;
- selected initial VLA model candidate, defaulting to SmolVLA only if compatible;
- minimum GPU/VRAM path;
- training vs inference location;
- dataset storage/version approach;
- teleoperation and recording approach.

### D5. Camera / observation configuration

Define:

- number of cameras for V1;
- expected resolution/FPS;
- calibration requirements;
- timestamps/synchronization expectations;
- whether camera data enters ROS 2, LeRobot directly, or via an adapter.

Keep V1 minimal.

### D6. LLM model/provider strategy

Select an initial Agent model strategy.

Evaluate:

- API-hosted vs local;
- structured tool calling;
- latency;
- cost/token observability;
- model replaceability;
- test/mocking strategy;
- secrets management.

The architecture must not tightly couple the Agent state machine to one vendor.

### D7. Agent orchestration framework

Evaluate at minimum:

- LangGraph candidate;
- a small custom deterministic state machine + LLM boundary as alternative.

Selection criteria:

- durable state/persistence;
- resume/recovery;
- HITL;
- structured tools;
- testability;
- observability;
- complexity within six weeks.

Do not select based on popularity alone.

### D8. Persistence/database

Choose MVP and target persistence approach for:

- mission state;
- idempotency;
- evaluation metadata;
- trace references.

Consider SQLite/PostgreSQL/Redis only as justified.

### D9. Observability

Define the minimum stack for:

- Agent decision/tool trace;
- mission correlation;
- service/runtime metrics;
- model/VLA latency;
- Chaos/Soak evidence.

The stack may combine Agent-specific tracing and generic metrics/logging, but avoid excessive infrastructure.

### D10. Docker/service topology

Define what should be containerized during MVP and later.

Do not containerize hardware access merely for purity if it increases risk without portfolio value.

### D11. ROS 2 architecture

Define minimum nodes/adapters and namespaces for:

- AMR navigation;
- manipulator execution if ROS 2 is used there;
- perception/verification as needed;
- Agent execution adapter;
- health/diagnostics.

### D12. Development PC vs robot PC role split

Explicitly define where these responsibilities run:

- training;
- Agent;
- DB;
- simulator;
- ROS 2 master-equivalent/discovery domain configuration as relevant;
- robot drivers;
- VLA inference;
- telemetry.

Network boundaries must be explicit.

### D13. Repository structure/tooling

Freeze the initial layout and development tooling for:

- Python package management;
- test runner;
- formatter/linter;
- typing;
- pre-commit/CI if appropriate;
- config management;
- result artifacts.

Do not create application features.

---

## 5. Required outputs

Create or update only planning/foundation files required by this task.

### 5.1 Environment manifest

Create:

`docs/environment/development_environment_v1.md`

It must contain:

- host OS / WSL status;
- Linux distribution/version;
- CPU/RAM;
- GPU/VRAM;
- NVIDIA driver / CUDA-related facts that are actually verified;
- Python;
- Node/Codex if relevant to development workflow;
- ROS 2 version;
- Docker version;
- chosen VLA/Agent package strategy;
- physical devices available;
- network topology;
- known constraints.

### 5.2 System architecture draft

Create:

`docs/architecture/system_architecture_v1.md`

Include:

- context diagram;
- runtime components;
- responsibility boundaries;
- development PC / robot PC placement;
- data/control flow;
- which boundaries are mocks in MVP;
- which boundaries are intended for final integration.

### 5.3 ADRs

Create directory:

`docs/architecture/adr/`

Create at minimum:

- `ADR-001-manipulator.md`
- `ADR-002-amr.md`
- `ADR-003-simulation.md`
- `ADR-004-vla-stack.md`
- `ADR-005-camera-observation.md`
- `ADR-006-llm-strategy.md`
- `ADR-007-agent-framework.md`
- `ADR-008-persistence.md`
- `ADR-009-observability.md`
- `ADR-010-deployment-topology.md`

Each ADR must contain:

```text
Status
Context
Decision
Alternatives
Rationale
Trade-offs
MVP usage
Final usage
Validation evidence
Review trigger
```

A decision may remain `Proposed` if validation is genuinely incomplete; do not fake acceptance.

### 5.4 Interface boundary plan

Create:

`docs/contracts/contract_plan.md`

Do not implement full APIs yet.

Define planned contracts for:

- Mission;
- Factory Tool;
- Robot/Fleet State;
- PHM State;
- Navigation Skill;
- VLA Skill;
- Verification Result.

List mandatory cross-cutting fields such as IDs, timestamps, versions, errors, retryability, and timeouts.

### 5.5 Environment verification script

Create:

`scripts/verify_environment.sh`

Requirements:

- non-destructive;
- safe to rerun;
- verifies tool/version availability;
- does not move robots;
- does not train a model;
- does not download large models without explicit user authorization;
- outputs a readable summary;
- returns non-zero only for checks categorized as required.

Also create a structured result writer if justified, e.g.:

`results/phase0/environment_verification.json`

Do not commit machine-specific secrets or personal paths unnecessarily.

### 5.6 Phase 0 risk list

Create:

`plans/phase0_risks.md`

At minimum evaluate:

- teleoperation stability;
- VLA hardware compatibility;
- GPU/VRAM/training feasibility;
- Agent framework complexity;
- ROS-VLA interface coupling;
- schedule risk from known ROS/simulation work;
- Soak/validation schedule risk.

### 5.7 Next executable tasks

Create:

`plans/next_tasks_after_phase0.md`

Recommend only the next focused tasks, in order.

The first tasks should normally establish:

1. repository/tooling baseline;
2. VLA proof-of-life / teleop vertical slice;
3. Day-10 MVP Agent/tool vertical slice;

Do not implement them in TASK-P0-001.

---

## 6. Validation actions required in Phase 0

Perform safe, lightweight checks rather than full application implementation.

Examples of acceptable validation:

- command/version checks;
- Python import tests;
- Docker smoke test;
- ROS 2 basic environment check;
- GPU detection;
- dependency-resolution feasibility;
- Codex/Git tooling check;
- camera enumeration without changing settings destructively;
- robot device enumeration without commanding movement;
- LeRobot package/import feasibility;
- framework import/minimal no-side-effect test;
- architecture compatibility review.

Examples of out-of-scope validation:

- collecting the complete VLA Dataset V1;
- full VLA fine-tuning;
- implementing the Factory Agent;
- building Nav2 maps;
- moving physical robots to prove integration;
- implementing production APIs.

---

## 7. Files allowed to change

Allowed:

- `docs/environment/**`
- `docs/architecture/**`
- `docs/contracts/contract_plan.md`
- `plans/phase0_risks.md`
- `plans/next_tasks_after_phase0.md`
- `scripts/verify_environment.sh`
- `results/phase0/**`
- development config files only when necessary to validate/freeze tooling
- `.gitignore` if needed for secrets/cache/large artifacts
- this task file only for correcting a factual error with explicit explanation

Do not change the durable context files unless a verified contradiction is found. If one is found, report it first.

---

## 8. Files / areas that must not be implemented in this task

Do not create production application logic under:

- `src/agent/`
- `src/vla/`
- `src/robot/`
- `src/factory/`

Do not create a front-end.

Do not collect a real training dataset.

Do not begin fine-tuning.

Do not implement E2E robot motion.

---

## 9. Exit Criteria

TASK-P0-001 is **PASS** only when all required criteria below are satisfied.

### EC-01 Context understood

Codex has reviewed all required context and reports no unresolved contradiction between project, business, JD gap, engineering principles, and portfolio goals.

If a contradiction exists, task status is BLOCKED until explicitly resolved.

### EC-02 Environment manifest created

`development_environment_v1.md` contains verified facts and labels unverified items clearly.

### EC-03 Critical stack decisions documented

All D1-D13 areas are addressed with accepted/proposed/deferred status and rationale.

### EC-04 Risky assumptions validated

At least the highest-risk feasible assumptions receive lightweight proof-of-life evidence, especially:

- GPU/runtime feasibility;
- LeRobot/VLA stack feasibility;
- robot/teleop feasibility where hardware is available;
- Agent framework/persistence feasibility;
- ROS 2 environment feasibility.

### EC-05 Architecture boundary frozen enough for next tasks

The architecture clearly separates:

- LLM semantic reasoning;
- deterministic execution/safety;
- VLA skill;
- ROS/factory integration.

### EC-06 Contract plan exists

Major component boundaries and cross-cutting request/result fields are documented.

### EC-07 Environment verification is reproducible

`scripts/verify_environment.sh` runs safely and provides useful PASS/WARN/FAIL output.

### EC-08 No application scope creep

No production Agent, VLA, navigation, or UI feature is implemented.

### EC-09 Risks and next tasks documented

Phase 0 risks and next tasks exist and are prioritized against the Day-10 MVP / six-week schedule.

### EC-10 Evidence stored

Command outputs or structured verification evidence required to justify key decisions are saved or referenced without including secrets.

---

## 10. Completion report format

When finished, report exactly these sections:

### Decisions

Table:

| Area | Decision | Status | Key reason | Review trigger |
|---|---|---|---|---|

### Environment verification

- commands/checks run;
- PASS/WARN/FAIL;
- blocking issues.

### Files created/changed

List paths.

### Exit Criteria

List EC-01 through EC-10 as `PASS`, `FAIL`, or `BLOCKED` with one-line evidence.

### Top risks

Top 5 only, ordered by project impact.

### Recommended next task

Recommend one next task only. Do not start it.

---

## 11. Suggested first Codex prompt for this task

```text
Implement TASK-P0-001 only.

First read:
- AGENTS.md
- all files under context/
- TASK-P0-001.md

Before changing files:
1. inspect the repository and git status;
2. inspect the local development environment non-destructively;
3. summarize the architecture decisions that must be made;
4. identify the highest-risk assumptions to validate.

Then execute the task exactly within its allowed scope.
Do not implement application features.
Do not move physical robots.
Do not download large models or datasets without explicit approval.
Do not invent unverified environment facts or benchmark results.

At the end, report Decisions, Environment verification, Files created/changed,
Exit Criteria EC-01~EC-10, Top risks, and one Recommended next task.
```
