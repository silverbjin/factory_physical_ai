# Factory Physical AI Agent — Codex Engineering Instructions

> Scope: repository root and all descendant directories unless a more specific `AGENTS.md` or `AGENTS.override.md` exists.
> Last reviewed: 2026-08-28

## 1. Mission

Build a production-oriented Physical AI prototype for automotive manufacturing line-side parts logistics.

The system must demonstrate that a senior robot/software engineer can rapidly acquire and operationalize two relatively newer capabilities:

1. production-oriented LLM Agent engineering;
2. direct VLA dataset construction, fine-tuning, evaluation, and iteration.

The implementation must remain aligned with Hyundai AutoEver's manufacturing/robot intelligence direction: Software-Defined Factory (SDF), heterogeneous robot integration, manufacturing/logistics system integration, AI Agent, Digital Twin, Robot Integrated Monitoring, and PHM.

This is not a robotics toy demo. It is a senior-level system-engineering portfolio project.

---

## 2. Authority and source of truth

Use this precedence when instructions conflict:

1. explicit user instruction for the current task;
2. the assigned `tasks/TASK-*.md` file;
3. a more specific nested `AGENTS.override.md` / `AGENTS.md`;
4. this root `AGENTS.md`;
5. `context/*.md`;
6. architecture/ADR documents already accepted in `docs/`;
7. implementation code and tests.

Do not silently reinterpret an accepted architecture decision. If a task requires changing one, stop the implementation of that design change and surface it as an ADR update/review item.

Repository artifacts have distinct roles:

- `AGENTS.md`: agent operating rules.
- `context/`: durable project/business/JD context.
- `plans/`: implementation and validation plans.
- `tasks/`: executable units of work with Exit Criteria.
- `docs/architecture/`: accepted architecture and ADRs.
- `docs/contracts/`: stable component/interface contracts.
- `src/`: application code.
- `tests/`: automated verification.
- `data/`: datasets or dataset manifests. Large data should not be committed unless explicitly required.
- `results/`: measured machine-readable evidence.
- external Excel workbook: project-management/dashboard layer only; it is not the implementation source of truth.

Never fabricate missing context. Mark unresolved items explicitly as `TBD`, `ASSUMPTION`, or `BLOCKED`.

---

## 3. Required reading before work

For every task:

1. Read this file.
2. Read the assigned task file completely.
3. Read only the relevant documents under `context/`, `plans/`, `docs/architecture/`, and `docs/contracts/`.
4. Inspect the current code and tests before modifying them.
5. Check `git status` and do not overwrite unrelated user changes.

For Phase 0 or architecture tasks, read all files under `context/`.

For implementation tasks, avoid loading unrelated context merely to increase context size.

---

## 4. Product boundary

### 4.1 LLM Agent responsibility

The LLM Agent may decide:

- user/mission intent interpretation;
- semantic task decomposition;
- selection among approved tools/skills;
- reasoning over structured factory state;
- recovery strategy selection from approved policies;
- replanning after observations or failures;
- whether human approval is required, according to configured rules.

### 4.2 Deterministic software responsibility

Deterministic code must own:

- schema validation;
- safety constraints and policy enforcement;
- timeout and retry budgets;
- exponential backoff;
- idempotency;
- duplicate mission suppression;
- authorization boundaries;
- state persistence/checkpointing;
- robot command execution;
- lifecycle and health checks;
- version selection and rollback;
- metric calculation.

### 4.3 VLA responsibility

VLA is a sensorimotor skill/policy layer. It may consume permitted observations such as:

- camera observations;
- robot state;
- task/language instruction;
- optional scene/task metadata defined by the contract.

It produces manipulation actions through a controlled skill interface.

### 4.4 ROS 2 responsibility

ROS 2 is the physical execution/integration layer for:

- robot state;
- navigation;
- sensors;
- manipulation execution;
- lifecycle/health;
- simulator or physical robot adapters.

### 4.5 Forbidden shortcuts

