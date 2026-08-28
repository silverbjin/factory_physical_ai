# Business Context — Hyundai AutoEver / Physical AI / SDF Alignment

> Last reviewed: 2026-08-28
> Purpose: keep implementation decisions anchored to the target company's public business direction.

## 1. Why this context exists

A technically impressive robot demo can still be weak for this portfolio if it does not resemble the problems Hyundai AutoEver is positioning itself to solve.

This file separates:

- **publicly supported facts**;
- **project interpretation/inference**.

Codex must not present an inference as an official Hyundai AutoEver statement.

---

## 2. Publicly supported facts

### 2.1 Hyundai AutoEver describes SDF as an AI-software-driven manufacturing platform

Hyundai AutoEver's official SDF page describes Software-Defined Factory as a platform that integrates and controls manufacturing elements through AI-driven software and connects OT and IT across the manufacturing value chain.

The same official SDF platform lists, among other solutions:

- WMS (Warehouse Management System);
- Robot Integrated Monitoring;
- Smart Vision;
- Virtual Factory Builder / Virtual Factory Platform;
- SD Brain (AI Agent);
- SF Digital Twin;
- Integrated PHM;
- simulator / integrated control / cloud-edge / data pipeline capabilities.

This combination matters because the target project intentionally combines a factory Agent, robot/fleet state, VLA manipulation, WMS-like state, PHM signal, simulation/verification, and operational evidence.

### 2.2 Hyundai AutoEver disclosed robot intelligence and SDF R&D

Hyundai AutoEver's 2025 public filing lists R&D including:

- `RaaS R&D(2단계) 도메인 기능 개발`: modular robot/equipment operational functions and robot intelligence platform development;
- `SDF 서비스 체계 구현`: SW/HW decoupling, standardized interfaces, function-level service separation, and an autonomous-production foundation;
- `SDF솔루션 선행기술 개발/검증용 물리 테스트베드 구축`: physical factory R&D field and physical-virtual cross-verification;
- `가상공장 환경 에셋확장 및 가상물리 검증 개발`: digital-twin physical/virtual verification;
- `다관절 로봇 가이던스를 위한 AI 기반 3D 측정 기술 개발`: 3D vision, articulated robot coordinate mapping, and robot monitoring;
- global monitoring/metrics-related R&D and AI/LLM projects in adjacent areas.

### 2.3 The target RX Technology team is explicitly robot-intelligence/business oriented

The publicly mirrored Physical AI Engineer posting describes the RX technology team as focused on:

- heterogeneous robot control/monitoring systems;
- integration with other systems;
- manufacturing/logistics productivity;
- robot intelligence services;
- customized solutions and new business development.

The team leader note states that the team was newly established in 2024 to support robotics, combining Hyundai AutoEver software capabilities with robots from inside/outside Hyundai Motor Group and carrying the mission through business realization.

### 2.4 Hyundai Motor Group is elevating Physical AI strategically

Hyundai Motor Group's 2026 public statements describe Physical AI across robotics, smart factories, and autonomous driving and emphasize real-world operational data feeding continuous AI model improvement.

In July 2026, the Group stated that it is evolving beyond traditional automotive manufacturing toward a `Physical AI solution company`, emphasizing manufacturing competitiveness, robotics, AI Defined Factories, and a real-world data flywheel.

---

## 3. Project interpretation

The following is an engineering interpretation derived from the above public materials, not an official division-of-responsibility statement from Hyundai AutoEver.

The most plausible portfolio target is not "build a better robot hardware platform." It is:

> Build the software/intelligence/operations layer that lets heterogeneous robots participate safely and measurably in a software-defined manufacturing process.

That suggests a project emphasis on:

```text
Manufacturing Goal / Order
        |
        v
   AI Agent / SD Brain-like orchestration
        |
        +---- WMS / factory state
        +---- robot/fleet state
        +---- PHM / health
        +---- Digital Twin / simulation evidence
        |
        v
 Robot Intelligence / Skills
        |
    +---+---+
    |       |
   AMR     VLA Manipulator
```

The portfolio should demonstrate **integration and operation**, not merely an isolated model.

---

## 4. Chosen project domain

### Automotive line-side parts logistics

The project uses a constrained automotive factory logistics scenario because it creates a natural bridge among:

- inventory/WMS state;
- AMR movement;
- robot/fleet monitoring;
- manipulation;
- part verification;
- PHM;
- mission scheduling/replanning;
- failure recovery;
- digital/simulation validation.

This is more aligned with the stated manufacturing/logistics and robot-intelligence direction than a household pick-and-place scenario.

---

## 5. Business-relevant demonstration story

Canonical example:

```text
Production request:
"Supply Brake ECU Type-B to Line B."

1. Agent parses the production/logistics goal.
2. WMS-like tool resolves the source rack and quantity.
3. Robot/fleet tool selects an eligible AMR.
4. PHM tool can exclude unhealthy resources.
5. AMR navigation moves to the source.
6. Perception/verification checks the part.
7. Fine-tuned VLA performs the manipulation skill.
8. Agent verifies the result.
9. Failures trigger bounded recovery/replanning.
10. All decisions and outcomes are traceable.
```

The ideal demo includes a failure because operations and recovery are more representative of real deployment than a one-shot success video.

---

## 6. Business alignment checks for future tasks

Before accepting a major feature, ask:

1. Does this strengthen manufacturing/logistics relevance?
2. Does it improve robot intelligence, integration, or operations?
3. Does it prove a JD capability?
4. Does it strengthen measured reliability/evaluation?
5. Could the same time be better spent closing the Agent/VLA competency gaps?

If most answers are no, the feature is likely out of scope.

---

## 7. Facts vs inference language policy

Use wording such as:

- `Hyundai AutoEver publicly lists ...` for verified product/R&D facts;
- `The project interprets this as ...` for architectural inference;
- `This prototype is designed to align with ...` for portfolio design decisions.

Do not say:

- `Hyundai AutoEver will deploy exactly this architecture`;
- `RX team internally uses this exact framework`;
- `this prototype reproduces Hyundai AutoEver proprietary systems`.

No proprietary/internal company information is assumed or required.

---

## 8. Primary references

### Hyundai AutoEver official SDF

- https://www.hyundai-autoever.com/eng/business-area/digital-transformation/sdf/contents.do?cntnSeq=457

Relevant public concepts: SDF, WMS, Robot Integrated Monitoring, SD Brain (AI Agent), SF Digital Twin, Integrated PHM, virtual verification, cloud/edge, data pipeline.

### Hyundai AutoEver public filing / KRX

- https://kind.krx.co.kr/external/2025/11/14/001929/20251114004354/11013.htm

Relevant public R&D: RaaS robot intelligence platform, SDF service architecture, physical SDF testbed, physical-virtual verification, virtual factory, 3D robot guidance/monitoring.

### Target job posting

Official URL supplied for the target role:

- https://career.hyundai-autoever.com/ko/o/229348

Public mirror used to cross-check readable JD/team text:

- https://kr.linkedin.com/jobs/view/tech-ai-engineer-physical-ai-engineer-at-hyundai-autoever-4444257725

### Hyundai Motor Group Physical AI strategy

- https://www.hyundai.com/worldwide/en/newsroom/detail/0000001100
- https://www.hyundai.com/worldwide/en/newsroom/detail/0000001238
- https://www.hyundai.com/content/hyundai/worldwide/en/newsroom/detail/0000001257.html
