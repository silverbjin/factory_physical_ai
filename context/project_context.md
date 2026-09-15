# Project Context — Factory Physical AI Agent

> Last reviewed: 2026-09-15
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

The accepted Simulation Lane now uses simulation as an engineering validation harness rather than as a research objective. The planned post-gate stack is **ROS 2 Jazzy + Gazebo Harmonic + MuJoCo**: ROS 2 Jazzy provides system integration/orchestration, Gazebo Harmonic provides the authoritative system-level AMR/sensor/navigation simulation, and MuJoCo provides component-level manipulation physics for VLA Skill validation.

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

The scenario should remain small enough for the original six-week product scope plus the explicit Simulation Week A/B risk-reduction extension, while remaining realistic enough to expose integration and operational failure modes.

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

### 4.1 Simulation First execution topology

The post-gate Simulation Lane increases fidelity in controlled layers while preserving the accepted Skill/Verification contracts:

```text
L0 — Deterministic contract/runtime
Mission Executor
  -> deterministic Navigation/VLA/Verification fixtures
  -> lifecycle / timeout / reconciliation / fail-closed semantics

L1-NAV — ROS 2 Jazzy + Gazebo Harmonic
Mission Executor / Navigation Skill
  -> ROS 2 Jazzy
  -> Nav2-facing execution
  -> Gazebo Harmonic AMR / sensor / world simulation

L1-VLA — MuJoCo manipulation physics
VLA Skill
  -> contract-preserving MuJoCo backend
  -> manipulator / object / contact / observation-action physics

L2-SYSTEM — ROS 2 Jazzy + Gazebo Harmonic
Factory mission
  -> Mission Executor
  -> Navigation / VLA / Verification boundaries
  -> one authoritative Gazebo system world
  -> normal system E2E and system-level failures
```

Simulation authority rules:

- Gazebo Harmonic is the authoritative integrated system world for Simulation E2E.
- MuJoCo is an engineering bench for manipulation physics and VLA Skill evidence.
- deterministic fixtures remain the contract/lifecycle regression baseline.
- the current v1 scope does not synchronize Gazebo and MuJoCo as two simultaneous authoritative physics worlds.
- simulator models do not imply selection of myCobot, myAGV, D455, Orin Nano, or any other physical target.
- a simulator backend must remain behind the accepted Skill/Verification contract and must not create a direct actuator contract.

This strategy is intended to reduce sim-to-real and integration risk without turning the project into custom simulator, SLAM, or Nav2 research.

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

**ROS 2 Jazzy** is the planned Simulation Lane middleware baseline.

Responsible for:

- launch/orchestration of ROS-facing simulation components;
- Nav2-facing navigation execution;
- robot/sensor topic, service, action, and TF integration where required;
- Gazebo Harmonic integration through the ROS/Gazebo boundary selected by the relevant Task;
- preserving the accepted project Skill contracts above simulator-specific APIs.

### Gazebo Harmonic

Planned responsibility:

- authoritative integrated Simulation world;
- AMR/navigation/sensor/system-level simulation;
- ROS 2 Jazzy system E2E;
- system-level navigation and sensor failure injection.

Gazebo is not evidence of physical robot readiness.

### MuJoCo

Planned responsibility:

- manipulation-physics engineering backend;
- contact/grasp/object interaction validation;
- VLA observation/action execution experiments behind the accepted VLA Skill boundary;
- manipulation-specific fault scenarios.

MuJoCo is not a second authoritative system world and does not authorize model training or physical motion.

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

The original project-management baseline remains **6 physical/product weeks**, approximately **20 hours/week**, with a portfolio-visible MVP by approximately Day 10.

The current execution plan adds two explicit **Simulation Weeks (A/B)** before the original physical Week-1 lane. This creates an 8-logical-week sequence unless calendar time is compressed; it does not rename or reinterpret the original `TASK-W1-*` through `TASK-W6-*` work.

```text
Simulation Architecture
SIM-C01 -> SIM-001 -> SIM-002 -> SIM-GATE
        ↓ accepted SIM_GO
SIM Week A
ROS 2 Jazzy / Gazebo Harmonic / MuJoCo component foundations
        ↓
SIM Week B
Mission integration / Gazebo system E2E / multi-layer failure / qualification
        ↓
Hardware selection and readiness under separate authority
        ↓
Original Week 1 through Week 6
```

The Simulation Weeks are risk-reduction work. They must not be counted as Dataset V1, fine-tuning, physical teleoperation, or physical E2E evidence.

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

### Original six-week progression

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
- real-time Gazebo↔MuJoCo dual-authority physics co-simulation in v1;
- custom simulator-bridge research beyond the adapters needed by accepted Skill contracts;
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

1. the Simulation Lane produced reproducible deterministic, Gazebo Harmonic system, and MuJoCo manipulation evidence without conflating simulation with physical success;
2. a VLA was fine-tuned on a directly constructed/versioned demonstration dataset;
3. VLA failures were classified and used to improve a later dataset/model version;
4. a stateful Factory Agent was evaluated over a repeatable mission benchmark;
5. LLM decisions were separated from deterministic execution/safety policies;
6. Agent, VLA, ROS/factory tools were integrated through explicit contracts;
7. representative failures were detected and recovered or safely escalated;
8. production-like regression/Chaos/Soak evidence was generated;
9. the final portfolio communicates business relevance, measured improvements, limitations, and engineering decisions without fabricated claims.
