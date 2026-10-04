# Gazebo 3D Diagnostic Package

목적: `SIMULATION_FIRST_V1` 3D 데모에서 Gazebo GUI가 열리지만 world / robot / Entity Tree가 보이지 않는 원인을 **추측하지 않고 단계적으로 분리**합니다.

진단 순서:

```text
1. Gazebo server가 살아 있는가?
2. GUI와 server의 GZ_PARTITION / ROS_DOMAIN_ID가 같은가?
3. server 환경에서 /world/* topic이 보이는가?
4. scene / pose topic에 실제 traffic이 있는가?
5. server가 읽은 SDF에 model/include가 존재하는가?
6. GUI log에 OGRE / OpenGL / EGL / GLX 오류가 있는가?
7. server가 GUI보다 먼저 종료되는가?
```

## 사용법

가장 중요한 조건:

**Normal E2E를 실행해 Gazebo GUI와 server가 살아 있는 동안 별도 Terminal에서 이 스크립트를 실행합니다.**

Terminal 1:

```bash
cd ~/projects/factory_physical_ai_simDemo
source .venv-sim/bin/activate

./demo_3d/scripts/01_normal_e2e_3d.sh
```

`Enter`를 누르지 않은 상태를 유지합니다.

Terminal 2:

```bash
cd ~/projects/factory_physical_ai_simDemo
source .venv-sim/bin/activate

./diagnose_gazebo_3d.sh
```

결과 위치:

```text
results/demo/diagnostics/gazebo_3d_YYYYMMDD-HHMMSS/
├── SUMMARY.txt
├── REPORT.txt
├── gazebo_processes.txt
├── transport_env.txt
├── gz_topics.txt
├── gz_services.txt
├── world_topics.txt
├── scene_topics.txt
├── scene_probe.txt
├── server_world.sdf
├── sdf_summary.txt
├── gazebo_gui_normal.log
├── normal_runner.log
├── log_errors.txt
├── server_lifetime.txt
├── glxinfo.txt          # glxinfo 설치 시
└── ...
```

## 가장 중요한 결과

```bash
cat results/demo/diagnostics/gazebo_3d_*/SUMMARY.txt
```

가능한 판정:

- `TRANSPORT_ENV_MISMATCH`
- `SERVER_HAS_NO_WORLD_TRANSPORT`
- `WORLD_OR_SCENE_CONTENT_MISSING`
- `GUI_RENDERER_FAILURE`
- `GUI_NOT_POPULATING_DESPITE_LIVE_SCENE`
- `SERVER_LIFETIME_TOO_SHORT`
- `UNRESOLVED`

다음 대화에서는 `SUMMARY.txt`와 `REPORT.txt` 내용만 전달하면 됩니다.

## 주의

스크립트는 canonical Evidence를 수정하지 않습니다.

다음 명령은 사용하지 마십시오.

```bash
pkill gz
pkill -f gazebo
```

canonical simulation server까지 종료할 수 있습니다.
