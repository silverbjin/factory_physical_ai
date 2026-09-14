# Read-only Review — TASK-SIM-GATE

## 1. 검토 정보

- TASK: `TASK-SIM-GATE`
- 작업 유형: Independent Read-only Review
- 실행 순번: `02`
- 일자: `2026-09-14`
- 검토 대상 commit: `714e1cf6854861380013ebc1bf09d812ba3edca8`
- 리비전 확인: 최초 `6503618c83a51714a4ad948f58917832e8bbc4e2` 기준 implementation delta로 검토를 시작했으며, 동일 delta가 검토 도중 위 commit으로 기록됨
- 검토 시작 시 Git 상태: TASK-SIM-GATE artifact 6개 untracked, global task-history index 1개 modified, staged changes 없음
- Evidence: `../../../results/simulation/SIM-GATE_readiness.json`
- Evidence SHA-256: `430a84d5555e6e9a9e0ae1f01a680bbb47e30350b8f4060069c26800d37ed231`
- Evidence payload SHA-256: `0582322051568429667f1f06668637ee07f5bd9eabc9f91e94295e8a6208e2a2`

## 2. 검토 결론

- Recommendation: `REJECT`
- Computed implementation result: `SIM_GO`
- Effective simulation-lane authorization: `false`
- BLOCKER: 1
- HIGH: 0
- MEDIUM: 1
- LOW: 0

Canonical repository 상태에서는 C01–C20과 current `SIM_GO` 계산이 재현된다. 그러나 unreviewed runtime 변경을 modified acceptance hash로 다시 가리키게 만들면 reviewed commit의 실제 blob과 비교하지 않아 direct-actuator invariant를 우회하고 `SIM_GO`를 반환한다. Mandatory contract boundary가 우회 가능하므로 acceptance할 수 없다.

## 3. Requirement Traceability

| Requirement | Implementation | Test | Evidence | Status |
|---|---|---|---|---|
| Exact Required Context binding | `REQUIRED_CONTEXT_PATHS`, `_required_context_bindings` | canonical positive test | `required_context_bindings` | PASS |
| SIM-001 acceptance/READY/bindings | `sim_001_identity`, `sim_001_ready`, `sim_001_immutable` | blocked/missing/stale/profile tests | C03–C05 | PASS |
| SIM-002 acceptance/READY/bindings | `sim_002_identity`, `sim_002_ready`, `sim_002_immutable` | blocked/missing/stale tests | C06–C08 | FAIL — reviewed-commit content binding 누락 |
| SIM-002 → SIM-001 binding | `sim_002_to_sim_001` | different-revision test | C09 | PASS |
| bounded smoke semantics | `_bounded_smoke_is_valid` | canonical and tampering suite | C10 | PASS |
| physical/camera/motion isolation | `physical_independence`, `camera_independence`, `no_physical_motion` | physical authorization test | C11–C13 | PASS |
| P0 exact Week authorization | `p0_valid`, `week_preserved` | mutation/missing-P0 tests | C14, C19 | PASS |
| Dataset/training separation | `dataset_boundary`, `training_boundary` | Dataset alias test | C15–C16 | PASS |
| accepted contract boundary | `contract_boundary` | canonical test | C17 | PASS |
| no direct actuator contract | `no_direct_actuator` token blacklist | marker-only direct actuator test | C18 | FAIL — 실제 새 operation 우회 가능 |
| self-report/forged result rejection | decision reconstructed from C01–C19 | forged `SIM_GO` test | C20 | FAIL — acceptance rehash + unreviewed direct operation에서 false PASS |
| required authorization snapshot booleans | direct `_dig` values from P0 | canonical boolean test only | `authorization_snapshot` | FAIL — malformed present value가 non-boolean으로 전파됨 |
| implementation/acceptance/authorization separation | hard false effective authorization | canonical and all negative tests | state fields | PASS |
| machine-readable evidence integrity | canonical payload and artifact hashes | independent reconstruction | evidence/payload | FAIL — C18/C20 semantic claim이 우회 probe와 불일치 |

