# Read-only Review — TASK-SIM-GATE

## 1. 검토 정보

- TASK: `TASK-SIM-GATE`
- 작업 유형: Independent Read-only Re-review
- 실행 순번: `04`
- 일자: `2026-09-14`
- 검토 대상: `65fc651618fe316eefe3a903274bcdd94607abef` 기준 uncommitted `03_fix` delta
- 검토 시점 Git 상태: gate verifier/test/report/evidence와 TASK history가 modified/untracked, staged changes 없음
- Evidence: `../../../results/simulation/SIM-GATE_readiness.json`
- Evidence SHA-256: `d376b7f43580c27c500fd915b81f277e5b4c67215b36b80530d00b26e1c2c0ec`
- Evidence payload SHA-256: `ff0cf6ccf1e72732719e3fde7e26cba90333d91054b2525f3102a000055be78d`

## 2. 검토 결론

- Recommendation: `REJECT`
- Computed canonical result: `SIM_GO`
- Effective simulation-lane authorization: `false`
- BLOCKER: 1
- HIGH: 0
- MEDIUM: 0
- LOW: 0

Canonical repository에서는 C01–C20과 `SIM_GO`가 정확히 재구성되고 이전 malformed-boolean finding도 해소됐다. 그러나 acceptance의 `reviewed_commit`과 runtime hash를 함께 변경하고 direct operation을 문자열 연결로 구성한 독립 temp-clone probe가 원래 review record와 불일치하면서도 C06/C08/C18 및 최종 `SIM_GO`를 통과했다. Independent-review provenance와 direct-actuator invariant를 결합해 우회할 수 있으므로 acceptance할 수 없다.

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| Required Context 및 frozen ordering | `REQUIRED_CONTEXT_PATHS`, source binding reconstruction | canonical test | C01–C02 | PASS |
| SIM-001 independent acceptance/READY | `sim_001_identity`, `sim_001_ready` | missing/blocked/stale tests | C03–C05 | PASS |
| SIM-002 independent acceptance/READY | `_review_record_matches`, `sim_002_identity` | missing/blocked tests | C06–C07 | FAIL — review record가 지칭한 exact commit과 acceptance `reviewed_commit` 미비교 |
| acceptance/current/reviewed Git blob 결속 | `_reviewed_file_binding_matches` | rehashed runtime test | C05, C08 | FAIL — acceptance `reviewed_commit` 자체를 바꾸면 다른 commit blob을 신뢰 |
| SIM-002 → SIM-001 binding | `sim_002_to_sim_001` | different predecessor test | C09 | PASS |
| bounded deterministic smoke | `_bounded_smoke_is_valid` | canonical/tampering tests | C10 | PASS |
| physical/camera/motion isolation | boundary predicates | physical mutation tests | C11–C13 | PASS |
| P0/Week authorization preservation | strict P0 validation | mutation/missing/malformed tests | C14, C19 | PASS |
| Dataset/training separation | boundary predicates | Dataset alias test | C15–C16 | PASS |
| accepted logical contract boundary | `contract_boundary` | canonical operation test | C17 | PASS |
| no direct actuator contract | literal AST allowlist + token blacklist | literal operation test | C18 | FAIL — concatenated operation identifier bypass |
| independent decision reconstruction | C01–C19 aggregation | forged result tests | C20 | FAIL — combined provenance/operation bypass returns `SIM_GO` |
| strict boolean authorization snapshot | `_conservative_bool` | string/int/null matrix | snapshot | PASS |
| implementation/acceptance/authorization separation | hard false effective authorization | canonical/negative tests | state fields | PASS |

## 4. 주요 Findings

### BLOCKER

