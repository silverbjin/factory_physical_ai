# SIMULATION_FIRST_V1 — 3D Rendering Demo Package

이 버전은 **JSON/Dashboard 중심 데모가 아니라 실제 Gazebo 3D 렌더링을 주 화면**으로 사용하도록 설계했습니다.

## 장면별 원칙

| 장면 | 3D 표현 | 의미 |
|---|---|---|
| Normal E2E | 실제 canonical Gazebo 실행 + GUI attach | 실제 정상 mission |
| Navigation Timeout | 실제 SIM-009 Navigation fault 실행 + Gazebo GUI | timeout → unknown → reconciliation/retry |
| Verification Uncertain | live Gazebo world + 실제 Verification uncertain 평가 | uncertainty는 물리 motion보다 판정 의미가 중심 |
| Final Qualification | **paused Gazebo 3D context** + 실제 evidence-only Gate | Gate는 simulation을 실행하지 않음 |

`Final Qualification`에서 새 simulation workload를 실행하지 않는 것은 의도적입니다. `TASK-SIM-E2E`는 evidence-only Gate이기 때문입니다.

---

## 설치

프로젝트 루트에 `demo_3d/`를 복사합니다.

```bash
cd ~/projects/factory_physical_ai_simDemo
cp -a /path/to/package/demo_3d .
chmod +x demo_3d/scripts/*.sh
source .venv-sim/bin/activate
```

필요 시:

```bash
cp demo_3d/config/demo.env.example demo_3d/config/demo.env
source demo_3d/config/demo.env
```

## 1. Preflight

```bash
./demo_3d/scripts/00_preflight_3d.sh
```

확인 항목:
- canonical results tree clean
- accepted SIM-008/SIM-009/SIM-010/E2E artifacts 존재
- Gazebo CLI (`gz sim` 또는 `ign gazebo`) 탐지
- SIM-008 runner 탐지
- failure runner의 scenario-filter 지원 여부
- world file 자동 탐지 여부

## 2. HUD는 보조 화면

별도 Terminal:

```bash
./demo_3d/scripts/launch_3d_hud.sh
```

브라우저:
`http://127.0.0.1:8766`

HUD는 3D 화면을 대체하지 않고 현재 scene/decision만 표시합니다.

## 3. Normal E2E — 실제 Gazebo 3D

```bash
./demo_3d/scripts/01_normal_e2e_3d.sh
```

동작:
1. canonical runner와 같은 `GZ_PARTITION`으로 Gazebo GUI attach
2. normal E2E 실제 실행
3. runner에 `--output`이 없으면 detached Git worktree에서 안전 실행
4. 결과는 `results/demo/SIM-008_normal_e2e_demo.json`
5. accepted Evidence는 변경하지 않음

## 4. Navigation Timeout — 실제 Gazebo 3D fault

```bash
./demo_3d/scripts/02_navigation_timeout_3d.sh
```

우선순위:
1. `DEMO_NAV_TIMEOUT_COMMAND`이 설정되어 있으면 그 실제 canonical scenario command 실행
2. failure runner가 `--scenario` / `--scenario-id` / `--only`를 지원하면 `SIM009-NAV-TIMEOUT-RETRY`만 실행
3. 그렇지 않으면 full SIM-009 suite를 실제 실행하면서 Gazebo GUI attach

**발표 품질을 위해서는 1 또는 2를 권장**합니다. Full suite fallback은 시연 시간이 길 수 있습니다.

## 5. Verification Uncertain — 3D world + 실제 uncertain 평가

```bash
./demo_3d/scripts/03_verification_uncertain_3d.sh
```

대상 canonical scenario:
`SIM009-VERIFY-UNCERTAIN`

Verification uncertainty가 실제로 robot motion을 발생시키는 scenario가 아닐 수 있으므로, 이 경우 Gazebo world를 live 3D context로 유지하면서 실제 Verification evaluation을 실행합니다.

HUD에 다음 disclosure가 표시됩니다:

> 3D world is visual context when the Verification fixture itself has no physical motion.

즉 **3D context를 semantic execution으로 속이지 않습니다.**

## 6. Final Qualification — 3D context + 실제 Gate

```bash
./demo_3d/scripts/04_final_qualification_3d.sh
```

이 단계는:
- canonical world를 **paused 3D context**로 표시
- 실제 `verify_simulation_e2e_qualification.py` 실행
- 결과를 `results/demo/SIM-E2E_qualification_demo.json`에 기록
- stdout decision을 그대로 표시

중요:
`TASK-SIM-E2E` 자체는 simulator를 실행하지 않습니다. 3D 화면은 발표 맥락을 유지하기 위한 paused context입니다.

## 7. 전체 Showcase

```bash
./demo_3d/scripts/run_3d_showcase.sh
```

순서:
1. Normal E2E 3D
2. Navigation Timeout 3D
3. Verification Uncertain 3D
4. Final Qualification + paused 3D context

각 장면은 Enter 후 다음으로 넘어갑니다.


---

## v1.1 — Runtime-owned Gazebo server attach

이 패키지는 더 이상 Demo가 먼저 `GZ_PARTITION`을 만들고 `gz sim -g`를 실행하지 않습니다.