## 4. 주요 Findings

### BLOCKER

- **ID:** `TASK-SIM-GATE-REV-B01`
- **File / Symbol:** `scripts/verify_simulation_lane_gate.py::_commit_exists`, `sim_002_immutable`, `no_direct_actuator`; `tests/test_simulation_lane_gate.py::test_direct_actuator_contract_detected`
- **Issue:** Verifier는 acceptance의 `reviewed_commit`이 존재하는지만 확인하고 acceptance-bound runtime/evidence/report/test blob이 그 commit의 실제 내용과 같은지 확인하지 않는다. C18은 제한된 문자열 blacklist와 SIM-001 self-report boolean에 의존한다. Temp probe에서 `src/simulation_runtime/smoke.py`에 `DIRECT_ACTUATOR_OPERATION = "actuator.execute"`를 추가하고 SIM-002 acceptance의 runtime SHA만 새 파일에 맞추자 `C08=PASS`, `C18=PASS`, 최종 `SIM_GO`가 나왔다.
- **Why it matters:** 독립 검토되지 않은 direct actuator-facing operation이 acceptance hash 갱신만으로 gate를 통과한다. 이는 mandatory no-direct-actuator invariant와 immutable independent-review trust chain을 우회한다.
- **Requirement / Contract affected:** TASK Sections 4.2, 14, C08, C18, C20, 21, 22; `INV-SIM-003`, `INV-SIM-004`, `payload hash != semantic trust`.
- **Evidence:** Independent probe result: `gate_result=SIM_GO`, `C08=PASS`, `C18=PASS`, while mutated runtime did not match reviewed commit `6abd9fc1158cd9fd0a02d2a496557fd74a16390b`.
- **Recommended remediation:** Acceptance가 가리키는 profile/evidence/report/runtime/entry/test 각각을 `reviewed_commit:path` blob과 SHA-256 비교하고 current canonical file 및 acceptance SHA와 모두 일치시켜야 한다. C18은 marker boolean이나 단순 blacklist가 아니라 reviewed blob binding과 allowlisted logical-operation/public-boundary 분석으로 재구성한다. Negative test는 실제 runtime/contract에 direct actuator operation을 추가하고 hashes를 재계산한 뒤 반드시 `SIM_NO_GO`를 검증해야 한다.

### HIGH

No HIGH findings.

### MEDIUM

- **ID:** `TASK-SIM-GATE-REV-M01`
- **File / Symbol:** `scripts/verify_simulation_lane_gate.py::evaluate_simulation_lane_gate`, `authorization_snapshot` construction
- **Issue:** P0 authorization 값이 존재하지만 boolean이 아닌 경우 `p0_valid`는 실패해 `SIM_NO_GO`가 되지만, snapshot은 `_dig(..., default=False)`가 원래 malformed 값을 그대로 반환한다. Probe에서 `task_w1_001="false"`를 주자 output이 JSON boolean `false`가 아니라 string `"false"`였다.
- **Why it matters:** Gate는 안전하게 NO_GO이지만 mandatory machine-readable evidence schema의 `true | false` 형식을 위반해 downstream parser/audit semantics가 불안정해진다.
- **Requirement / Contract affected:** TASK Sections 10, 11, 20 및 fail-closed evidence semantics.
- **Evidence:** Independent probe: `gate_result=SIM_NO_GO`, `C14=FAIL`, `type(authorization_snapshot.task_w1_001_authorized)=str`.
- **Recommended remediation:** P0 값이 실제 `bool`일 때만 snapshot에 복사하고, missing/malformed 값은 conservative boolean `false`와 명시적 blocker/raw-diagnostic field로 분리한다. string/int/null 각각에 대해 모든 authorization snapshot field가 boolean임을 검증하는 tests를 추가한다.

### LOW

No LOW findings.

## 5. Scope Review

