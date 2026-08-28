# Project Context — Factory Physical AI Agent

> Last reviewed: 2026-08-28
> Status: authoritative project context for planning and implementation

## 1. Project name

**Factory Physical AI Agent**

Portfolio-facing alternative name:

**SDF Physical AI Supervisor**

Subtitle:

**LLM Agent + VLA 기반 자동차 제조공장 자율 부품공급 및 장애복구 시스템**

---

## 2. Project purpose

This project is designed to prove rapid senior-level acquisition and operationalization of two capabilities:

1. **production-oriented LLM Agent engineering**;
2. **direct VLA dataset construction, fine-tuning, evaluation, and improvement**.

The project deliberately reuses existing robot/system engineering competence where possible rather than spending the schedule re-proving known ROS/navigation/simulation skills.

The target signal to an employer is not:

> “I tried an Agent framework and a VLA model.”

It is:

> “I can identify a competency gap, learn the technology quickly, establish reliable interfaces and evaluation, integrate it with a real robot software stack, and drive it from POC toward production readiness.”

---

## 3. Primary business scenario

The project models a reduced automotive manufacturing **line-side parts logistics** workflow.

Canonical user mission:

> `Supply Brake ECU Type-B to Line B.`

Nominal high-level workflow:

```text
Operator goal
  -> Factory AI Agent
  -> production/inventory state query
  -> robot/fleet/health query
  -> mission planning
  -> AMR navigation
  -> part verification
  -> VLA manipulation
  -> delivery/placement
  -> result verification
  -> mission completion
```

The scenario should remain small enough for a six-week project but realistic enough to expose integration and operational failure modes.

---

## 4. Core architecture concept

```text
                         Operator
                            |
                     Natural-language goal
                            |
                            v
                  +--------------------+
                  | Factory AI Agent   |
                  | semantic planning  |
                  +---------+----------+
                            |
                     structured tools
       +--------------------+---------------------+
       |                    |                     |
       v                    v                     v
      WMS               Fleet/Robot              PHM
       |                    |                     |
       +--------------------+---------------------+
                            |
                      World State
                            |
                            v
                    Mission Executor
                            |
                +-----------+-----------+
                |                       |
                v                       v
          Navigation Skill         VLA Skill Server
             / ROS 2                 fine-tuned VLA
                |                       |
                v                       v
               AMR                  Manipulator
                \                       /
                 +----------+----------+
                            |
                      Verification
                            |
                            v
                       Mission Result
                            |
                 traces / metrics / data
                            |
                            v
                       Evaluation
```

---

## 5. Responsibility boundaries

### LLM Agent

Responsible for:

- interpreting the mission goal;
- semantic task decomposition;
- selecting approved tools/skills;
- reasoning over structured observations;
- selecting an approved recovery strategy;
- replanning.

Not responsible for raw actuator control.

### Deterministic runtime

Responsible for:

- contract/schema validation;
- safety policies;
- retry/timeout/backoff;
- idempotency;
- persistent mission state;
- execution authorization;
- result verification rules;
- metrics.

### VLA

Responsible for the manipulation sensorimotor policy through a controlled skill contract.

### ROS 2

Responsible for robot/sensor integration and execution.

---

## 6. Mandatory failure scenarios

The final system must exercise representative failures rather than demonstrate only a happy path.

### F1. Inventory/part mismatch

Expected part and detected part differ.

Expected recovery:

```text
stop manipulation
-> verify mismatch
-> query inventory again
-> update source location
-> replan mission
```

### F2. VLA manipulation failure

Pick or place fails.

Expected policy options:

- bounded retry;
- alternative skill/pose if explicitly supported;
- human intervention/escalation.

### F3. Robot health/PHM warning

Assigned robot is not healthy enough for the mission.

Expected recovery:

```text
remove robot from eligible pool
-> select alternative robot
-> preserve mission idempotency
-> continue/replan
```

### F4. Navigation blocked/unavailable

Expected handling:

- wait within policy;
- reroute;
- assign another robot;
- escalate if no safe route exists.

### F5. Factory API failure

Examples:

- WMS timeout;
- malformed response;
- temporary dependency outage.

Expected handling:

- schema validation;
- bounded retry/backoff;
- fallback or human escalation.

### F6. Agent/runtime restart

Expected behavior:

- restore checkpoint;
- avoid duplicate physical execution;
- resume or safely reconcile mission state.

---

## 7. VLA learning loop

The VLA portion must include an actual iterative learning lifecycle:

```text
Teleoperation
-> demonstration recording
-> Dataset V1 validation
-> fine-tuning
-> baseline evaluation
-> failure taxonomy
-> targeted Dataset V2
-> retraining
-> regression/generalization evaluation
-> skill deployment
```

