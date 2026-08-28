# TASK 작업 이력 기록 정책

## 목적

이 문서는 Codex가 수행하는 각 TASK의 다음 작업을 `docs/`에 누적 기록하기 위한 공통 정책이다.

- Implementation
- Read-only Review
- Fix
- Re-review

목적은 단순 로그 보관이 아니라 다음을 가능하게 하는 것이다.

1. TASK별 구현 의도와 변경 범위 추적
2. 독립 검토에서 발견된 문제와 수정 과정 추적
3. 테스트 / Exit Criteria / Evidence 추적
4. 포트폴리오 및 기술 면접에서 문제 해결 과정을 설명할 수 있는 기록 확보
5. 최종 코드만으로 보이지 않는 설계 판단과 품질 게이트 기록

---

## 1. 저장 위치

모든 TASK 작업 이력은 다음 위치에 저장한다.

```text
docs/task_history/<TASK_ID>/
```

예:

```text
docs/task_history/TASK-MVP-002/
```

TASK별 디렉터리의 권장 구조:

```text
docs/task_history/TASK-MVP-002/
├── README.md
├── 01_implementation.md
├── 02_review.md
├── 03_fix.md
└── 04_review.md
```

추가 수정/재검토가 발생하면 계속 순번을 증가시킨다.

```text
05_fix.md
06_review.md
...
```

기존 기록 파일은 덮어쓰지 않는다.

---

## 2. 실행 순번 결정

각 Implementation / Review / Fix 실행 시:

1. `docs/task_history/<TASK_ID>/`가 없으면 생성한다.
2. 기존 `NN_*.md` 파일을 조회한다.
3. 가장 큰 `NN`에 1을 더하여 다음 실행 순번 `SEQ`를 결정한다.
4. 두 자리 숫자를 사용한다.

예:

```text
01_implementation.md
02_review.md
03_fix.md
04_review.md
```

기존 기록을 수정하거나 번호를 재사용하지 않는다.

---

## 3. 파일 종류

### Implementation

```text
<SEQ>_implementation.md
```

예:

```text
01_implementation.md
```

### Read-only Review / Re-review

```text
<SEQ>_review.md
```

예:

```text
02_review.md
04_review.md
```

### Fix

```text
<SEQ>_fix.md
```

예:

```text
03_fix.md
```

Review와 Re-review를 별도 파일명으로 구분하지 않는다.
시간 순서 자체가 재검토 여부를 보여준다.

---

## 4. 언어 정책

포트폴리오 가독성을 위해 설명 문장은 기본적으로 **한글**로 작성한다.

다음 항목은 원문 또는 영문 식별자를 유지한다.

- TASK ID
- 클래스 / 함수 / 변수 / enum 이름
- 파일 경로
- Git commit hash
- CLI 명령어
- 에러 메시지
- 테스트 이름
- contract / schema field
- ADR ID
- 상태 토큰
- `PASS`, `FAIL`, `ACCEPT`, `REJECT`
- `BLOCKER`, `HIGH`, `MEDIUM`, `LOW`

예:

```text
`MissionRecord.retry_limit`가 caller-controlled 상태여서
"one bounded retry" invariant를 우회할 수 있었다.
```

기술 용어를 억지로 한글화하지 않는다.

---

## 5. README.md 역할

각 TASK 디렉터리의 `README.md`는 상세 로그가 아니라 **TASK 전체 작업 흐름 요약**이다.

권장 구조:

```markdown
# TASK-MVP-002 작업 이력

## 1. TASK 개요

- TASK:
- 목표:
- 구현 범위:
- 주요 비범위:
- 관련 Context / Plan / Contract:

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | 최초 상태 모델 구현 | `01_implementation.md` |
| 02 | Review | REJECT | invariant 우회 2건 발견 | `02_review.md` |
| 03 | Fix | READY FOR RE-REVIEW | retry/constructor invariant 수정 | `03_fix.md` |
| 04 | Review | ACCEPT | 전체 Acceptance Gate 통과 | `04_review.md` |

## 3. 주요 설계 / 문제 해결 포인트

- ...
- ...

## 4. 검증 결과

- Focused tests:
- Full regression:
- Evidence:
- Final review:

## 5. 최종 상태

`ACCEPT TASK-MVP-002`

## 6. 포트폴리오 요약

TASK에서 해결한 문제를 3~6문장으로 기술한다.
무엇을 만들었는지뿐 아니라,
어떤 결함이 Review에서 발견되었고
어떻게 invariant / contract / test를 강화했는지를 포함한다.
```

