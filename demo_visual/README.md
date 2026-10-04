# SIMULATION_FIRST_V1 Visual Demo

JSON을 직접 보여주는 대신 accepted/live Evidence를 브라우저 대시보드로 시각화하는 read-only presentation layer입니다.

## 권장 구성

- 왼쪽: Gazebo Harmonic 또는 MuJoCo 실제 화면
- 오른쪽: Browser Visual Dashboard

Dashboard는 `Normal E2E`, `Navigation Timeout`, `Verification Uncertain`, `Final Qualification` 4개 화면을 제공합니다.

## 설치

`demo_visual/` 폴더를 프로젝트 루트에 복사하고:

```bash
chmod +x demo_visual/scripts/*.sh
source .venv-sim/bin/activate
```

## Dashboard

```bash
./demo_visual/scripts/launch_dashboard.sh
```

브라우저: `http://127.0.0.1:8765`

## Normal live

```bash
./demo_visual/scripts/run_normal_live_safe.sh
./demo_visual/scripts/replay_visual.sh normal
```

runner가 `--output`을 지원하지 않으면 detached Git worktree에서 실행해 accepted Evidence를 보호합니다.

## 대표 failure visual replay

```bash
./demo_visual/scripts/replay_visual.sh nav_timeout
./demo_visual/scripts/replay_visual.sh verify_uncertain
```

SIM-009 live suite를 `results/demo/SIM-009_failure_recovery_demo.json`에 생성해 두면 Dashboard는 그것을 우선 사용합니다. 없으면 accepted Evidence replay라고 상단에 명시합니다.

## Final Gate live

```bash
python3 scripts/verify_simulation_e2e_qualification.py --output results/demo/SIM-E2E_qualification_demo.json
./demo_visual/scripts/replay_visual.sh qualification
```

## 전체 리허설

Terminal A:
```bash
./demo_visual/scripts/launch_dashboard.sh
```
Terminal B:
```bash
./demo_visual/scripts/run_portfolio_visual.sh
```

> Dashboard visual replay는 완료된 Evidence를 설명하기 위한 시각화입니다. 실제 runtime event stream이 없는 구간을 live telemetry처럼 표현하지 않습니다.
