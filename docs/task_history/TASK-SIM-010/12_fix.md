# Fix — TASK-SIM-010

- Result: NOT READY FOR INDEPENDENT RE-REVIEW
- Based on Review: `06_review.md`; resolved scope from `11_diagnosis.md`
- Evidence: BLOCKED / `results/simulation/SIM-010_observability_regression.json`
- Regression: FAIL (`PROVEN_PREEXISTING`; identical four nodes and non-empty matching signatures)
- Git history: NO HISTORY ACTION REQUIRED
- Next: PREDECESSOR_QUALIFICATION_TASK_APPROVAL
- Implementation checkpoint: `3e528e218023df76ac86c1c82d8b4833e6f064fc`
- Fresh validation: focused `23 passed`; Evidence regenerated with `source_git_sha=3e528e218023df76ac86c1c82d8b4833e6f064fc`

## Finding Results

| Finding | Severity | Status | Correction | Regression |
|---|---|---|---|---|
| SIM010-REV-001 | BLOCKER | FIXED | SIM-004/005/007/009의 명시적 정규화, applicability, 동일 시나리오 의미론 및 SIM-008 hash alias 제거 | PASS (`23 passed`) |
| SIM010-REV-002 | HIGH | FIXED | 동일 명령의 current/baseline node 및 stable signature 비교 유지 | `PROVEN_PREEXISTING` |
| PREDECESSOR_PROVENANCE_GAPS | BLOCKER | BLOCKED | 허용된 매핑 후 남은 immutable gap을 fail-closed로 유지 | BLOCKED |

## Delta

- SIM-004 asset hash와 action-keyed wall/bound authority를 결합했으며 structured `simulation_time` 부재는 유지했다.
- SIM-005 exact MuJoCo provenance를 분리하고 기존 run의 `trace_id` 부재를 유지했다.
- SIM-007 profile aggregate와 accepted failure outcome을 operation run과 분리했다.
- SIM-009 same-scenario failure/Verification 의미론과 exact version-wide backend binding을 적용하고 run-local gap을 유지했다.
- SIM-008의 단일 config hash를 `bridge_sha256`/`launch_sha256`로 중복 alias하던 동작을 제거했다.
- fresh Evidence에서 deterministic replay와 1/1 normal 및 16/16 failure coverage는 PASS이나 physics qualification은 BLOCKED다.
- Draft proposal: `docs/proposals/TASK-SIM-Q01_provenance_qualification.md` (`IMPLEMENTATION AUTHORIZED: NO`).

Final fix status: NOT READY FOR INDEPENDENT RE-REVIEW
