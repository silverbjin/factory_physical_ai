# Implementation — TASK-P0-006

## 1. 작업 정보

- TASK: `TASK-P0-006`
- 작업 유형: Implementation
- 실행 순번: `01`
- 일자: 2026-09-03
- 시작 시 Repository 상태: `scripts/verify_robot_io_readiness.py`, `tests/test_verify_robot_io_readiness.py`, `results/phase0/P0-006_robot_io_readiness.json` 3개가 untracked 상태였고, 그 외 tracked diff/staged change는 없었다.
- 선행 조건: `TASK-P0-005` Independent Read-only Review `ACCEPT`; accepted evidence SHA-256 `aafe0273a3fa8d28652494ea8f72fc396247fed81c6d5ab71311ff628e646aae` 일치
- 구현 완료와 물리 readiness 결과는 분리한다. Technical implementation은 `COMPLETE`이고 physical decision은 `DEVICE_IO_BLOCKED`다.

## 2. 작업 목적

물리 motion을 전혀 명령하지 않고 robot/controller, camera, state/control path, workspace boundary, abort/E-stop, 향후 supervised teleoperation prerequisite를 재현 가능하게 판정하는 fail-closed verifier를 완성했다. 현재 host에 확정된 target declaration과 device가 없으므로 사실을 추정하거나 preferred hardware를 대체 target으로 사용하지 않고 mandatory blocker로 보존했다.

## 3. 구현 범위

### 구현한 내용

- 고정된 `/dev` pattern만 읽는 bounded device discovery
- operator declaration schema와 device-root escape 방지
- robot/stable identity/permission metadata 확인(장치 open 없음)
- 명시적으로 safe한 regular-file state snapshot에 한정된 4096-byte/timeout read
- 최대 5 frame/30초 제한을 가진 camera acquisition worker
- C01-C18 mandatory check, blocker propagation, atomic JSON output, exit code `0/2/3`
- `MEASURED`, `DECLARED_INPUT`, `DERIVED`, `DOCUMENTED`, `NOT_VERIFIED` provenance 분리
- hardware reproduction document와 risk register
- 정상/누락/permission/timeout/partial diagnostic/aggregate mismatch test

### 명시적으로 구현하지 않은 내용

- physical motion, joint/gripper/trajectory command, physical teleoperation
- Dataset V1, episode recording, SmolVLA model load/inference, training/fine-tuning
- ROS/VLA, Agent, AMR integration
- `TASK-P0-007`, `TASK-P0-004R`, 모든 Week 1 task
- accepted `TASK-P0-005` implementation/evidence 변경

## 4. 변경 파일

| 파일 | 변경 목적 |
|---|---|
| `scripts/verify_robot_io_readiness.py` | bounded non-motion discovery/probe, fail-closed aggregation, provenance, atomic evidence 구현 |
| `tests/test_verify_robot_io_readiness.py` | required happy/failure/timeout/parsing/propagation safety regression 15건 |
| `results/phase0/P0-006_robot_io_readiness.json` | canonical measured/declared/derived readiness evidence |
| `docs/hardware/robot_camera_io_readiness_v1.md` | target/topology/path/safety/reproduction/미검증 항목 문서화 |
| `plans/robot_camera_io_risks.md` | `RESOLVED`/`DEFERRED`/`BLOCKING`/`OUT_OF_SCOPE` risk disposition |
| `docs/task_history/TASK-P0-006/01_implementation.md` | 현재 implementation audit record |
| `docs/task_history/TASK-P0-006/README.md` | TASK workflow summary |
| `docs/task_history/README.md` | global TASK history index 갱신 |

## 5. 주요 구현 내용

Canonical verifier는 robot serial/controller와 vendor SDK를 열지 않는다. Device discovery는 `/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/serial/by-id/*`, `/dev/video*`, `/dev/v4l/by-id/*`만 child process에서 조회하며 explicit timeout 후 terminate/kill/join한다. 선언된 robot/camera path가 `dev_root`와 각 stable-identity root를 벗어나면 probe 전에 거부한다.

State observation은 operator가 `regular_file_snapshot` 및 `safe_read_only=true`로 선언한 regular file만 최대 4096 bytes 읽는다. Camera는 유효한 selected/readable device가 있을 때만 별도 worker에서 bounded frame count로 읽고 frame을 저장하지 않는다. 현재 canonical run에는 declaration/device가 없어 두 probe 모두 실행하지 않았다.

모든 C01-C18 check는 mandatory다. `decide_readiness()`는 check가 없거나 하나라도 `PASS`가 아니면 `DEVICE_IO_BLOCKED`를 반환한다. `validate_evidence()`가 aggregate mismatch를 verifier error로 승격하고, output은 temporary file + `fsync` + `os.replace`로 atomic write한다.

Operator declaration은 source reference를 포함하더라도 verifier가 그 내용을 독립 검증하지 않았으므로 interface/workspace provenance를 `DECLARED_INPUT`으로 유지한다. `DOCUMENTED`는 task contract에서 직접 정해진 deferred owner 같은 항목에만 사용한다.

## 6. 주요 설계 판단