Initial guidance:

- start with one manipulation task and one VLA family;
- prefer a LeRobot-compatible workflow;
- collect enough task variation to analyze generalization;
- do not optimize for maximum model breadth.

Candidate initial model: **SmolVLA**, subject to Phase 0 validation and hardware/GPU compatibility.

---

## 8. Agent lifecycle

The Agent portion must progress beyond a chat/tool-call demo.

Required lifecycle:

```text
Mission input
-> validated mission state
-> structured planning/tool use
-> persistent state transitions
-> observation
-> success verification or failure classification
-> recovery/replan
-> completion/cancellation
-> trace/evaluation
```

Production-oriented features to prove:

- persistence;
- timeout;
- retry/backoff;
- idempotency;
- Human-in-the-loop;
- tracing/observability;
- evaluation;
- process restart recovery;
- version/rollback awareness.

---

## 9. Evaluation targets

Targets are engineering goals, not claimed results.

### VLA metrics

- Task Success Rate;
- Pick Success Rate;
- Place Success Rate;
- Completion Time;
- Intervention Rate;
- Inference Latency;
- success by variation category.

Variation categories should include a practical subset of:

- position;
- orientation;
- distractor;
- lighting;
- camera view;
- language instruction.

### Agent benchmark

Target benchmark set: **100 missions**.

Recommended distribution:

| Scenario | Cases |
|---|---:|
| Normal | 30 |
| Inventory mismatch | 15 |
| Robot unavailable | 10 |
| Navigation failure | 10 |
| Manipulation failure | 15 |
| PHM warning | 10 |
| API timeout | 5 |
| Unsafe request | 5 |

Metrics:

- Mission Success Rate;
- Tool Selection Accuracy;
- Invalid Tool Call Rate;
- Recovery Success Rate;
- Human Intervention Rate;
- P95 Latency;
- token/cost metrics when applicable.

### Reliability validation

- deterministic regression suite;
- fault injection/Chaos tests;
- 24h soak target;
- 72h soak target if schedule allows;
- 7-day run is optional, not required for success.

---

## 10. Schedule strategy

Nominal total duration: **6 weeks**, approximately **20 hours/week**.

A portfolio-visible MVP should exist by approximately Day 10.

### Day-10 MVP

Minimum demonstrable chain:

```text
natural-language mission
-> Factory Agent
-> WMS/factory tool
-> robot/VLA skill abstraction
-> one injected failure
-> recovery/replan
-> mission result
```

The MVP may use mocks/simulation at boundaries as long as they are explicitly labeled.

### Six-week progression

- Week 1: VLA vertical slice;
- Week 2: VLA dataset iteration + skill service;
- Week 3: Factory Agent vertical slice;
- Week 4: Agent production engineering + 100-mission evaluator;
- Week 5: Agent-AMR-VLA integration + failure recovery;
- Week 6: regression, Chaos, Soak, production-readiness evidence.

---

## 11. Scope exclusions / non-goals

Unless they become necessary to an Exit Criterion, do not prioritize:

- multi-agent architecture;
- a photorealistic factory simulation;
- advanced fleet optimization research;
- custom SLAM/Nav2 research;
- a new RL benchmark unrelated to the VLA/Agent gaps;
- many VLA model comparisons;
- a full production MES/WMS;
- sophisticated front-end design;
- direct LLM motion generation.

---

## 12. Repository-level evidence strategy

Measured outputs should be stored as machine-readable artifacts.

Recommended target structure:

```text
results/
  vla/
    exp001/
    exp002/
    summary.csv
  agent/
    benchmark_v001/
    summary.csv
  chaos/
    runs/
    summary.csv
  soak/
    soak_24h/
    soak_72h/
  portfolio/
    vla_v1_v2.csv
    agent_100_missions.csv
    chaos_summary.csv
    soak_summary.csv
    improvement_cases.json
```

Every portfolio number must be traceable to a measured result or explicitly labeled synthetic fixture.

---

## 13. Definition of final project success

The project is successful when it can credibly demonstrate all of the following:

1. a VLA was fine-tuned on a directly constructed/versioned demonstration dataset;
2. VLA failures were classified and used to improve a later dataset/model version;
3. a stateful Factory Agent was evaluated over a repeatable mission benchmark;
4. LLM decisions were separated from deterministic execution/safety policies;
5. Agent, VLA, ROS/factory tools were integrated through explicit contracts;
6. representative failures were detected and recovered or safely escalated;
7. production-like regression/Chaos/Soak evidence was generated;
8. the final portfolio communicates business relevance, measured improvements, limitations, and engineering decisions without fabricated claims.