실제 실행 순서:

```text
canonical runner start
        ↓
new `gz sim ... -s ...` server 자동 탐지
        ↓
같은 polling iteration에서 /proc/<PID>/environ 캡처
        ↓
GZ_PARTITION / ROS_DOMAIN_ID / GZ_* / IGN_* 추출
        ↓
동일 transport 환경으로 `gz sim -g`
```

따라서 SIM-008/SIM-009 runner가 매 실행마다 동적으로 만드는 partition/domain을 GUI가 그대로 따라갑니다.

예:

```text
server:
  GZ_PARTITION=sim004-xxxxxxxxxxxx
  ROS_DOMAIN_ID=125

GUI:
  GZ_PARTITION=sim004-xxxxxxxxxxxx
  ROS_DOMAIN_ID=125
```

### 이전 오류가 해결되는 이유

이전 버전:

```text
GUI partition = sim-first-demo-...
server partition = sim004-...
→ 서로 다른 Transport graph
→ 검은 Gazebo viewport
```

수정 버전:

```text
server 생성
→ server 환경 캡처
→ GUI가 server partition을 상속
→ 동일 world 표시
```

`/proc/<PID>/environ`은 server 발견 즉시 읽으므로 짧은 실행이 끝난 뒤 PID가 사라지는 race도 줄였습니다.

### 실제 저장소 failure runner

다음 두 이름을 자동 탐지합니다.

```text
scripts/run_simulation_failure_recovery.py
scripts/run_simulation_failure_suite.py
```

둘 다 존재하면 임의 선택하지 않고 `DEMO_FAILURE_RUNNER` 지정이 필요합니다.


---

## v1.2 — Gazebo GUI world-load race 해결

v1.1에서는 partition/domain attach는 성공했지만 canonical runner가 매우 빠르게 완료되어,
Gazebo GUI가 world/entity graph를 수신하기 전에 runtime cleanup이 server를 종료할 수 있었습니다.

관찰 예:

```text
server  : gz sim -r -s /tmp/nav2_....sdf
GUI     : gz sim -g
attach  : same GZ_PARTITION / ROS_DOMAIN_ID
runner  : rc=0
server  : bounded cleanup으로 종료
GUI     : Entity Tree empty
```

v1.2 실행 순서:

```text
canonical runner start
        ↓
runtime-owned Gazebo server 발견
        ↓
runner parent만 SIGSTOP
        ↓
같은 partition/domain으로 GUI attach
        ↓
DEMO_GUI_WARMUP_SECONDS (기본 4초)
        ↓
runner parent SIGCONT
        ↓
실제 mission execution
        ↓
canonical bounded cleanup
```

중요:
- Gazebo/Nav2 child server 자체는 warm-up 동안 계속 살아 있습니다.
- accepted runtime/Evidence는 수정하지 않습니다.
- presentation orchestration에서 runner parent의 진행만 짧게 지연합니다.
- 기본 4초이며 최대 8초로 제한됩니다.

정상 출력 예:

```text
[3D DEMO] attached GUI to runtime-owned server \
pid=... partition=sim004-... ROS_DOMAIN_ID=... warmup=4.0s
```

GUI가 여전히 늦게 뜨면 `demo.env`에서:

```bash
export DEMO_GUI_WARMUP_SECONDS=5.0
```

정도로만 올리는 것을 권장합니다.


---

## v1.3 — Current runtime server follow

진단 결과 v1.2에는 두 문제가 있었습니다.

1. GUI가 이전 Gazebo server의 partition/domain을 유지한 채 새 server가 생성될 수 있었습니다.
2. GUI warm-up을 위해 runner parent를 `SIGSTOP`한 실행에서 `NAVIGATION_LIFECYCLE_START_FAILED`가 관찰되었습니다.

v1.3은 canonical runtime timing을 변경하지 않습니다.

```text
canonical runner
      ↓
runner process tree의 gz server 탐색
      ↓
server A 발견
      ↓
server A transport로 GUI attach + /proc 재검증
      ↓
server A 종료 / server B 생성
      ↓
stale GUI 즉시 종료
      ↓
server B transport로 새 GUI attach
      ↓
runner 완료
      ↓
canonical bounded cleanup
      ↓
GUI도 자동 종료
```

따라서 `Enter` prompt 이후 빈 Gazebo 창을 남기지 않습니다. 3D 화면은 **canonical runner가 실제로 실행되는 동안** 보여주는 것이 정상입니다.

### 시작 전에 기존 GUI를 닫아야 함

v1.3은 stale GUI 혼입을 방지하기 위해 demo 시작 전에 `gz sim -g`가 이미 실행 중이면 fail-closed합니다.

확인:

```bash
pgrep -af 'gz sim -g'
```

기존 GUI만 종료한 뒤 실행하십시오.

```bash
kill <GUI_PID>
./demo_3d/scripts/01_normal_e2e_3d.sh
```

정상적인 핵심 출력:

```text
[3D DEMO] GUI transport verified \
server_pid=... gui_pid=... \
partition=sim004-... ROS_DOMAIN_ID=...
```

runtime이 Gazebo server를 교체하면 동일 메시지가 새 PID로 다시 출력됩니다.
