# VISUAL_DEMO_GUIDE

## 6분 권장 흐름

1. Architecture 30초 — `01_system_architecture.png`
2. Normal E2E 70초 — Gazebo + Dashboard `Normal E2E`
3. Navigation Timeout 80초 — Dashboard `UNKNOWN → Reconciliation → Retry`
4. Verification Uncertain 50초 — `UNCERTAIN != SUCCESS`
5. Final Gate 80초 — qualification matrix + `SIM_E2E_QUALIFIED`
6. Review REJECT → ACCEPT 30초 — `06_review_reject_to_accept.png`

## 진짜 실시간 대시보드로 확장하려면

현재 runner가 실시간 event stream을 별도 topic/file로 제공하지 않는 구간은 완료 Evidence 기반 replay입니다. 진짜 live telemetry가 필요하면 runtime을 수정하지 않고 다음 sidecar를 추가하는 것이 권장됩니다.

```text
ROS/event observer sidecar
→ read-only subscription
→ results/demo/live_events.jsonl
→ Dashboard SSE/polling
```

이 구조는 production contract나 accepted Evidence schema를 presentation 때문에 변경하지 않습니다.