### README 갱신 규칙

각 workflow 종료 시 `README.md`의 작업 흐름에 현재 실행을 추가한다.

기존 작업 이력을 삭제하거나 재작성하지 않는다.

최종 `ACCEPT` Review가 발생하면:

- `최종 상태` 갱신
- `검증 결과` 갱신
- `포트폴리오 요약` 갱신

중간 단계에서는 확인되지 않은 최종 성공을 미리 작성하지 않는다.

---

## 6. Implementation 기록 형식

`<SEQ>_implementation.md`:

```markdown
# Implementation — <TASK_ID>

## 1. 작업 정보

- TASK:
- 작업 유형: Implementation
- 실행 순번:
- 일자:
- 시작 시 Repository 상태:
- 선행 조건:

## 2. 작업 목적

TASK가 해결하려는 문제와 구현 목표를 한글로 요약한다.

## 3. 구현 범위

### 구현한 내용

- ...

### 명시적으로 구현하지 않은 내용

- ...

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `...` | ... |

## 5. 주요 구현 내용

핵심 클래스, 상태 모델, API, 알고리즘, contract 준수 사항을 설명한다.

## 6. 주요 설계 판단

왜 이 구조를 선택했는지 기록한다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Focused test | `...` | PASS |
| Regression | `...` | PASS |
| Syntax/static | `...` | PASS |
| `git diff --check` | `...` | PASS |

## 8. Exit Criteria

- ... — PASS/FAIL

## 9. Evidence

- 경로:
- Hash:
- 상태:

## 10. 구현 결과

`<TASK_ID> is complete.`

또는

`<TASK_ID> is NOT complete.`

## 11. 다음 단계

독립 Read-only Review 여부 등 다음 작업만 기록한다.
```

---

## 7. Review 기록 형식

`<SEQ>_review.md`:

```markdown
# Read-only Review — <TASK_ID>

## 1. 검토 정보

- TASK:
- 작업 유형: Independent Read-only Review
- 실행 순번:
- 검토 대상:
- 검토 시점 Git 상태:

## 2. 검토 결론

- Recommendation: ACCEPT / REJECT
- BLOCKER:
- HIGH:
- MEDIUM:
- LOW:

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|

## 4. 주요 Findings

### BLOCKER

...

### HIGH

...

### MEDIUM

...

### LOW

...

## 5. Acceptance Gates

```text
Scope compliance: PASS/FAIL
Requirement compliance: PASS/FAIL
Contract compliance: PASS/FAIL
State / invariant safety: PASS/FAIL/NOT APPLICABLE
Test adequacy: PASS/FAIL
Regression safety: PASS/FAIL
Evidence integrity: PASS/FAIL/NOT APPLICABLE
```

## 6. 검토에서 확인한 핵심 위험

포트폴리오 관점에서 중요한 문제를 한글로 2~5개 요약한다.

## 7. 최종 Recommendation

`ACCEPT <TASK_ID>`

또는

`REJECT <TASK_ID>`
```

### Review의 Read-only 의미

Read-only Review는 다음 영역에 대해 엄격히 read-only다.

- `src/`
- `tests/`
- `results/`
- contracts / schemas / ADR
- architecture / plan / task specification
- Git index / history

단, 감사 기록을 남기기 위한 다음 문서 쓰기만 예외적으로 허용한다.

```text
docs/task_history/<TASK_ID>/<SEQ>_review.md
docs/task_history/<TASK_ID>/README.md
```

이를 **audit-log write exception**으로 정의한다.

Review는 이 두 파일 외의 repository 파일을 생성/수정/삭제하면 안 된다.

---

## 8. Fix 기록 형식

`<SEQ>_fix.md`:

