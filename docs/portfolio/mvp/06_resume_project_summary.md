# Resume Project Summary

## A. 3-line project summary

자동차 제조 line-side parts logistics를 대상으로, 한국어 부품 공급 요청을 typed mission으로 변환하는 Factory Agent와 deterministic mission/action runtime을 구현했다. timeout을 `UNKNOWN`으로 보존하고 reconciliation 뒤 one bounded retry만 허용하는 recovery policy를 SQLite·JSONL/JSON evidence와 함께 검증했다. Day-10 MVP는 deterministic fake tool 기반 software validation이며 real robot, VLA fine-tuning, ROS 2 integration은 별도 후속 gate로 분리했다.

## B. Evidence-based bullets

- provider semantic output과 `MissionRequest` runtime ownership을 분리하고, malformed payload·extra field·invalid UUID/timestamp/quantity를 fail-closed contract test로 검증했다. (`TASK-MVP-001`, `tests/test_factory_agent.py`)
- `UNKNOWN != SUCCEEDED`를 보장하는 finite mission/action transition model과 one bounded retry·HITL escalation path를 구현했다. (`TASK-MVP-002`, `TASK-MVP-004`)
- typed WMS/Robot Skill fake gateway를 통해 `Rack A19` inventory와 correlation-aware action-status reconciliation을 연결했다. (`TASK-MVP-003`, `TASK-MVP-004`)
- SQLite lifecycle, JSONL trace, JSON summary로 canonical run을 재구성하고, independent review에서 발견된 correlation metadata gap을 immutable attempted-call trace와 regression으로 보완했다. (`TASK-MVP-005`)
- normal path와 single-timeout recovery path를 각각 E2E로 검증했으며, release manifest에 full regression `50 PASS`와 evidence validation `PASS`를 기록했다. (`TASK-MVP-006`~`008`)

## C. Technology stack

| 구분 | 완료된 MVP |
|---|---|
| Core implementation | Python, dataclasses, typed contracts, deterministic state machine, in-process fakes, SQLite |
| Testing / validation | `unittest`, focused E2E, tamper regression, JSON/JSONL parsing, SQLite reload, SHA-256 evidence verification |
| Development workflow | Git task-focused commits, TASK history, independent read-only review, `REJECT → Fix → ACCEPT` audit trail |
| Future Week scope | ROS 2/Nav2/MoveIt adapters, physical robot/camera, VLA dataset and fine-tuning/evaluation, hosted provider gate, real factory integrations |

## D. One-sentence interview hook

“로봇 스킬 timeout을 단순 실패로 처리하지 않고 `UNKNOWN` 상태와 correlation-aware reconciliation으로 모델링한 뒤, independent review가 찾아낸 evidence bypass를 tamper regression으로 고정한 프로젝트입니다.”
