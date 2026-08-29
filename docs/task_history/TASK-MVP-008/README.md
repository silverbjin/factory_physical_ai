# TASK-MVP-008 작업 이력

## 1. TASK 개요

- TASK: `TASK-MVP-008`
- 목표: 동결된 Day-10 MVP를 기능 확장 없이 재현 가능한 portfolio release로 정리한다.
- 구현 범위: normal mission, 단일 timeout/recovery mission, evidence inspection을 위한 최소 문서·runner·validator·release manifest.
- 주요 비범위: physical robot/camera, ROS 2, Nav2, MoveIt, VLA fine-tuning/inference, real WMS/MES/PHM, hosted LLM, Docker/PostgreSQL, multi-day soak, production deployment.
- 관련 문서: `tasks/TASK-MVP-008.md`, `docs/mvp/day10_mvp.md`, `results/mvp/release/day10_release.json`.

## 2. 작업 흐름

| 순서 | 유형 | 결과 | 핵심 내용 | 상세 기록 |
|---:|---|---|---|---|
| 01 | Implementation | COMPLETE | Day-10 reproduction guide, normal/failure runner, evidence validator, release manifest를 추가했다. | `01_implementation.md` |
| 02 | Review | ACCEPT | 재현성, evidence validator, scope/limitation 문서화 및 release claim을 독립 검토했다. | `02_review.md` |

## 3. 주요 설계 / 문제 해결 포인트

- release는 새 runtime 기능을 만들지 않고, 기존 `Agent → Deterministic Runtime → typed fake tools` 경계를 문서와 실행 진입점으로 노출했다. 따라서 Agent가 raw ROS command나 actuator command를 생성하지 않는 Day-10 경계가 유지된다.
- canonical mission `Line B에 Brake ECU Type-B 1개를 공급해줘.`의 normal path와, 첫 transfer timeout 이후 reconciliation 및 one bounded retry를 수행하는 failure/recovery path를 별도 runner로 재현 가능하게 했다.
- `scripts/verify_mvp_evidence.sh`는 `results/mvp/MVP-006.json`과 `results/mvp/MVP-007.json`의 `status` 및 source/run artifact SHA-256을 확인한다. release 문서는 fixture 기반 software evidence와 물리·성능 측정의 차이를 명시한다.
- `results/mvp/release/day10_release.json`에는 검증 당시 commit `4f88083c7527abc99a9b91f95198f1844172ee19`, 50개 테스트의 PASS 결과, 그리고 알려진 제한 사항을 기계 판독 가능한 형태로 기록했다.

## 4. 검증 결과

| 검증 | 명령 | 결과 |
|---|---|---|
| Normal E2E | `bash scripts/run_mvp_normal.sh` | `3 PASS` |
| Failure/recovery E2E | `bash scripts/run_mvp_failure.sh` | `3 PASS` |
| Evidence validator | `bash scripts/verify_mvp_evidence.sh` | `PASS` |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | `50 PASS`, `0 FAIL` |
| Diff whitespace | `git diff --check` | `PASS` |

## 5. Exit Criteria

- normal path reproducible — `PASS`
- failure/recovery reproducible — `PASS`
- evidence validator passes — `PASS`
- README clearly states scope and limitations — `PASS`
- no out-of-scope feature was added — `PASS`
- full regression passes — `PASS`
- release evidence exists — `PASS`

## 6. Evidence

- Release evidence: `../../../results/mvp/release/day10_release.json` — `release_status: PASS`.
- Normal-path evidence: `../../../results/mvp/normal_e2e/latest.json` and `../../../results/mvp/MVP-006.json`.
- Failure/recovery evidence: `../../../results/mvp/failure_recovery/latest.json` and `../../../results/mvp/MVP-007.json`.
- Evidence validator: `../../../scripts/verify_mvp_evidence.sh` verifies the SHA-256 values declared by the MVP-006 and MVP-007 evidence manifests.

## 7. 최종 상태

`ACCEPT TASK-MVP-008`

## 8. 포트폴리오 요약

`TASK-MVP-008`은 Day-10 MVP를 보이는 데 필요한 최소 release surface를 만들었다. 한 제조 물류 mission과 한 번의 ambiguous timeout/recovery를 각각 재현하는 실행 경로를 제공하고, 결과는 JSON/JSONL/SQLite run artifact 및 SHA-256 검증으로 추적된다. 독립 검토에서는 scope, evidence integrity, 문서의 제한 사항, 재현 스크립트를 확인해 `ACCEPT` 결론을 받았다. 이 release는 physical robot 또는 VLA 성능을 주장하지 않으며, 이후 VLA readiness/fine-tuning과 controlled ROS integration을 별도 gate로 남긴다.

## 9. Explain TASK-MVP-008

TASK-MVP-008은 Day-10 MVP를 **재현 가능한 포트폴리오 release**로 정리한 작업입니다. 새 제품 기능은 추가하지 않았습니다.

제공한 것은 세 가지입니다.

- 정상 미션 재현: `bash scripts/run_mvp_normal.sh`
- 단일 timeout → reconciliation → 1회 retry 복구 재현: `bash scripts/run_mvp_failure.sh`
- MVP-006/007 증거의 SHA-256 검증: `bash scripts/verify_mvp_evidence.sh`

문서에는 자동차 line-side logistics 시나리오와 다음 경계를 명확히 기록했습니다.

```text
Operator text → Factory Agent → Deterministic Runtime → typed fake tools → evidence
```

Day-10 범위는 canonical mission 1개, ambiguous failure 1개, deterministic recovery 1개, evidence입니다. ROS 2, Nav2, MoveIt, VLA, physical robot/camera, 실제 WMS/MES/PHM, hosted LLM, Docker/PostgreSQL은 의도적으로 제외했습니다.

검증 결과는 normal E2E 3 PASS, failure/recovery E2E 3 PASS, 전체 회귀 50 PASS, evidence validator PASS입니다. release 증거는 [day10_release.json](/home/jinho/projects/factory_physical_ai/results/mvp/release/day10_release.json)에 기록되어 있고, 재현 안내는 [day10_mvp.md](/home/jinho/projects/factory_physical_ai/docs/mvp/day10_mvp.md)에 있습니다.

## 10. 다음 단계

Day-10 MVP release는 `ACCEPT` 상태다. 후속 VLA 또는 ROS integration은 별도 TASK와 사전 gate가 승인될 때만 시작한다.
