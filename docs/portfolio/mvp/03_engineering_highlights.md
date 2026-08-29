# Engineering Highlights

## Highlight 1. Semantic Agent output을 실행 request와 분리

### 문제

언어 모델 provider output을 바로 mission request로 사용하면, provider-specific payload와 runtime metadata가 섞이고 malformed output이 implementation exception으로 새어 나갈 수 있다.

### 제약

Day-10은 hosted provider, LangGraph, ROS 2, physical execution을 허용하지 않는다.

### 설계 판단

provider boundary는 semantic `MissionProposal`, application boundary는 validated `MissionRequest`로 분리했다. UUID·UTC timestamp·required string·positive non-boolean quantity·extra field를 strict하게 검증한다.

### 구현과 검증

`FactoryAgent`, `ModelProvider`, `DeterministicFakeProvider`, `MissionValidationError`를 사용한다. `tests/test_factory_agent.py`는 non-mapping provider output, extra field, invalid mapping key, whitespace-only field, naive timestamp, invalid UUID, invalid quantity를 fail-closed로 검증한다.

### 최종 결과

canonical Korean request는 `Brake ECU Type-B`, `1`, `Line B`로 구조화된다. 이 scope는 Agent semantic boundary에 한정되며 execution-layer command를 만들지 않는다. Evidence: [`MVP-001.json`](../../../results/mvp/MVP-001.json), commit `51a9bef`.

## Highlight 2. `UNKNOWN`을 성공으로 변환하지 않는 bounded recovery

### 문제

robot-side timeout은 physical action이 성공했는지 실패했는지 알려주지 않는다. 바로 retry하면 duplicate operation이 될 수 있고, 바로 failure로 처리하면 실제 상태를 잃는다.

### 제약

MVP는 하나의 timeout fixture와 retry budget `1`만 가진다. Agent는 physical outcome을 결정할 수 없다.

### 설계 판단

timeout은 action `UNKNOWN`, mission `RECONCILING`으로 전이한다. `get_action_status(action_id)`의 typed `FAILED + retryable=true` 결과가 있어야 `RECOVERING`과 one retry가 가능하다. non-retryable은 deterministic `ESCALATED`로 끝난다.

### 구현과 검증

`MissionRecord`, `ActionRecord`, `SingleFailureRecoveryCoordinator`, `DeterministicTimeoutRecoverySkillFake`와 transition tests가 policy를 고정한다. Evidence: [`MVP-004.json`](../../../results/mvp/MVP-004.json), commit `cbb002d`.

### 포트폴리오에서 전달할 메시지

Physical AI의 안전성은 모델이 timeout을 “판단”하게 하는 것이 아니라, ambiguous outcome을 durable state와 reconciliation protocol로 표현하는 데서 시작한다.

## Highlight 3. Persisted evidence도 fail-closed로 검증

### 문제

초기 persistence 구현은 JSONL/SQLite에 attempted-call `request_id`와 JSONL `component_version`을 충분히 남기지 않았다. valid-shaped summary만 있어도 correlation을 독립적으로 재구성하기 어려웠다.

### Review / Fix

`TASK-MVP-005` independent review는 이 누락을 `REJECT` 사유로 기록했다. fix는 immutable `AttemptedToolCall` trace, SQLite/JSONL correlation/version, validated trace에서 derive되는 `tool_call_valid`를 추가했다. re-review는 source/test/artifact SHA-256과 regression을 재검증해 `ACCEPT`했다.

### 최종 결과

SQLite는 mission/action transition과 idempotency 정보를 저장하고, restart/reload 뒤에도 `UNKNOWN`을 success로 변환하지 않는다. Evidence: [`MVP-005.json`](../../../results/mvp/MVP-005.json), commit `6561809`.

## Highlight 4. E2E wrapper의 “그럴듯한 증거” bypass를 regression으로 고정

### 문제

normal E2E에서 attempted call의 `request_id`가 typed inventory/transfer result와 달라도 evidence를 만들 수 있었고, failure E2E에서도 WMS context와 recovery artifact의 correlation을 충분히 보장하지 못했다.

### Review / Fix

`TASK-MVP-006`과 `TASK-MVP-007`은 모두 initial review에서 `REJECT`되었다. fix는 request ID, component version, timestamp, result kind, mission/action correlation을 교차 검증하고, tampered input을 각각 `PersistenceValidationError` 또는 `FailureRecoveryMissionError`로 reject하도록 했다.

### 검증

- `test_persistence_rejects_tampered_normal_run_correlation_or_tool_result`
- `test_e2e_evidence_rejects_tampered_inventory_correlation`
- final release full regression: `50 PASS`, `0 FAIL`

### 최종 결과

normal E2E는 `6e5e549`, failure/recovery E2E는 `95cb075`에 commit되었다. 이는 “테스트가 통과했다”보다, evidence가 실제 typed run과 같은 mission/action을 가리키는지를 검증한 사례다.