The LLM must never directly:

- output raw motor commands for execution;
- construct unrestricted ROS shell commands;
- generate and execute joint trajectories without deterministic validation;
- bypass safety checks;
- invent WMS/Fleet/PHM state;
- make unbounded retry decisions;
- decide that an unverified physical action succeeded.

Preferred flow:

```text
LLM semantic decision
  -> structured tool/skill call
  -> schema validation
  -> deterministic policy validation
  -> controlled execution
  -> structured observation/result
  -> agent re-evaluation
```

---

## 5. Business scope guardrails

The primary scenario is automotive manufacturing `line-side parts logistics`.

Canonical mission example:

> Supply Brake ECU Type-B to Line B.

The prototype should prioritize business-relevant interactions among:

- WMS/inventory;
- robot/fleet state;
- AMR/navigation skill;
- VLA manipulation skill;
- vision/verification;
- PHM/robot-health signal;
- mission orchestration;
- failure recovery;
- observability and operational evidence.

Do not pivot the project into a generic household robot, humanoid entertainment demo, pure RL benchmark, or standalone chatbot.

---

## 6. Scope priorities

Allocate engineering attention in approximately this order:

1. LLM Agent production engineering;
2. VLA dataset/fine-tuning/evaluation;
3. production-like validation and evidence;
4. Agent-VLA-ROS integration;
5. existing robot/navigation functionality only as needed.

Avoid spending significant time on:

- simulator visual polish;
- custom Nav2 optimization unless it blocks the mission;
- building a sophisticated front-end before reliability is proven;
- comparing many VLA models before one full learning loop works;
- multi-agent architecture before the single orchestrator is stable;
- unnecessary infrastructure that does not support an Exit Criterion.

Prefer the smallest architecture that proves the target competency.

---

## 7. Simulation-first and physical hardware safety

Default to simulation or dry-run mode unless the task explicitly authorizes physical hardware.

Before moving a physical robot, the implementation must have:

- an explicit operator-controlled start step;
- a stop/E-stop path appropriate to the platform;
- motion bounds or workspace limits;
- bounded speed/force settings where available;
- validated command schema;
- a documented expected behavior;
- no uncontrolled LLM-to-actuator path.

Never execute destructive or unsafe hardware operations merely to satisfy a test.

If physical safety cannot be verified, stop and report the condition rather than guessing.

---

## 8. Task execution protocol

For each `TASK-*`:

### Before editing

1. Summarize the task goal in one or two sentences.
2. Identify relevant files and contracts.
3. State a concise implementation plan.
4. Identify any assumption that affects correctness.
5. Confirm what is explicitly out of scope.

### During implementation

- Modify only files needed by the task.
- Preserve established interfaces unless the task authorizes contract changes.
- Prefer small, reviewable patches.
- Add typing, validation, structured errors, and logging where the task touches boundaries.
- Do not hide or swallow exceptions without an explicit policy.
- Keep external side effects behind interfaces so they can be mocked/tested.

### Before declaring completion

1. Run the task-specific tests.
2. Run affected regression tests.
3. Run lint/type/static checks defined by the repository.
4. Verify every Exit Criterion explicitly.
5. Generate required evidence under `results/` or `docs/`.
6. Report remaining warnings/limitations.
7. Do not begin the next task unless explicitly instructed.

A task is not complete because code compiles or a demo worked once.

---

## 9. Test and evidence policy

### 9.1 No invented results

Never fabricate:

- VLA success rates;
- Agent benchmark results;
- latency;
- token/cost metrics;
- recovery rates;
- Chaos results;
- Soak-test results;
- hardware execution outcomes.

If no real run is possible, use fixtures marked clearly as `synthetic`, `mock`, or `test_fixture`.

Synthetic values must never be exported as measured portfolio evidence.

### 9.2 Machine-readable evidence

Prefer machine-readable outputs:

- JSON / JSONL for mission traces and run metadata;
- CSV for experiment summaries;
- Markdown for human-readable reports generated from measured data.

