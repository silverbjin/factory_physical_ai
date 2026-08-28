# Engineering Principles — Factory Physical AI Agent

> Last reviewed: 2026-08-28
> Purpose: design and review standard for all architecture and implementation work.

## 1. Senior engineering objective

The project optimizes for **credible operational engineering**, not maximum feature count.

The default question is:

> What is the smallest implementation that produces strong, measurable evidence of correct architecture, learning, integration, and recovery?

---

## 2. Principle: deterministic core, probabilistic intelligence

LLMs and VLAs are probabilistic components. They must be surrounded by deterministic controls.

Use probabilistic models for capabilities that benefit from semantics/generalization:

- language intent;
- semantic planning;
- visual-language reasoning;
- sensorimotor policy.

Use deterministic software for:

- safety;
- execution permissions;
- schemas;
- timeouts;
- retries;
- idempotency;
- persistence;
- state reconciliation;
- versioning;
- metric calculation.

This separation is a core architecture criterion.

---

## 3. Principle: contract-first integration

Integration failures are expected when Agent, ROS, VLA, and factory services evolve independently.

Before deep integration, define versioned contracts for:

- mission state;
- tool requests/responses;
- skill execution;
- error taxonomy;
- timeout/retryability;
- health/version;
- robot state;
- VLA execution result.

Prefer typed schemas and contract tests.

Do not couple the Agent directly to implementation-specific ROS/VLA internals.

---

## 4. Principle: failure-first design

For every component, define before or with the happy path:

- expected failure modes;
- failure signal;
- timeout;
- retryability;
- recovery action;
- escalation condition;
- evidence/log fields.

A feature without a defined failure policy is incomplete.

---

## 5. Principle: idempotent physical operations

Duplicate API or Agent calls must not cause duplicate physical work.

Every mission/action that can create a side effect should carry identifiers such as:

- `mission_id`;
- `request_id`;
- `idempotency_key`.

On process restart or retry, reconcile state before issuing a new physical action.

---

## 6. Principle: observability is part of the feature

If a system cannot explain why a mission failed, the feature is not production-ready.

A mission trace should make it possible to reconstruct:

- initial goal;
- state snapshot;
- Agent decisions;
- tool/skill calls;
- response/error;
- retry/recovery path;
- human approvals;
- final outcome;
- timing.

Prefer correlation via `mission_id` across services.

---

## 7. Principle: evaluation before optimization

Never optimize a model or Agent based only on anecdotal demos.

First create a repeatable evaluator.

### VLA

Establish a baseline evaluation before Dataset V2.

### Agent

Establish scenario fixtures and metric definitions before trying to improve prompt/framework behavior.

### Runtime

Establish health/latency/recovery metrics before long Soak runs.

---

## 8. Principle: failure-driven data engineering

For VLA, more episodes are not automatically better.

Use:

```text
Evaluation
-> Failure Taxonomy
-> Hypothesis
-> Targeted Data Collection
-> Retrain
-> Regression Evaluation
```

Prefer deliberate coverage of difficult variations to indiscriminate dataset growth.

---

## 9. Principle: model and dataset traceability

Every trained model artifact must be traceable to:

- dataset version/manifest;
- training configuration;
- code version;
- environment/model dependency versions;
- evaluation run.

A model file without provenance is not portfolio-grade evidence.

---

## 10. Principle: bounded autonomy

The Agent must operate inside explicit limits:

- maximum reasoning/tool steps;
- per-tool timeout;
- retry count/budget;
- allowed tools;
- allowed state transitions;
- safety gates;
- human approval points.

Do not equate autonomy with unbounded behavior.

---

## 11. Principle: human-in-the-loop for uncertainty and risk

Escalation is a correct outcome when the system lacks sufficient confidence/state to proceed safely.

HITL should be considered for:

- safety-sensitive missions;
- persistent perception mismatch;
- ambiguous inventory state;
- repeated VLA failure;
- unhealthy robot resources;
- policy-violating requests.

Track intervention rate as an operational metric.

---

## 12. Principle: simulation-first, hardware-evidence second

Use simulation/mocks to establish deterministic software correctness and failure coverage rapidly.

Use physical hardware where it provides unique evidence:

- VLA demonstrations;
- real camera/manipulator observations;
- real timing/interface constraints;
- selected E2E demonstrations.

Do not block core Agent production engineering on unnecessary hardware integration.

---

## 13. Principle: production-like, not fake-production

It is acceptable that the project is a prototype.

It is not acceptable to imply real production scale without evidence.

Use terms accurately:

- `production-oriented architecture`;
- `production-like validation`;
- `simulated/mocked factory API`;
- `24-hour soak in prototype environment`.

Avoid unsupported terms such as `production-proven` or `at-scale deployment`.

---

## 14. Principle: explicit Exit Criteria

Each task must have objective completion criteria.

Bad:

> Agent persistence implemented.

Good:

> During an in-progress mission, terminate the Agent process, restart it, restore the latest durable checkpoint, and resume/reconcile without duplicate tool execution. Automated integration test passes and run evidence is stored.

---

## 15. Principle: measured portfolio evidence

Every portfolio claim should map to a file/run.

Examples:

```text
Claim: VLA orientation success improved.
Evidence: results/vla/exp001 + exp002 + comparison CSV.

Claim: Agent handles API timeout.
Evidence: agent benchmark case + Chaos CH-01 trace.

Claim: restart recovery works.
Evidence: CH-03 structured run + integration test.
```

---

## 16. Principle: keep the known technology thin

Known ROS/Nav2/Gazebo capabilities should be implemented only to the level required for reliable integration.

Project schedule should not be consumed by:

- custom navigation tuning;
- simulation graphics;
- generic ROS tutorials;
- reimplementing standard robot middleware features.

Use saved time to deepen Agent/VLA reliability and evaluation.

---

## 17. Principle: architecture decisions are reversible where possible

Early choices should keep migration cost visible.

For every major ADR, document:

- selected option;
- alternatives;
- reason;
- trade-off;
- review trigger;
- migration/rollback consideration.

Examples:

- Agent framework;
- VLA model;
- database;
- observability stack;
- simulator;
- manipulator/teleop stack.

---

## 18. Principle: security and secrets hygiene

Never commit:

- LLM API keys;
- Hugging Face tokens;
- cloud credentials;
- private endpoints;
- personal/proprietary factory data.

Use `.env.example`, secret injection, and local configuration.

Logs should avoid sensitive prompt/data capture unless necessary and intentionally configured.

---

## 19. Principle: reproducible commands

Every important workflow should become a documented command or script:

- environment verification;
- dataset validation;
- training;
- VLA evaluation;
- Agent benchmark;
- Chaos injection;
- Soak runner;
- portfolio metric export.

Prefer repeatability over manual screenshots.

---

## 20. Review checklist

Before accepting a task, ask:

- Is the responsibility boundary correct?
- Is there an explicit contract?
- Is the failure behavior defined?
- Is execution bounded/idempotent?
- Is it observable?
- Is it testable?
- Is it measurable?
- Is provenance/version captured?
- Is it aligned to the JD/business story?
- Did we avoid unnecessary scope?
