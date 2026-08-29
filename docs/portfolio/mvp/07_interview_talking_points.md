# Interview Talking Points

## Q. Agent와 deterministic runtime의 책임을 왜 나눴습니까?

### 30초 답변

Agent는 자연어 goal을 semantic proposal로 바꾸지만, schema validation·state transition·retry budget·persistence·side effect dispatch는 deterministic runtime이 소유합니다. 그래서 provider output이 잘못돼도 robot execution boundary까지 도달하지 않습니다.

### 2분 답변

`MissionProposal`은 의미 필드만 갖고, `MissionRequest`의 UUID와 UTC metadata는 service boundary가 부여합니다. 이후 runtime이 typed gateway result를 보고 mission/action state를 바꿉니다. 이 분리는 future hosted provider나 VLA가 들어와도 probabilistic component가 safety·idempotency를 소유하지 않게 합니다.

### 근거

- file: `src/contracts/mission.py`, `src/factory_agent/service.py`
- TASK: `TASK-MVP-001`
- test: `tests/test_factory_agent.py`
- evidence: `results/mvp/MVP-001.json`
- commit: `51a9bef`

## Q. timeout을 왜 `UNKNOWN`으로 처리했습니까?

### 30초 답변

timeout은 physical action의 success/failure 증거가 아닙니다. `UNKNOWN`으로 보존하고 같은 `action_id`를 reconciliation한 뒤에만 retry 또는 escalation을 결정합니다.

### 2분 답변

immediate retry는 동일 부품 이송을 중복할 수 있습니다. 그래서 action은 `UNKNOWN`, mission은 `RECONCILING`이 되고, typed `get_action_status`가 `FAILED + retryable=true`를 반환한 경우만 `RECOVERING`으로 진행합니다. retry budget은 caller나 Agent가 변경할 수 없고 MVP에서는 1입니다.

### 근거

- file: `src/mission_runtime/state.py`, `src/mission_runtime/recovery.py`
- TASK: `TASK-MVP-004`
- test: `tests/test_recovery.py`
- evidence: `results/mvp/MVP-004.json`
- commit: `cbb002d`

## Q. original tests가 놓친 결함은 무엇이었습니까?

### 30초 답변

valid-shaped evidence가 실제 typed tool result와 다른 `request_id`를 가리켜도 생성될 수 있었습니다. happy path는 통과했지만 correlation tampering은 테스트하지 않았습니다.

### 2분 답변

independent review가 attempted-call trace와 inventory/transfer result 간 request ID·version·timestamp correlation을 요구했습니다. 이후 persistence writer는 모든 field를 cross-check하고, mismatch는 `PersistenceValidationError`로 reject합니다. tampered run을 만드는 regression을 추가한 뒤 재검토에서 `ACCEPT`되었습니다.

### 근거

- file: `src/mission_runtime/persistence.py`
- TASK: `TASK-MVP-006`
- test: `test_persistence_rejects_tampered_normal_run_correlation_or_tool_result`
- evidence: `results/mvp/MVP-006.json`
- commit: `6e5e549`

## Q. failure E2E에서 무엇을 실제로 증명했습니까?

### 30초 답변

첫 Robot Skill attempt의 deterministic timeout, 한 번의 reconciliation, 한 번의 retry, 그리고 `COMPLETED`를 evidence로 재구성 가능하게 증명했습니다.

### 2분 답변

WMS fake는 먼저 `Rack A19`을 반환합니다. recovery coordinator는 timeout 결과를 `UNKNOWN`으로 저장하고 action status를 조회한 뒤 retryable failure일 때만 retry합니다. failure wrapper도 inventory context와 recovery artifact가 동일 mission/action을 가리키는지 fail-closed 검증합니다.

### 근거

- file: `src/mission_runtime/failure_recovery.py`
- TASK: `TASK-MVP-007`
- test: `test_e2e_evidence_rejects_tampered_inventory_correlation`
- evidence: `results/mvp/failure_recovery/latest.json`
- commit: `95cb075`

## Q. 왜 SQLite를 선택했으며, 무엇을 주장하지 않습니까?

### 30초 답변

single-process MVP의 durable mission/action evidence에는 SQLite가 충분했지만, multi-process concurrency나 production durability를 주장하지 않습니다.

### 2분 답변

SQLite는 transition, idempotency key, attempted call, trace reconstruction을 local file로 남길 수 있게 했습니다. `UNKNOWN` reload invariant도 테스트했습니다. PostgreSQL은 concurrent worker나 service topology를 검증하기 전의 후속 migration target이며, Day-10의 scope를 불필요하게 넓히지 않았습니다.

### 근거

- file: `src/mission_runtime/persistence.py`
- TASK: `TASK-MVP-005`
- test: `tests/test_persistence.py`
- evidence: `results/mvp/MVP-005.json`
- commit: `6561809`

## Q. 실제 로봇·ROS·VLA가 없는 것이 약점 아닌가요?

### 30초 답변

그렇기 때문에 completion claim을 software MVP로 제한했습니다. Day-10은 execution authority와 evidence boundary를 먼저 검증하고, physical/VLA validation은 별도 gate로 남겼습니다.

### 2분 답변

architecture는 future ROS 2 adapter, Nav2 local navigation authority, MoveIt/`ros2_control` controller authority, VLA skill boundary를 정의하지만 runtime에는 넣지 않았습니다. 이 선택은 로컬 hardware evidence 없이 physical claim을 하지 않으면서 later integration contract를 보존합니다. 다음 단계는 physical observation, VLA dataset/fine-tuning/evaluation, controlled native ROS adapter 검증입니다.

### 근거

- file: `plans/day10_mvp_scope_v1.md`, `docs/architecture/system_architecture_v1.md`
- TASK: `TASK-MVP-008`
- test: `bash scripts/verify_mvp_evidence.sh`
- evidence: `results/mvp/release/day10_release.json`
- commit: `0b8c224`

## Q. evidence integrity를 어떻게 다뤘습니까?

### 30초 답변

JSONL/JSON이 존재하는지만 보지 않고, persisted transition과 attempted-call correlation을 검증하고 source/run artifact SHA-256을 확인했습니다.

### 2분 답변

evidence writer는 caller가 준 validity flag를 신뢰하지 않습니다. immutable trace와 typed result를 cross-check한 뒤 `tool_call_valid`를 derive합니다. release validator는 MVP-006/007 manifests에 선언된 source 및 run artifact hash를 재계산합니다. 따라서 evidence는 fixture-derived이지만, 적어도 기록과 validated run의 연결은 검증합니다.

### 근거

- file: `scripts/verify_mvp_evidence.sh`, `src/mission_runtime/persistence.py`
- TASK: `TASK-MVP-005`~`TASK-MVP-008`
- test: `bash scripts/verify_mvp_evidence.sh`
- evidence: `results/mvp/MVP-005.json`, `results/mvp/MVP-006.json`, `results/mvp/MVP-007.json`
- commit: `0b8c224`