```markdown
# Fix — <TASK_ID>

## 1. 수정 정보

- TASK:
- 작업 유형: Review Finding Fix
- 실행 순번:
- 기준 Review:
- 수정 대상 Severity:

## 2. 수정 대상 Findings

| Finding ID | Severity | 문제 | 처리 결과 |
|---|---|---|---|
| ... | BLOCKER | ... | FIXED |

## 3. 원인 분석

단순 증상이 아니라 왜 문제가 발생했는지 기술한다.

## 4. 수정 내용

| 파일 | 수정 내용 | 연결 Finding |
|---|---|---|

## 5. 추가/강화한 테스트

Review에서 발견된 우회 경로나 실패 경로를
어떤 regression test로 고정했는지 기술한다.

## 6. 테스트 결과

| 검증 | 결과 |
|---|---|
| Focused tests | PASS |
| Full regression | PASS |
| `git diff --check` | PASS |

## 7. Evidence 갱신

- Evidence:
- Hash:
- 변경된 claim:

## 8. 남은 Findings

없으면:

`없음`

LOW 또는 defer한 MEDIUM이 있다면 명시한다.

## 9. History Action

`No history action required.`

또는

`HISTORY ACTION REQUIRED`

## 10. 수정 결과

`<TASK_ID> fixes are ready for independent re-review.`

또는

`<TASK_ID> fixes are NOT ready for independent re-review.`
```

---

## 9. 글로벌 TASK History Index

다수 TASK가 누적되면 다음 파일을 유지하는 것을 권장한다.

```text
docs/task_history/README.md
```

예:

```markdown
# TASK 작업 이력

| TASK | 상태 | Implementation | Review | Fix | 최종 결과 |
|---|---|---:|---:|---:|---|
| TASK-MVP-001 | ACCEPTED | 1 | 1 | 0 | ACCEPT |
| TASK-MVP-002 | ACCEPTED | 1 | 2 | 1 | ACCEPT |
| TASK-MVP-003 | IN PROGRESS | 1 | 1 | 0 | REJECT |
```

각 workflow 종료 시 해당 TASK 행을 최신 상태로 갱신한다.

상세 정보는 반드시 TASK별 `README.md`에 둔다.

---

## 10. Evidence와 docs의 역할 분리

`results/`와 `docs/task_history/`는 목적이 다르다.

```text
results/
→ 기계 검증 가능한 Evidence
→ hash, test result, exit criteria, structured JSON

docs/task_history/
→ 사람이 읽는 작업 이력
→ 설계 의도, 문제 발견, 수정 과정, 검토 결과
```

같은 정보를 과도하게 복제하지 않는다.

TASK History 문서에서는 Evidence 파일을 상대 경로로 참조한다.

예:

```text
Evidence: `../../../results/mvp/MVP-002.json`
```

---

## 11. Portfolio 작성 원칙

TASK 기록은 단순 작업 일지가 아니라 다음 질문에 답할 수 있어야 한다.

1. 어떤 문제를 해결했는가?
2. 어떤 contract / architecture 제약이 있었는가?
3. 어떤 방식으로 구현했는가?
4. 어떤 테스트로 검증했는가?
5. Review에서 무엇이 잘못되었다고 발견했는가?
6. 왜 기존 테스트가 그 문제를 잡지 못했는가?
7. 어떻게 invariant / boundary / evidence를 강화했는가?
8. 최종적으로 어떤 품질 Gate를 통과했는가?

특히 실패한 Review를 삭제하지 않는다.

```text
Implementation → REJECT → Fix → ACCEPT
```

흐름은 포트폴리오에서 중요한 문제 해결 증거다.

---

## 12. Commit 권장 방식

Task 작업 이력 문서도 Git으로 추적한다.

권장 예:

### Implementation

```text
feat(mvp): implement mission state model
```

Implementation 코드 / 테스트 / Evidence / implementation history를 함께 포함할 수 있다.

### Review

```text
docs(review): record TASK-MVP-002 review
```

Review는 source를 수정하지 않고 review report / history summary만 기록한다.

### Fix

```text
fix(mvp): enforce mission runtime invariants
```

Fix 코드 / regression tests / Evidence / fix history를 함께 포함한다.

### Accepted re-review

```text
docs(review): record TASK-MVP-002 acceptance
```

History rewrite는 별도 명시적 사용자 승인 없이 수행하지 않는다.