- **ID:** `TASK-SIM-GATE-REV-B02`
- **File / Symbol:** `scripts/verify_simulation_lane_gate.py::_review_record_matches`, `_git_blob_sha256`, `_runtime_operations_are_allowlisted`; related tests in `tests/test_simulation_lane_gate.py`
- **Issue:** `_review_record_matches`는 review record에서 `ACCEPT`와 task decision 문자열만 확인하고, record가 지칭하는 exact reviewed commit을 acceptance의 `reviewed_commit`과 비교하지 않는다. `_runtime_operations_are_allowlisted`는 완성된 단일 string literal만 수집하므로 `"actuator" + ".execute"`를 operation으로 인식하지 못한다.
- **Why it matters:** Temp clone에서 runtime에 `DIRECT_ACTUATOR_OPERATION = "actuator" + ".execute"`를 추가해 commit하고, copied SIM-002 acceptance의 `reviewed_commit`과 `runtime_module_sha256`만 그 commit에 맞췄다. Review record는 계속 원래 `6abd9fc1158cd9fd0a02d2a496557fd74a16390b`를 명시했지만 verifier는 `C06=PASS`, `C08=PASS`, `C18=PASS`, 최종 `SIM_GO`를 반환했다. 미검토 revision과 direct-actuator operation이 결합해 mandatory authorization gate를 우회한다.
- **Requirement / Contract affected:** TASK Sections 4.2, 5, 14, C06, C08, C18, C20, 21, 22; `INV-SIM-003`; `payload hash != semantic trust`.
- **Evidence:** Independent isolated-clone probe: `gate_result=SIM_GO`, `C06=PASS`, `C08=PASS`, `C18=PASS`, `review_record_still_names_original=True`.
- **Recommended remediation:** Acceptance의 task별 canonical paths를 고정하고, independent review record 또는 별도 immutable review binding이 명시한 exact reviewed commit을 acceptance 값과 비교한다. Operation analysis는 constant concatenation을 포함한 static string expression을 정규화하거나 direct actuator/control ownership marker를 구조적으로 거부해야 한다. 위 combined attack을 그대로 재현하여 반드시 `SIM_NO_GO`가 되는 regression test를 추가한다.

### HIGH

No HIGH findings.

### MEDIUM

No MEDIUM findings. 이전 `TASK-SIM-GATE-REV-M01`은 strict boolean snapshot과 malformed input matrix로 해소됐다.

### LOW

No LOW findings.

## 5. Scope Review

- required scope implemented: PASS
- unrelated changes: PASS
- next-task leakage: PASS
- frozen boundaries preserved: PASS for the canonical delta

변경은 TASK-SIM-GATE verifier, focused tests, report/evidence와 task history에 한정됐다. Runtime, predecessor contract/schema, ADR, P0 evidence, physical integration, Dataset V1, training, Week task, hardware freeze 또는 post-review acceptance는 변경되지 않았다.

## 6. Contract Review

- contract compliance: FAIL
- prior-task compatibility: PASS for canonical repository state
- public interface compatibility: FAIL

검토한 frozen sources는 `ADR-Simulation-Lane-v1.md`, `simulation_task_mapping_v1.md`, `system_architecture_v1.md`, `contract_plan.md`, `simulation_execution_contract_v1.md`, hardware status, P0-004R 및 accepted SIM-001/SIM-002 evidence/acceptance chain이다. Canonical content는 frozen five-operation boundary를 보존하지만 combined probe에서 새 direct operation을 차단하지 못한다.

## 7. Test Adequacy

- happy paths: PASS
- invalid paths: FAIL
- boundary cases: FAIL
- invariant coverage: FAIL
- focused suite: PASS — `19 passed in 1.70s`
- full regression: PASS — `188 passed in 42.10s`

새 tests는 exact literal `actuator.execute`와 acceptance hash rewrite를 다루지만, acceptance `reviewed_commit` rewrite와 static string concatenation을 결합한 우회는 포함하지 않는다.

## 8. Evidence Integrity

- evidence exists: PASS
- task identity correct: PASS
- changed-file list correct: NOT APPLICABLE
- test claims verified: PASS
- exit criteria verified: FAIL
- hashes verified: PASS

Independent reconstruction은 canonical evidence와 byte-for-byte 일치했으며 current/acceptance/reviewed-blob hashes도 모두 일치했다. 그러나 C06/C08/C18/C20이 combined tampering에서 false PASS이므로 semantic evidence integrity는 FAIL이다.

## 9. Acceptance Gates

```text
Scope compliance: PASS
Requirement compliance: FAIL
Contract compliance: FAIL
State / invariant safety: FAIL
Test adequacy: FAIL
Regression safety: PASS
Evidence integrity: FAIL
```

## 10. 검토에서 확인한 핵심 위험

- File blob을 commit에 결속해도 그 commit ID 자체가 independent review record와 결속되지 않으면 provenance를 다른 revision으로 바꿀 수 있다.
- AST의 단일 literal 수집은 constant concatenation 같은 간단한 표현에도 operation 의미를 놓친다.
- 개별 방어가 각각 존재해도 두 약점을 결합하면 최종 `SIM_GO`까지 도달할 수 있으므로 combined adversarial regression이 필요하다.

## 11. 최종 Recommendation

`REJECT TASK-SIM-GATE`

`TASK-SIM-GATE-REV-B02`를 수정하고 evidence를 재생성한 뒤 다시 independent review해야 한다. `simulation_lane_authorized=false`를 유지하고 `SIM-GATE_acceptance.json`을 생성해서는 안 된다.