Each experiment/run should record where applicable:

- run/experiment ID;
- timestamp;
- git commit SHA;
- config/model/dataset version;
- environment version;
- seed when relevant;
- inputs/scenario;
- measured outputs;
- pass/fail state;
- failure category;
- artifact paths.

### 9.3 Regression principle

Do not weaken a failing test simply to make the build green.

If a requirement changed, update the requirement/contract/ADR first, then update tests with justification.

---

## 10. Agent engineering requirements

Production-oriented Agent tasks should consider, when applicable:

- durable state/persistence;
- deterministic state transitions;
- structured tool calls;
- retry/backoff/timeout;
- idempotency;
- human-in-the-loop;
- safe cancellation;
- observability/tracing;
- offline evaluation;
- regression suite;
- process restart recovery;
- dependency failure;
- versioning/rollback;
- token/latency budgets.

An LLM response by itself is not a production feature.

---

## 11. VLA engineering requirements

VLA work should follow a complete measurable learning loop:

```text
Teleoperation / demonstration
  -> dataset recording
  -> dataset validation
  -> dataset versioning
  -> training/fine-tuning
  -> evaluation
  -> failure taxonomy
  -> targeted dataset improvement
  -> retraining
  -> regression evaluation
  -> controlled skill deployment
```

Prioritize data quality and failure-driven dataset iteration over merely increasing episode count.

For every VLA model version, preserve linkage among:

- model version;
- dataset version;
- training config;
- code commit;
- evaluation report;
- known failure distribution.

---

## 12. Interface/contract rules

Use explicit contracts between major components.

Expected component boundaries include:

- Factory Agent <-> Factory Tools;
- Factory Agent <-> Skill Registry;
- Agent/Skill layer <-> ROS 2 execution adapter;
- Agent <-> VLA Skill Server;
- Agent <-> WMS/Fleet/PHM mocks or adapters.

Contracts should include as applicable:

- `mission_id`;
- `request_id`;
- `idempotency_key`;
- `timestamp`;
- schema/version;
- success/error result;
- retryable/non-retryable classification;
- timeout semantics;
- health/version endpoint behavior.

Contract changes require explicit review because they can affect multiple workstreams.

---

## 13. Coding conventions

Until Phase 0 freezes exact tooling:

- Python: use modern typing, structured models, isolated side effects, and testable functions.
- C++: use only where ROS 2/performance/device integration justifies it.
- TypeScript: use only if/when an operator UI or service requires it.
- Prefer configuration files/environment variables over hard-coded deployment values.
- Never commit credentials, API keys, tokens, personal data, or proprietary data.

When Phase 0 defines formatter/linter/type-checker/test commands, update this section or create a more specific nested `AGENTS.md` rather than guessing commands on every task.

---

## 14. Git discipline

Before changes:

```bash
git status
```

Do not delete, reset, or overwrite unrelated user work.

Commits should be task-focused. Recommended pattern:

```text
feat(vla): ...
feat(agent): ...
feat(integration): ...
test(validation): ...
fix(agent): ...
docs(adr): ...
chore(env): ...
```

Do not create or push remote branches unless the user requests it.

---

## 15. Reporting format after each task

End a task with a concise report containing:

### Implemented
- files changed;
- behavior added/changed.

### Validation
- commands/tests run;
- pass/fail results;
- evidence generated.

### Exit Criteria
- each criterion: PASS / FAIL / BLOCKED.

### Remaining issues
- limitations, risks, or assumptions.

### Next task
- only suggest; do not start it without instruction.

---

## 16. Project success test

The repository should ultimately support a defensible story:

> A production-oriented LLM Agent accepts a manufacturing logistics goal, queries structured factory state, orchestrates AMR and a fine-tuned VLA manipulation skill through controlled interfaces, verifies outcomes, recovers from representative failures, and produces measurable evaluation/Chaos/Soak evidence.

If an implementation decision does not materially strengthen this story, question whether it belongs in scope.
