# MVP Portfolio Build Prompt

## Purpose

This file converts the completed Day-10 MVP into a portfolio-ready technical case study.

The goal is not to list all TASKs or changed files. The goal is to explain, with repository evidence, how the MVP was designed, implemented, reviewed, corrected, validated, accepted, and committed as a Physical AI engineering system.

Typical invocation:

```text
Build MVP Portfolio
```

---

## 1. Working Mode

Act as a senior Physical AI / robotics software portfolio editor and system-design reviewer.

This is a documentation-only workflow.

Do not modify:
- `src/`
- `tests/`
- `results/`
- contracts
- schemas
- ADRs
- task specifications
- plans
- Git history

You MAY create/update only:

```text
docs/portfolio/mvp/
```

Do not stage or commit unless explicitly requested.

---

## 2. Sources to Read

Inspect the actual repository before writing.

At minimum read, when present:

- `AGENTS.md`
- `context/`
- `plans/`
- `tasks/TASK-MVP-001.md` through `tasks/TASK-MVP-008.md`
- `docs/architecture/`
- `docs/contracts/`
- relevant ADRs
- `docs/task_history/README.md`
- `docs/task_history/TASK-MVP-001/` through `TASK-MVP-008/`
- `results/`
- relevant Git commits

Also inspect:

```bash
git log --oneline --decorate --graph
git show --stat <relevant-commit>
```

Only describe behavior supported by accepted TASK history, source code, tests, Evidence, frozen architecture/contracts, and Git history.

---

## 3. Portfolio Positioning

Do not present this as “8 TASKs completed.”

Reorganize the MVP around 4–5 engineering themes.

Prefer the following when supported by evidence:

1. Architecture / contract discipline
2. Deterministic mission-action runtime and fail-closed semantics
3. Agent ↔ physical execution responsibility boundary
4. Failure recovery / reconciliation / retry / escalation
5. Independent verification, Evidence, and traceability

Treat Codex automation as engineering infrastructure, not as the main achievement.

The portfolio should communicate:

```text
Problem
→ Constraint
→ Architecture decision
→ Implementation
→ Verification
→ Review finding
→ Fix
→ Regression
→ ACCEPT
```

---

## 4. What to Emphasize

### 4.1 Architecture and contract discipline

Show:
- scope freeze
- frozen contracts
- explicit ownership boundaries
- state/schema discipline
- later-task scope prevention

Explain why these matter in Physical AI systems where probabilistic AI decisions and physical execution have different failure modes.

### 4.2 Deterministic and fail-closed runtime

When present in the accepted implementation, highlight:
- finite state transitions
- explicit action lifecycle
- `UNKNOWN != SUCCEEDED`
- bounded retry
- reconciliation
- recovery
- HITL escalation
- terminal-state invariants
- bypass prevention

Do not claim mechanisms that are not in the final accepted code.

### 4.3 Agent ↔ execution boundary

Explain where Agent reasoning ends and deterministic runtime ownership begins.

When supported, use a structure such as:

```text
Agent intent
    ↓
Contract
    ↓
Mission / Action Runtime
    ↓
Execution Adapter
    ↓
Robot / Simulator / External System
```

### 4.4 Failure-aware engineering

Do not show only happy-path E2E.

Include at least one real case of:

```text
normal path
→ ambiguity/failure
→ detection
→ recovery/reconciliation/escalation
→ verified outcome
```

### 4.5 Independent Review as engineering evidence

Strongly emphasize:

```text
Implementation
→ Tests / Evidence
→ Independent Read-only Review
→ REJECT
→ Fix
→ Regression
→ Re-review
→ ACCEPT
→ Commit
```

At least one case study should show a defect that passed the original tests but was found by independent review and then fixed with a regression test.

### 4.6 Traceability

Show:

```text
Requirement
→ Implementation
→ Test
→ Evidence
→ Review
→ Commit
```

Use exact task IDs, evidence paths, test results, review findings, and commit IDs only when verified.

---

## 5. What Not to Emphasize

Do not make these the center of the portfolio:

- lines of code
- number of prompts
- “AI wrote the code”
- raw test counts without explaining risk coverage
- every TASK in chronological order
- every changed file
- generic “robust/scalable/production-ready” claims
- Week functionality not yet implemented

Do not claim real-factory deployment, production readiness, or real-robot validation unless directly evidenced.

---

## 6. Reconstruct the MVP

For every `TASK-MVP-001` through `TASK-MVP-008`, internally identify:

| Field | Required |
|---|---|
| TASK ID | yes |
| engineering goal | yes |
| major implementation | yes |
| key contract/boundary | when applicable |
| tests | when available |
| first review | yes |
| findings | when applicable |
| fix/design change | when applicable |
| final ACCEPT | yes |
| final commit | when available |
| portfolio value | yes |

Then select only the strongest material for the narrative.

Do not make all eight TASKs equally prominent.

---

## 7. Select 3–5 Engineering Highlights

Select 3 to 5 highlights using these priorities:

1. architecturally important
2. relevant to Physical AI / robotics
3. failure-aware
4. clear before/after improvement
5. evidence-backed
6. useful in technical interviews

For each highlight write:

```text
Problem
→ Constraint
→ Design decision
→ Implementation
→ Verification
→ Review finding if any
→ Correction
→ Final result
→ Engineering lesson
```

---

## 8. Required Outputs

Create:

