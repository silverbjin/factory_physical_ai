# Factory Physical AI — Day-10 MVP

자동차 제조 line-side parts logistics를 위한 production-oriented Physical AI prototype입니다. Day-10 release는 한 개의 canonical mission과 한 개의 ambiguous Robot Skill timeout을 대상으로, deterministic runtime의 reconciliation/one-retry policy와 machine-readable evidence를 검증합니다.

```text
Operator text → Factory Agent → Deterministic Runtime → typed WMS/Robot Skill fakes → SQLite + JSONL/JSON evidence
```

Canonical mission: `Line B에 Brake ECU Type-B 1개를 공급해줘.`

normal path는 `Rack A19` inventory observation 후 one transfer로 `COMPLETED`가 됩니다. failure path는 첫 transfer timeout을 `UNKNOWN`으로 보존하고, action-status reconciliation 뒤 retryable result일 때만 한 번 retry해 `COMPLETED`가 됩니다.

Day-10에서는 Nav2, MoveIt, VLA, physical robot/camera, real WMS/MES/PHM, hosted LLM, Docker/PostgreSQL을 의도적으로 mock/defer합니다. 이는 Agent semantic boundary와 deterministic state/idempotency/persistence/evidence를 먼저 검증하기 위한 scope decision이며 physical validation이나 VLA fine-tuning, production deployment을 주장하지 않습니다.

재현 방법과 evidence 위치는 [Day-10 MVP guide](docs/mvp/day10_mvp.md)를 참고하세요. 다음 단계는 VLA readiness/fine-tuning validation과 controlled ROS integration입니다.