- `ADR-001`의 SO-101/SO-100-class preference는 selected target이 아니므로 canonical evidence에서 `NOT_VERIFIED`로 유지했다.
- 장치 부재를 simulation이나 synthetic fixture로 대체하지 않았다. Synthetic ready path는 verifier logic unit test에만 사용하며 canonical evidence에 포함하지 않았다.
- 불명확한 vendor/network/controller query는 안전성을 실험으로 확인하지 않고 실행 경로 자체에서 제외했다.
- 구현 성공과 readiness 성공을 분리해, 올바르게 완료된 verifier가 mandatory blocker를 발견하면 exit `2`와 `DEVICE_IO_BLOCKED`를 내도록 했다.

## 7. 테스트 및 검증

| 검증 | 명령 | 결과 |
|---|---|---|
| Canonical safe run A/B | `python3 scripts/verify_robot_io_readiness.py --device-discovery-timeout-seconds 5 --camera-timeout-seconds 5 --state-timeout-seconds 2 --camera-frame-count 1` | 두 번 모두 expected exit `2`, 동일한 `DEVICE_IO_BLOCKED` semantics |
| Focused tests | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_verify_robot_io_readiness -v` | 15 PASS, 0 FAIL |
| Full regression | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v` | 68 PASS, 0 FAIL |
| Syntax | `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q scripts/verify_robot_io_readiness.py tests/test_verify_robot_io_readiness.py` | PASS |
| JSON | `python3 -m json.tool results/phase0/P0-006_robot_io_readiness.json >/dev/null` | PASS |
| Process leak | `pgrep -af '^python(3)? .*verify_robot_io_readiness\\.py'` after completion | no remaining process, PASS |
| P0-005 integrity | `sha256sum results/phase0/P0-005_vla_runtime.json` | expected hash match, PASS |
| Whitespace | `git diff --check` and per-untracked-file `git diff --no-index --check` | PASS |

## 8. Exit Criteria

- EC-01 Correct Context — PASS: P0-005 accepted, W1 unauthorized, P0-004R required.
- EC-02 Target Hardware Decision — PASS: selection unresolved and `DEVICE_IO_BLOCKED` without substitution.
- EC-03 Robot Device Discovery — PASS: bounded measured discovery completed; no candidates and blocker preserved.
- EC-04 Host Access — PASS: access remains `NOT_VERIFIED`; no permission/security change.
- EC-05 State Interface Identified — PASS: missing path classified `NOT_VERIFIED`/blocking without inference.
- EC-06 Non-Motion State Observation — PASS: unsafe/undeclared query skipped and readiness impact explicit.
- EC-07 Control Interface Identified — PASS: unresolved and no command sent.
- EC-08 Gripper Interface — PASS: applicability/path unresolved and no actuation.
- EC-09 Camera Identity — PASS: no selected/candidate camera; measured discovery separated from selection.
- EC-10 Camera Frame Acquisition — PASS: unavailable camera skipped; bounded success/failure paths tested.
- EC-11 Camera Configuration — PASS: unresolved fields recorded `NOT_VERIFIED`.
- EC-12 Workspace Constraints — PASS: missing target-specific limits recorded as mandatory blocker.
- EC-13 Abort / E-Stop Path — PASS: `NOT_VERIFIED`, no motion-test claim.
- EC-14 Teleoperation Prerequisites — PASS: explicitly `BLOCKED`; not implemented/authorized.
- EC-15 No Motion — PASS: all command flags false; no robot/controller interface opened.
- EC-16 Scope Preservation — PASS: no forbidden downstream implementation.
- EC-17 Regression Safety — PASS: 15 focused/68 full tests; P0-005 hash unchanged.
- EC-18 Evidence Integrity — PASS: JSON/report/risk/history material facts and provenance agree.
- EC-19 Repeatability — PASS: two final safe runs produced the same semantic decision/check results.
- EC-20 Final Decision — PASS: exactly `DEVICE_IO_BLOCKED`; authorization invariants explicit.

## 9. Evidence

- 경로: `../../../results/phase0/P0-006_robot_io_readiness.json`
- Evidence SHA-256: `84d627dd2b12896e5f94ee27b5617e9dff1c37642a605c6774e7c74f2a1a1749`
- Verifier SHA-256: `3378cf47993eebba7df5c7ec535d1116e66ae5a9d825baa6389c160cc1db2217`
- 상태: valid JSON, `DEVICE_IO_BLOCKED`, canonical hardware declaration 없음, mandatory unresolved blocker 15건
- Safety: robot/joint/gripper/trajectory/teleoperation command false; controller open false; camera frame persistence false
- Authorization: `TASK-W1-001 authorized: false`; `TASK-P0-004R required: true`

## 10. 구현 결과

`TASK-P0-006 is complete.`

Physical readiness decision:

`DEVICE_IO_BLOCKED`

Technical implementation completion은 실제 device readiness를 의미하지 않는다.

## 11. 다음 단계

다음 절차는 bare `TASK-P0-006` 명령을 통한 Independent Read-only Review다. 이 implementation에서 review를 수행하지 않았고 `TASK-P0-007`, `TASK-P0-004R`, Week 1 task를 시작하지 않았다.
