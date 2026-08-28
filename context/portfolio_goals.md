# Portfolio Goals — Evidence and Story

> Last reviewed: 2026-08-28
> Purpose: define what must be visible and defensible at the end of the project.

## 1. Portfolio thesis

The final portfolio should demonstrate this thesis:

> A senior robot/software engineer can rapidly absorb modern Physical AI technologies, directly fine-tune and improve a VLA from collected demonstrations, engineer a stateful LLM Agent with production-oriented controls, and integrate the two through reliable robot/factory interfaces with measured failure-recovery evidence.

The strongest signal is **learning speed plus engineering discipline**, not the number of frameworks used.

---

## 2. Four headline portfolio extracts

The final project-management workbook already anticipates four key outputs. Repository results must make them reproducible.

### 2.1 VLA V1 -> V2 performance improvement

Required story:

```text
Dataset V1
-> Model V1
-> evaluation
-> dominant failure
-> engineering hypothesis
-> targeted Dataset V2
-> Model V2
-> regression/generalization evaluation
```

Expected output artifact:

- `results/portfolio/vla_v1_v2.csv`

Suggested metrics:

- Normal SR;
- Position SR;
- Orientation SR;
- Distractor SR;
- Overall SR;
- latency;
- intervention rate.

The portfolio should emphasize **why the dataset changed**, not only the improvement percentage.

### 2.2 Agent 100 Mission evaluation

Required story:

> The Agent was evaluated repeatedly over a scenario-balanced benchmark rather than a few curated demos.

Expected artifact:

- `results/portfolio/agent_100_missions.csv`

Required metrics:

- Mission Success Rate;
- Tool Selection Accuracy;
- Invalid Tool Call Rate;
- Recovery Success Rate;
- Human Intervention Rate;
- P95 Latency.

### 2.3 Chaos / Soak validation

Required story:

> Production-oriented failure modes were intentionally injected and the prototype was tested for recovery and long-running stability.

Expected artifacts:

- `results/portfolio/chaos_summary.csv`;
- `results/portfolio/soak_summary.csv`.

Representative Chaos cases:

- WMS timeout;
- malformed WMS response;
- Agent restart;
- DB disconnect;
- ROS node restart;
- VLA timeout;
- robot unavailable;
- network latency spike.

Soak target:

- 24h required if feasible within project constraints;
- 72h desired;
- 7 days optional.

### 2.4 Failure -> Decision -> Improvement cases

Select 2-3 cases with the clearest engineering reasoning.

Expected artifact:

- `results/portfolio/improvement_cases.json`.

Each case should contain:

1. Failure / symptom;
2. Evidence;
3. Root-cause hypothesis;
4. Decision and alternatives considered;
5. Change implemented;
6. Before metric;
7. After metric;
8. Evidence paths;
9. limitation/remaining risk.

Prefer a smaller numerical gain with a clear engineering decision over a large but unexplained gain.

---

## 3. Minimum final deliverables

### Repository

- clean README;
- reproducible setup;
- architecture/contracts;
- tests;
- measured results;
- no leaked secrets or proprietary data.

### Technical documentation

- `docs/architecture/system_architecture.md`;
- Architecture Decision Records;
- component contracts;
- VLA training/evaluation report;
- Agent evaluation report;
- failure analysis;
- Chaos/Soak report;
- production-readiness assessment.

### Demo

Target 3-5 minutes.

Recommended narrative:

```text
1. business problem
2. natural-language mission
3. Agent plan/tool calls
4. AMR/VLA execution
5. injected mismatch/failure
6. recovery/replan
7. mission completion
8. metrics/evidence dashboard
```

The failure/recovery segment is more important than visual polish.

---

## 4. README structure target

The final README should approximately follow:

1. Business Problem
2. Why this maps to Physical AI / SDF
3. Architecture
4. LLM Agent design
5. VLA dataset and fine-tuning
6. Integration contracts
7. Failure recovery
8. Evaluation methodology
9. Measured results
10. VLA V1 -> V2 improvement
11. Agent 100 Mission benchmark
12. Chaos / Soak results
13. Failure -> Decision -> Improvement cases
14. Production-readiness assessment
15. Limitations
16. Next steps
17. JD capability mapping

Do not write final measured claims until the data exists.

---

## 5. Portfolio evidence quality bar

### Strong evidence

- automated test output;
- machine-readable benchmark result;
- experiment manifest;
- failure trace correlated by mission ID;
- model/dataset version mapping;
- reproducible script;
- before/after evaluation;
- commit-linked report.

### Weak evidence

- screenshot without run context;
- single successful demo;
- hand-entered metric with no source;
- unversioned model file;
- prompt transcript presented as evaluation.

Strong evidence should dominate.

---

## 6. Quantitative results policy

Never pre-commit to invented final numbers.

Targets may be used for engineering gates, but the final portfolio must display actual results.

If a target is missed, do not hide it. A useful portfolio story may be:

```text
Target: 95% recovery
Measured: 89%
Dominant remaining failure: VLA timeout after retry budget exhaustion
Mitigation implemented: fallback/HITL
Remaining production risk: model-service availability
```

This can be more credible than a suspiciously perfect result.

---

## 7. Seniority signals to make explicit

The final project should make these visible:

- architecture boundaries, not framework glue;
- ADRs and trade-offs;
- contract/version management;
- failure taxonomy;
- release gates;
- regression policy;
- observability;
- rollback/recovery;
- production-like validation;
- limitation disclosure.

---

## 8. Business alignment signals

Use the project to show familiarity with a manufacturing software/robot-intelligence context:

- line-side logistics;
- WMS/inventory state;
- heterogeneous robot/fleet abstraction;
- Robot Integrated Monitoring-like operational concerns;
- AI Agent orchestration;
- PHM-informed resource selection;
- virtual/simulation verification;
- IT/OT integration boundaries.

Do not claim to reproduce Hyundai AutoEver proprietary products.

---

## 9. Final interview narrative

A defensible final narrative should resemble:

> My existing strength is robot software and system integration. I identified that this JD places additional weight on production-level Agent operation and VLA fine-tuning, so I built a project specifically to close those two gaps. I directly constructed and versioned manipulation demonstrations, fine-tuned a VLA, classified failure modes, and improved a later dataset/model version. In parallel, I built a stateful Agent with explicit tool contracts, persistence, idempotency, HITL, and repeatable evaluation. I then integrated the Agent and VLA into a manufacturing logistics flow and validated representative failures with Chaos/Soak-style tests. The key outcome is not just that the demo works, but that each improvement and recovery behavior is measurable and traceable.

The final wording must be adjusted to actual results.
