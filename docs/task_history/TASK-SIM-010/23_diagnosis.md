# Diagnosis — TASK-SIM-010

Result: RESOLVED

- Status: RESOLVED
- Trigger: S10-G6 준비 중 immutable baseline의 실제 summary가 `4 failed, 337 passed`로 재현되어 `22_review.md`의 `4 failed, 392 passed`와 충돌함
- Triggering status: `S10-G6 STOPPED`
- Finding ID: `SIM010-G6-001`
- Diagnosis tier/model: targeted read-only provenance diagnosis / GPT-5.6 Sol, medium reasoning

## Trigger

`22_review.md`는 candidate와 baseline 모두 `4 failed, 392 passed`라고 기록했다.
그러나 candidate `2179d965...`에서 실행한 fresh G6 runner와 이 진단의 독립 detached
재실행은 baseline `6909c6c...`에 대해 일관되게 `4 failed, 337 passed`를 기록했다.
Canonical Evidence는 갱신되지 않았고 G7은 실행되지 않았다.

## Requirement / Contract

`tasks/TASK-SIM-010.md` §14.10과 `21_diagnosis.md`는
`PROVEN_PREEXISTING`에 total/pass count equality를 요구하지 않는다. 요구 조건은 양쪽
실행의 유효성, 동일한 qualified interpreter와 command, 각 commit의 clean detached
source/test tree, complete failed-node set equality, 그리고 모든 corresponding non-empty
stable failure signature equality이다. Test summary/count는 완전하게 기록해야 하지만
서로 동일할 필요는 없다.

```text
g5_requires_equal_total_test_count: NO
g5_requires_equal_pass_count: NO
g5_requires_equal_failed_node_set: YES
g5_requires_equal_nonempty_stable_signatures: YES
```

## Authoritative Source

- `tasks/TASK-SIM-010.md`, 특히 R11과 §14.10–§14.12
- `docs/task_history/TASK-SIM-010/21_diagnosis.md`
- `docs/task_history/TASK-SIM-010/22_review.md`
- immutable Git objects `2179d965b64abac79c068a94363b9a67e9f4739b` 및 `6909c6cceb727598570f6e170ae8d1d293418c9a`
- `scripts/run_simulation_observability_regression.py::_run_regression`, `classify_execution`
- `src/simulation_runtime/observability_regression.py::failure_signatures`, `classify_regression_failures`
- fresh detached pytest/collection outputs generated during this diagnosis

## Root Cause

Primary classification은 `PREVIOUS_BASELINE_EXECUTED_CANDIDATE_TEST_TREE`이다.
이전 manual G5의 baseline command는 `PYTHONPATH`만 baseline checkout의 `src`로
설정하고 pytest process의 cwd는 candidate worktree에 그대로 두었다.

```text
cwd=/home/jinho/projects/factory_physical_ai_sim_010
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=/tmp/sim010-g5-baseline-log/src
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python -m pytest -q -p no:cacheprovider
```

따라서 pytest는 candidate test tree를 수집했다. 여러 candidate test module은 다시
candidate `ROOT/src`를 `sys.path` 앞에 삽입하므로 이 실행은 하나의 immutable baseline
source/test execution도 아니었다. 이후 별도로 baseline cwd에서 수행한 import probe는
baseline origin을 보였지만, 앞선 full-suite process의 test/source provenance를 소급해
교정하지 못한다. 당시 ephemeral raw log는 정리되었으나 exact command와 result는 해당
manual execution transcript에 남아 있으며, 현재 Git collection 비교가 원인을 재현한다.

## Candidate/Baseline Test Provenance

동일한 qualified interpreter와 command로 각 commit의 clean detached cwd에서 다시
실행했다. 두 worktree는 실행 후 clean 상태를 확인하고 제거했다.