- required scope implemented: PASS
- unrelated changes: PASS
- next-task leakage: PASS
- frozen boundaries preserved: PASS for canonical delta

변경은 verifier, focused tests, gate report/evidence와 TASK history에 한정된다. Smoke runtime, contract/schema, ADR, P0 evidence, Week tasks, physical integration, Dataset V1, training, hardware freeze 또는 post-review acceptance artifact는 변경되지 않았다.

## 6. Contract Review

- contract compliance: FAIL
- prior-task compatibility: PASS for canonical repository state
- public interface compatibility: FAIL — tampered direct-actuator operation을 검출하지 못함

검토한 frozen/authoritative sources는 `ADR-Simulation-Lane-v1.md`, `simulation_task_mapping_v1.md`, `system_architecture_v1.md`, `contract_plan.md`, hardware status, P0-004R, accepted SIM-001/SIM-002 profile/evidence/acceptance chain이다. Current hashes와 authorization booleans는 모두 일치하지만 C18 enforcement가 reviewed revision에 immutable하게 연결되지 않는다.

## 7. Test Adequacy

- happy paths: PASS
- invalid paths: FAIL
- boundary cases: FAIL
- invariant coverage: FAIL
- focused suite: PASS — `16 passed in 0.41s`
- full regression: PASS — `185 passed in 38.21s`

Required 15 named negative tests는 존재하지만 direct-actuator test가 실제 runtime/contract 변경 대신 SIM-001 evidence boolean만 뒤집는다. 따라서 acceptance SHA를 미검토 runtime에 맞춘 우회와 malformed P0 value type을 검증하지 못한다.

## 8. Evidence Integrity

- evidence exists: PASS
- task identity correct: PASS
- changed-file list correct: NOT APPLICABLE — evidence에 changed-file list 없음
- test claims verified: PASS for recorded commands/counts
- exit criteria verified: FAIL
- hashes verified: PASS

Independent recomputation:

- Evidence SHA-256: `430a84d5555e6e9a9e0ae1f01a680bbb47e30350b8f4060069c26800d37ed231`
- Payload SHA-256: `0582322051568429667f1f06668637ee07f5bd9eabc9f91e94295e8a6208e2a2`
- Verifier SHA-256: `167b589c06ac8f30db77b79ac4288037a0f967dd4352d3f42aa0cfc0c3f1c3e1`
- Focused tests SHA-256: `4575868257eafec24406cc8643d4f9b8b002cf8e3a6686458bfc37084e5593c2`
- Report SHA-256: `4a7116de3090a868994967eb849714ded09627f9ff855607ae5a89b44aeda20d`

Canonical evidence is internally hash-consistent, but its C18/C20 PASS semantics are materially incomplete because the independent bypass probe returns `SIM_GO` for an unreviewed direct-actuator change.

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

- Acceptance hash와 current file만 비교하고 reviewed commit blob을 확인하지 않으면 hash를 함께 갱신한 unreviewed 변경을 독립 승인으로 오인할 수 있다.
- Direct-actuator 금지는 marker field나 제한된 token blacklist가 아니라 immutable reviewed revision과 allowlisted contract semantics로 검증해야 한다.
- Fail-closed decision뿐 아니라 NO_GO evidence의 field type도 계약을 지켜야 downstream automation이 안전하게 해석할 수 있다.
- Current canonical `SIM_GO` 계산의 재현성은 verifier가 모든 필수 tampering을 차단한다는 증거가 아니다.

## 11. 최종 Recommendation

`REJECT TASK-SIM-GATE`

`TASK-SIM-GATE-REV-B01`이 mandatory actuator-ownership invariant와 independent acceptance trust chain을 우회하여 `SIM_GO`를 만들 수 있다. 해당 finding과 malformed authorization snapshot 처리를 수정하고 evidence를 재생성한 뒤 독립 재검토가 필요하다. `simulation_lane_authorized=false`를 유지하고 post-review gate acceptance를 생성해서는 안 된다.
