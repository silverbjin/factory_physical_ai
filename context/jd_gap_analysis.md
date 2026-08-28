# JD Gap Analysis — Physical AI Engineer

> Last reviewed: 2026-08-28
> Purpose: turn the candidate/JD gap into explicit project evidence requirements.

## 1. Target role summary

The target Physical AI Engineer JD publicly describes work including:

- autonomous decision-making AI Agent systems integrating LLM, vision models, and reinforcement learning;
- multimodal sensor-based environment perception and autonomous navigation agents;
- agent policy learning/training/optimization using simulation;
- ReAct architecture and tool/API-integrated LLM Agent frameworks;
- Python, C++, and TypeScript implementation;
- ROS, Gazebo, PyBullet, IsaacGym, and computer vision;
- Git, Docker, REST/gRPC API development/deployment.

Publicly listed experience expectations include:

- AI Agent or LLM application development experience;
- robot / Embodied AI experience;
- multiple years of ROS/ROS 2, sensor, simulation, and computer-vision experience;
- deep-learning automation framework experience;
- substantial Python/C++ experience.

Preferred areas include major LLMs, Agent frameworks, PyTorch/TensorFlow/Hugging Face, vector databases, prompt engineering, and Vision-Language Models.

---

## 2. Candidate positioning used by this project

This project assumes the candidate's strongest evidence is in mature robot/software/system engineering, while the most important gaps to close are:

### Gap A — Production-oriented LLM Agent operation

Existing/adjacent experience is not treated as equivalent to long-running production Agent ownership.

The project therefore needs concrete evidence for:

- persistent mission state;
- checkpoint/resume;
- bounded retry/backoff/timeout;
- idempotency;
- Human-in-the-loop;
- structured tool/API contracts;
- offline evaluation;
- regression;
- tracing/observability;
- dependency/process failure recovery;
- Chaos/Soak validation;
- latency/token/cost awareness where applicable.

### Gap B — Direct VLA fine-tuning and dataset iteration

The project assumes insufficient evidence of directly owning a complete VLA learning loop.

The project therefore needs concrete evidence for:

- teleoperation or demonstration acquisition;
- dataset construction and validation;
- dataset versioning;
- direct VLA fine-tuning;
- repeated evaluation;
- failure taxonomy;
- targeted data collection driven by failures;
- V1 -> V2 retraining;
- model/dataset/config/commit traceability;
- deployment behind a stable skill interface.

---

## 3. What the project should not claim

The portfolio must not claim:

- multiple years of production LLM Agent ownership if that experience did not occur;
- VLA research expertise beyond demonstrated work;
- proprietary Hyundai AutoEver system knowledge;
- production-scale robot fleet operation not actually measured.

Instead, the project should make a stronger and defensible senior-level claim:

> A senior robot/software engineer identified the Agent/VLA gap, acquired the technologies rapidly, created measurable learning/evaluation loops, integrated them with a controlled robot software architecture, and validated representative operational failure modes.

---

## 4. JD-to-project evidence map

| JD / capability area | Existing/adjacent strength | Project gap | Required project evidence |
|---|---|---|---|
| ROS / robot / sensor / simulation | Strong | Avoid re-proving excessively | Minimal but reliable ROS 2 execution adapter, AMR/VLA integration |
| Python / C++ | Strong | None central | Production-quality typed Python; C++ only where justified |
| Computer vision | Strong/adjacent | VLM/VLA integration depth | structured visual verification + VLA observations |
| LLM Agent | Partial/adjacent | Production runtime depth | stateful Agent + Tool contracts + 100-mission eval + recovery |
| ReAct / tool use | Partial/newer | Reliability and bounded operation | controlled tool loop, step/timeout limits, error policies |
| API integration | Strong/adjacent | Agent-grade idempotent semantics | WMS/Fleet/PHM REST/gRPC-style contracts, schema validation |
| VLA / Vision-Language action | Gap | Direct training ownership | dataset V1/V2, fine-tuning, evaluation, skill deployment |
| ML training automation | Adjacent | VLA reproducibility | config-driven train/eval scripts + run metadata |
| Simulation policy training | Existing RL experience is adjacent | Do not over-invest | use only if required by chosen VLA/agent validation path |
| Docker/deployment | Existing/adjacent | End-to-end reproducibility | containerized services or reproducible env manifest |
| Reliability / operations | General senior engineering strength | Agent-specific proof | fault injection, restart recovery, Chaos/Soak evidence |
| TypeScript | Not a primary gap | Optional | only lightweight operator UI if schedule allows |

---

## 5. Proof hierarchy

The project should prioritize evidence in this order.

### Tier 1 — Must-have

1. **VLA direct fine-tuning evidence**
   - Dataset V1;
   - training config/log;
   - evaluated Model V1.

2. **Failure-driven VLA improvement**
   - failure taxonomy;
   - targeted Dataset V2;
   - Model V2;
   - measured V1 vs V2 comparison.

3. **Production-oriented Agent evidence**
   - durable mission state;
   - tool schemas;
   - retry/timeout/idempotency;
   - restart recovery;
   - structured traces.

4. **Agent evaluation**
   - repeatable 100-mission benchmark;
   - mission/tool/recovery/latency metrics.

5. **E2E failure recovery**
   - at least three representative failure scenarios across model/runtime/factory state.

### Tier 2 — Strong differentiators

- Chaos fault injection harness;
- 24h/72h Soak testing;
- model/service rollback;
- PHM-driven resource reassignment;
- reproducible portfolio metric export;
- architecture decision records.

### Tier 3 — Optional polish

- TypeScript operator dashboard;
- more VLA model families;
- multi-agent orchestration;
- photorealistic digital twin;
- advanced fleet scheduling.

Tier 3 must never block Tier 1 or Tier 2.

---

## 6. Seniority bar

For a senior candidate, success is not measured only by feature count.

Every major implementation should answer:

1. Why is the responsibility placed in this component?
2. What happens when it fails?
3. How is failure detected?
4. How is recovery bounded?
5. How can an operator inspect the event?
6. How is the change evaluated and regressed?
7. How is the artifact/version rolled back?
8. What evidence proves the result?

A junior-style `works on my machine` demo is insufficient.

---

## 7. Portfolio wording after completion

Preferred framing after real evidence exists:

> My prior strength is robot software and system integration. For this role, I deliberately targeted two weaker areas: production-oriented LLM Agent operation and direct VLA fine-tuning. I built a manufacturing logistics prototype where the Agent orchestrates factory tools and a fine-tuned VLA skill through explicit contracts, then evaluated it with failure-driven VLA dataset iterations, a repeatable Agent mission benchmark, and production-like failure/soak tests.

This wording must be updated to match actual measured outcomes.
