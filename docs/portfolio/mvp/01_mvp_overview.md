# Day-10 MVP 개요

## 1. 문제 정의

자동차 제조 현장의 line-side 공급 요청은 언어 이해, inventory 상태, side-effecting robot action, 실패 시 재시도, 그리고 사후 설명 가능성을 함께 요구한다. 이 MVP는 그 전체 문제를 해결한다고 주장하지 않는다. 대신 한 개의 부품 공급 mission을 통해 Agent semantic boundary와 deterministic execution policy가 어떻게 분리되어야 하는지 증명한다.

## 2. Day-10 MVP 목표

canonical mission은 `Line B에 Brake ECU Type-B 1개를 공급해줘.`이다. fixture는 `Brake ECU Type-B`, quantity `1`, source `Rack A19`, destination `Line B`로 고정했다.

정상 run은 다음을 증명한다.

```text
Operator text → Factory Agent → MissionRequest → WMS fake → Robot Skill fake
→ COMPLETED → SQLite + JSONL/JSON evidence
```

실패 run은 첫 transfer timeout 후 `UNKNOWN → RECONCILING → RECOVERING → SUCCEEDED → COMPLETED`를 증명한다. retry는 정확히 한 번이며 reconciliation보다 앞설 수 없다.

## 3. 주요 제약

- Agent는 goal interpretation과 semantic proposal만 담당한다.
- schema validation, state transition, timeout/retry budget, idempotency, persistence는 deterministic code가 담당한다.
- timeout은 action success나 failure의 증거가 아니다. 같은 `action_id`를 status query로 reconcile해야 한다.
- 모든 MVP fixtures는 in-process deterministic fake다.

## 4. 구현 범위

`TASK-MVP-001`~`TASK-MVP-008`은 아래 순서로 최소 수직 슬라이스를 만들었다.

1. Factory Agent provider boundary와 `MissionRequest` validation
2. finite mission/action state model
3. typed WMS/Robot Skill gateway와 deterministic fakes
4. single timeout, reconciliation, bounded recovery
5. SQLite persistence와 reconstructable evidence
6. normal E2E
7. single-failure recovery E2E
8. reproducible release guide와 evidence validator

## 5. 명시적 비범위

실제 ROS 2 node, Nav2 map, MoveIt planning, `ros2_control`, physical robot/camera, VLA dataset·fine-tuning·inference, real factory service, hosted LLM SDK, Docker/PostgreSQL, Grafana, multi-agent는 포함하지 않는다. [frozen Day-10 scope](../../../plans/day10_mvp_scope_v1.md)가 이 확장을 별도 후속 TASK로 요구한다.

## 6. 최종 MVP 동작

normal E2E는 `src/mission_runtime/normal.py`의 `CanonicalNormalMissionExecutor`가 typed gateway를 통해 `Rack A19` inventory와 one successful transfer를 확인한 뒤 mission을 `COMPLETED`로 전이한다. failure E2E는 `src/mission_runtime/failure_recovery.py`의 `CanonicalFailureRecoveryE2EExecutor`가 기존 recovery coordinator를 조합해 frozen timeout fixture를 실행한다.

## 7. 검증 방식

- focused normal E2E: `bash scripts/run_mvp_normal.sh`
- focused failure/recovery E2E: `bash scripts/run_mvp_failure.sh`
- SHA-256 evidence check: `bash scripts/verify_mvp_evidence.sh`
- full regression: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v`

release evidence는 `50 PASS`, `0 FAIL`을 기록한다. 정확한 run manifest는 [`results/mvp/release/day10_release.json`](../../../results/mvp/release/day10_release.json)이다.

## 8. MVP에서 얻은 핵심 결과

이 MVP의 결과는 “AI가 로봇을 움직였다”가 아니다. probabilistic Agent input이 typed contract에서 멈추고, side effect는 deterministic state/policy를 통과하며, ambiguous result가 evidence와 함께 reconciliation된다는 것을 재현 가능하게 보인 것이다.