| Field | Candidate | Baseline |
|---|---|---|
| Commit / test-tree origin | `2179d965b64abac79c068a94363b9a67e9f4739b` | `6909c6cceb727598570f6e170ae8d1d293418c9a` |
| Diagnostic worktree | `/tmp/sim010-diag-candidate-cnIwf2` | `/tmp/sim010-diag-baseline-TRP5Gc` |
| Collected tests | `396` | `341` |
| Python | `/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python` | same |
| MuJoCo | `3.13.0` | `3.13.0` |
| Project import origin | candidate detached `src/simulation_runtime/mujoco_vla_backend.py` | baseline detached `src/simulation_runtime/mujoco_vla_backend.py` |
| Command | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<detached>/src .../bin/python -m pytest -q -p no:cacheprovider` | identical |
| Exit / summary | `1`; `4 failed, 392 passed` | `1`; `4 failed, 337 passed` |

Failed-node set은 양쪽 모두 동일한 네 node이고, 각 normalized signature는 non-empty이며
정확히 일치했다. Candidate-only collection은 정확히 55개로,
`tests/test_simulation_observability_regression.py`의 51개와
`scripts/codex/test_run_task_orchestrator.py`의 4개다. Baseline에는 전자 파일 자체가
없다. 따라서 count 차이는 `EXPECTED_TEST_SUITE_EVOLUTION`이며 runner provenance defect가
아니다.

## Previous G0-G5 Record Analysis

```text
previous_392_baseline_source_commit: MIXED / NOT ONE IMMUTABLE BASELINE SOURCE
previous_392_baseline_test_tree_commit: 2179d965b64abac79c068a94363b9a67e9f4739b
previous_392_baseline_reproducible: NO AS EXACT BASELINE; YES ONLY AS THE INVALID HYBRID INVOCATION
previous_392_record_valid: NO
```

`22_review.md`의 baseline summary와 baseline source-isolation 주장은 사실과 다르다.
기존 기록은 append-only audit evidence로 보존하며 이 진단에 의해
`SUPERSEDED_BY_CORRECTIVE_DIAGNOSIS`로 분류한다. G0–G4 결과와 53/21/32/0
requirement-scoped classification은 이 오류의 영향을 받지 않는다.

## Corrected G5 Interpretation

```text
corrected_candidate_summary: 4 failed, 392 passed
corrected_baseline_summary: 4 failed, 337 passed
corrected_G5_classification: PASS_PROVEN_PREEXISTING
S10_G5_corrected_status: PASS
```

두 실행은 유효하고 correct detached source/test tree와 동일 interpreter/command를
사용했다. Complete failed-node sets와 네 corresponding non-empty stable signatures가
정확히 일치하므로 pass-count 차이와 무관하게 §14.10을 충족한다.

G6 중지는 `A REAL G5 CONTRACT FAILURE`나 `C RUNNER DEFECT`가 아니라
`B A CORRECT STOP CAUSED BY AN INCORRECTLY PINNED HISTORY/PROMPT EXPECTATION`이다.
Corrected immutable summary를 명시적으로 사용하여 G6를 다시 실행할 수 있다.

## History Impact

- `existing_gate_history_factually_incorrect`: YES
- `existing_gate_history_should_be_overwritten`: NO
- `corrective_gate_history_required`: YES
- `22_review.md`: `SUPERSEDED_BY_CORRECTIVE_DIAGNOSIS` for baseline summary/source-isolation only

G6 재개 전에 corrected candidate/baseline summary와 G5 PASS를 새 append-only gate
validation record로 남겨야 한다. 기존 record는 수정하거나 삭제하지 않는다.

## Authorized Correction Boundary

- 이 세션: `23_diagnosis.md` 및 TASK-SIM-010 history README만 추가/갱신
- 후속 validation history: corrected G5 facts를 새 numbered record로 append
- 그 다음: immutable candidate `2179d965...`로 manual G6/G7 재실행

Source, tests, runner, TASK specification, Q01/predecessor authority에 대한 correction은
필요하지 않다.

## Protected Boundary

다음을 변경하지 않는다: production source, tests, runner, `tasks/TASK-SIM-010.md`,
canonical Evidence/report, accepted Q01 및 SIM-003–SIM-009 artifacts, Acceptance,
orchestrator source, immutable candidate/baseline Git objects. 기존 numbered history도
덮어쓰지 않는다.

## Required Verification

1. Corrective gate record가 `4 failed, 392 passed` candidate와
   `4 failed, 337 passed` baseline을 각 immutable test-tree commit에 결합해야 한다.
2. Failed-node set 및 non-empty stable signatures의 exact equality를 보존해야 한다.
3. G6/G7은 candidate `2179d965...`와 qualified Python으로 fresh 실행하고 canonical
   Evidence의 `source_git_sha`를 candidate에 고정해야 한다.
4. Canonical Evidence/report와 G7 repeatability가 통과한 뒤에만 S10-G8로 진행한다.

## Assumptions Forbidden

- 동일한 failed count가 동일한 complete failed-node set을 뜻한다.
- `PROVEN_PREEXISTING`은 total/pass count equality를 요구한다.
- `PYTHONPATH`만 baseline으로 지정하면 pytest cwd의 test tree도 baseline이다.
- 별도 import probe가 다른 process의 test/source provenance를 증명한다.
- 최신 documentation HEAD가 source candidate를 대체한다.
- 잘못된 history fact를 canonical Evidence에 그대로 고정해야 한다.

## Next Action

RESUME_IMPLEMENTATION

Final diagnosis status: RESOLVED
