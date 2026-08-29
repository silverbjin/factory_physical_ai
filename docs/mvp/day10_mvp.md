# Day-10 MVP Release Guide

## Scenario and boundary

자동차 제조 line-side logistics mission `Line B에 Brake ECU Type-B 1개를 공급해줘.`을 대상으로 한다. Agent는 semantic `MissionRequest`만 만들고, deterministic runtime이 typed WMS/Robot Skill fake, state transition, timeout/retry budget, persistence를 소유한다. Agent가 raw ROS command, trajectory, actuator command를 만들지 않는다.

## Reproduce

```bash
bash scripts/run_mvp_normal.sh
bash scripts/run_mvp_failure.sh
bash scripts/verify_mvp_evidence.sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

## Evidence

- Normal: `results/mvp/normal_e2e/latest.json`, `results/mvp/MVP-006.json`
- Failure/recovery: `results/mvp/failure_recovery/latest.json`, `results/mvp/MVP-007.json`
- Release: `results/mvp/release/day10_release.json`

The run directories contain SQLite lifecycle state, JSONL event traces, and JSON summaries. All displayed outcomes are deterministic fixture-derived software evidence, not physical execution or performance measurements.

## Scope and limitations

The frozen MVP proves one mission, one ambiguous timeout, one deterministic reconciliation/retry recovery, and evidence. It does not validate a physical robot, camera, VLA fine-tuning/inference, Nav2, MoveIt, ROS 2, real WMS/MES/PHM, hosted model behavior, multi-day soak, or production deployment. VLA readiness/fine-tuning and controlled ROS integration are later gates.