```text
docs/portfolio/mvp/
├── README.md
├── 01_mvp_overview.md
├── 02_architecture_and_contracts.md
├── 03_engineering_highlights.md
├── 04_failure_recovery_and_validation.md
├── 05_task_traceability.md
├── 06_resume_project_summary.md
└── 07_interview_talking_points.md
```

---

## 9. README.md

Make this the portfolio landing page.

Include:
- project one-liner
- problem
- MVP scope
- explicit non-goals
- architecture-at-a-glance
- 3–5 engineering highlights
- verification workflow
- final accepted MVP status
- links to detailed portfolio documents

Use one Mermaid diagram when repository evidence supports it.

Do not turn README into a full task log.

---

## 10. 01_mvp_overview.md

Use Korean narrative.

Structure:

```text
1. 문제 정의
2. Day-10 MVP 목표
3. 주요 제약
4. 구현 범위
5. 명시적 비범위
6. 최종 MVP 동작
7. 검증 방식
8. MVP에서 얻은 핵심 결과
```

---

## 11. 02_architecture_and_contracts.md

Explain:
- actual MVP components
- responsibility boundaries
- contracts/schemas
- state ownership
- deterministic vs probabilistic responsibilities
- dependency direction

For major decisions use:

```text
Decision
Why
Alternative rejected
Failure prevented
Evidence
```

Use Mermaid Live-compatible syntax.

Only draw components that actually exist in the accepted MVP.

---

## 12. 03_engineering_highlights.md

For each selected highlight:

```markdown
## Highlight N. <title>

### 문제
### 제약
### 설계 판단
### 구현
### 검증
### Review / Fix
### 최종 결과
### 포트폴리오에서 전달할 메시지
```

At least one highlight must be based on an actual `REJECT → Fix → ACCEPT` sequence when such a case exists.

---

## 13. 04_failure_recovery_and_validation.md

Focus on reliability.

When supported, explain:
- normal flow
- failure flow
- ambiguous result handling
- retry
- reconciliation
- recovery
- HITL/escalation
- terminal states

Also document:

```text
Implementation
→ Focused tests
→ Regression
→ Evidence
→ Independent Review
→ ACCEPT / REJECT
```

Include one actual case where the original tests passed but review discovered a gap.

Explain:
1. why the original tests did not catch it;
2. what was changed;
3. what regression test was added;
4. how re-review validated it.

---

## 14. 05_task_traceability.md

Create a compact appendix:

| TASK | Goal | Major artifacts | Tests | First review | Fixes | Final result | Commit |
|---|---|---|---|---|---|---|---|

Cover all `TASK-MVP-001` through `TASK-MVP-008`.

Link to task history where useful.

Do not duplicate full task logs.

---

## 15. 06_resume_project_summary.md

Create resume-ready material.

### A. 3-line project summary

### B. 5 evidence-based bullets

Prefer:

```text
Action + engineering object + technical decision + verified result
```

### C. Technology stack

Separate:
- Core implementation
- Testing / validation
- Development workflow
- Future Week scope

Do not mix future scope into completed MVP technology.

### D. One-sentence interview hook

Write one sentence that invites technical follow-up.

---

## 16. 07_interview_talking_points.md

Create 6–10 likely technical interview questions.

For each:

```markdown
## Q. ...

### 30초 답변

### 2분 답변

### 근거
- file:
- TASK:
- test:
- evidence:
- commit:
```

Prefer questions about:
- Agent vs deterministic execution ownership
- ambiguous success handling
- retry/recovery policy
- what independent review found
- why tests missed it
- contract discipline
- scope leakage prevention
- Evidence integrity
- what would change for real robot integration
- what Week work adds next

Use only questions supported by the actual project.

---

## 17. Language and Style

Use Korean for explanatory narrative.

Keep exact English for:
- code symbols
- state names
- TASK IDs
- file paths
- commands
- technologies
- ADR IDs
- contract/schema fields
- `PASS`, `FAIL`, `ACCEPT`, `REJECT`
- `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`

Tone:
- technical
- concise
- evidence-based
- professional

Avoid exaggerated marketing language and repetitive AI-style phrasing.

---

## 18. Evidence Rules

Every concrete claim must be traceable.

Examples:

```text
26 tests passed
BLOCKER 2건 발견
final ACCEPT
commit abc1234
```

Only use these when verified from repository evidence/history.

If evidence is ambiguous, qualify the statement instead of guessing.

---

## 19. Final Quality Gate

Before finishing, verify:

1. all 8 MVP tasks appear in traceability;
2. only accepted implementation is described as final;
3. failed reviews are not hidden;
4. at least one real `REJECT → Fix → ACCEPT` story is included when available;
5. architecture claims match frozen docs and final code;
6. Week work is not described as MVP-complete;
7. Mermaid diagrams reflect real boundaries;
8. quantitative claims have evidence;
9. resume bullets are outcome-oriented but not exaggerated;
10. interview answers match repository evidence.

---

## 20. Final Report

After creating the portfolio package, report:

```text
MVP PORTFOLIO BUILD COMPLETE
```

Then list:
- created files
- selected 3–5 engineering highlights
- strongest `REJECT → Fix → ACCEPT` case
- final MVP acceptance status
- evidence gaps or intentionally omitted claims
- recommended next portfolio action before Week work

Do not modify implementation code.

Do not begin Week tasks.

Begin building the MVP portfolio now.
