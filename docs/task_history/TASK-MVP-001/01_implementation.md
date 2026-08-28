# Implementation — TASK-MVP-001

## 1. 작업 정보

- TASK: `TASK-MVP-001`
- 작업 유형: Implementation history backfill
- 실행 순번: `01`
- 원 구현 일자: `2026-08-28`
- 이력 보강 일자: `2026-08-29`
- 시작 시 Repository 상태: implementation/evidence는 Git commit과 `results/mvp/MVP-001.json`에 존재했으나 `docs/task_history/TASK-MVP-001/` 기록은 없었다.
- 선행 조건: `TASK-P0-002 = GO`
- implementation commit: `51a9bef2043ca6df4a1a81e7754c34c4bdb12279` (`feat(mvp): establish factory agent vertical slice`)
- evidence base commit: `1e7cb881e63154b6f9ffd46482bd02c26f4b074a`; evidence 생성 시점에는 MVP-001 파일이 uncommitted였으며, 이 base commit이 MVP-001 source를 포함한다고 해석하면 안 된다.

## 2. 작업 목적

단일 canonical Korean natural-language mission을 deterministic fake provider 경계에서 semantic proposal로 변환하고, deterministic application service가 runtime metadata를 소유한 validated `MissionRequest`로 만드는 최소 Factory Agent vertical slice를 구현한다.

## 3. 구현 범위

### 구현한 내용

- `MissionProvider` provider abstraction 및 `DeterministicFakeProvider`
- provider-owned semantic `MissionProposal`과 application/service-owned outer `MissionRequest`
- exact-field, mapping type/key, non-blank string, positive non-boolean integer, UUID, UTC timestamp fail-closed validation
- canonical mission `Line B에 Brake ECU Type-B 1개를 공급해줘.`의 deterministic parse
- `request_id`, `mission_id`, `requested_by`, `created_at`의 service-owned runtime metadata

### 명시적으로 구현하지 않은 내용

- WMS/Fleet/PHM implementation, Robot Skill execution, failure injection, retry, timeout/reconciliation
- persistence/SQLite, ROS 2, Nav2, MoveIt, `ros2_control`, VLA, physical robot/camera
- hosted LLM SDK, LangGraph, Docker, PostgreSQL, Grafana, multi-agent, MVP-002 이후 functionality

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `src/contracts/__init__.py` | mission contract public exports |
| `src/contracts/mission.py` | `MissionProposal`, `MissionRequest`, `MissionValidationError`와 strict schema validation |
| `src/factory_agent/__init__.py` | Factory Agent package public exports |
| `src/factory_agent/provider.py` | provider-neutral `MissionProvider` protocol |
| `src/factory_agent/fake_provider.py` | canonical mission 전용 deterministic semantic fixture |
| `src/factory_agent/service.py` | provider proposal validation과 service-owned metadata assembly |
| `tests/test_factory_agent.py` | canonical parsing, determinism, fail-closed contract regression |
| `results/mvp/MVP-001.json` | machine-readable test/evidence manifest |

## 5. 주요 구현 내용

`DeterministicFakeProvider`는 canonical natural-language input에 대해서만 `mission_type`, `part_id`, `quantity`, `destination` semantic proposal을 동일하게 반환한다. provider는 `request_id`, `mission_id`, `requested_by`, `created_at`를 생성하지 않는다.

`FactoryAgent.parse_mission()`은 먼저 untrusted provider output을 `MissionProposal.from_mapping()`으로 strict validation한 뒤, service가 만든 runtime metadata와 결합하여 `MissionRequest.from_mapping()`을 호출한다. 따라서 `None`, list, tuple, string, integer 같은 non-mapping output, invalid mapping key, missing/extra field, blank string, invalid quantity, invalid UUID, naive timestamp는 `MissionValidationError`로 fail-closed 처리된다.

출력은 execution command, ROS command, pose, trajectory, WMS call 또는 Robot Skill call을 생성하지 않는 typed structured mission에 한정된다.

## 6. 주요 설계 판단

- LLM/provider는 semantic intent proposal만 담당하고, runtime metadata와 validation ownership은 deterministic service boundary에 둔다.
- `MissionProposal`과 `MissionRequest`를 분리해 future hosted provider가 physical-operation correlation metadata를 발명하지 못하게 한다.
- deterministic fake의 reproducibility는 semantic proposal level로 한정한다. UUID/timestamp 같은 runtime metadata는 semantic determinism의 증거로 사용하지 않는다.
- strict field set validation으로 provider output의 `execution_command` 같은 extra field를 수용하지 않는다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| 당시 unit/regression test | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 16 PASS (`MVP-001.json` measured result) |
| 당시 syntax/static | `PYTHONPYCACHEPREFIX=<temporary-directory> python3 -m compileall -q src tests` | PASS (`MVP-001.json` measured result) |
| 당시 tracked/untracked whitespace 검증 | `git diff --check` 및 intended MVP-001 file마다 `git diff --no-index --check /dev/null` | PASS (`MVP-001.json` measured result) |
| 이력 보강 시 focused recheck | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests/test_factory_agent.py -v` | 16 PASS |

## 8. Exit Criteria

- canonical mission produces a valid structured mission — PASS
- fake provider is deterministic — PASS
- malformed provider output fails closed — PASS
- no robot/ROS/VLA implementation exists — PASS
- tests pass — PASS
- `git diff --check` passes — PASS (evidence의 tracked 및 intended untracked-file coverage 기준)
- evidence file exists — PASS

## 9. Evidence

- 경로: `../../../results/mvp/MVP-001.json`
- SHA-256: `a132fd21a0521530715ce5185e3ea6570eef8231bbfa88303095b800977fbd5f`
- 상태: PASS
- evidence의 source/test snapshot hash는 현재 파일과 일치한다.
  - `src/contracts/__init__.py`: `e1765420b6c8a2056cbcb3713addf0476bbc3c0b8e85a4cf907e6d05d1768c62`
  - `src/contracts/mission.py`: `9c127a891216fc1843cf95e49f2ba30e8eec3ecec0c7bd9aa6c35c6a16e3f12b`
  - `src/factory_agent/__init__.py`: `e5e5286914712d4d976569d4bd9c518cd93a6615a96c038533ea42a3e6d7babc`
  - `src/factory_agent/provider.py`: `d66a3b724190c77df0d2228dca013cf1f6c0261e850fbefc4cbb38444e35c0f8`
  - `src/factory_agent/fake_provider.py`: `ea61908bb52918e64f3d0e83404772cc4fd7d4ed96a3bb1e6d0495c67bdabf07`
  - `src/factory_agent/service.py`: `b623c97edaa41e2b3f1fac9196b1c967a5568693a3fb2a61a29c0a38a1804f93`
  - `tests/test_factory_agent.py`: `60befcaf14b8b03832dd9b5764ea480955dc057d0424e55f6defa0ab4dcabae7`

## 10. 구현 결과

`TASK-MVP-001 is complete.`

## 11. 다음 단계

독립 Read-only Review/Fix의 별도 history record는 이 backfill 범위에 포함하지 않았다. 이후 workflow가 실행될 때 해당 sequence를 별도로 추가한다.
