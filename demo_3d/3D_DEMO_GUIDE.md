# 3D_DEMO_GUIDE — 5~7분 실제 시연

## 화면 배치

가장 권장:

```text
┌──────────────────────────────────────┬──────────────────────┐
│                                      │                      │
│         Gazebo 3D Rendering          │     3D Demo HUD      │
│              70%                     │        30%           │
│                                      │                      │
└──────────────────────────────────────┴──────────────────────┘
```

Gazebo가 반드시 주 화면입니다.

---

## 0:00–0:35 — Architecture

`assets/01_system_architecture.png`

설명:
- Gazebo = L2 integrated world authority
- MuJoCo = separate manipulation bench
- Final gate = Evidence reconstruction

---

## 0:35–1:50 — Normal E2E

Terminal:

```bash
./demo_3d/scripts/01_normal_e2e_3d.sh
```

관객에게 실제로 보여줄 것:
- Gazebo factory world
- robot navigation
- canonical mission의 world-state 변화
- final verified state

HUD:
- `LIVE_CANONICAL_RUN`
- phase = running → complete

설명:
“지금 보이는 것은 accepted JSON replay가 아니라 canonical Normal E2E runner의 실제 Gazebo 실행입니다.”

---

## 1:50–3:20 — Navigation Timeout

```bash
./demo_3d/scripts/02_navigation_timeout_3d.sh
```

권장: `demo.env`의 `DEMO_NAV_TIMEOUT_COMMAND`를 저장소의 실제 단일-scenario command로 한 번 bind합니다.

보여줄 것:
- navigation goal 진행
- robot이 목표를 완료하지 못하는 3D 상황
- timeout
- UNKNOWN
- original goal reconciliation
- retry authorization / next attempt

중요:
`Timeout → Retry`로 바로 설명하지 말고,
`Timeout → UNKNOWN → Reconciliation → Retry authorization` 순서로 설명합니다.

---

## 3:20–4:20 — Verification Uncertain

```bash
./demo_3d/scripts/03_verification_uncertain_3d.sh
```

3D:
- Gazebo world는 계속 live
- robot/object final state를 관객이 직접 봄

HUD:
- scenario = `SIM009-VERIFY-UNCERTAIN`
- outcome = uncertain
- decision = RECONCILE
- mission_success_committed = false

설명:
“이 장면은 robot이 더 움직이는 failure가 아니라, 현재 3D world를 관찰한 결과를 SUCCESS로 확정할 수 없는 경우입니다. 그래서 world는 live이지만 Mission은 성공 처리되지 않습니다.”

---

## 4:20–5:40 — Final Qualification

```bash
./demo_3d/scripts/04_final_qualification_3d.sh
```

3D:
- canonical Gazebo world를 paused state로 표시
- 시각적 맥락 유지

Gate:
- 실제 acceptance/hash/source-index/predicate reconstruction 실행
- 결과: `SIM_E2E_QUALIFIED`

설명:
“이 단계에서 시뮬레이션을 다시 돌리는 것은 오히려 계약 위반입니다. 화면의 3D world는 paused context이고, 오른쪽에서는 accepted Evidence만 읽어 Qualification을 수행하고 있습니다.”

---

## 5:40–6:20 — REJECT → ACCEPT

`assets/06_review_reject_to_accept.png`

마지막 메시지:
“3D로 잘 움직이는 것과 검증된 시스템은 다릅니다. 이 프로젝트는 실제 3D 실행, 장애 의미, Evidence integrity, Independent Review까지 하나로 묶었습니다.”


---

# Runtime-owned GUI attach 확인

Normal E2E 실행:

```bash
./demo_3d/scripts/01_normal_e2e_3d.sh
```

정상 attach 시 터미널에 다음 형식이 출력됩니다.

```text
[3D DEMO] attached GUI to runtime-owned server \
pid=<PID> partition=sim004-... ROS_DOMAIN_ID=<N>
```

이 출력이 보이면 별도의 `SERVER_PID` 수동 지정이나 `/proc` 명령은 필요하지 않습니다.

문제가 있을 때 확인:

```bash
pgrep -af 'gz sim|ign gazebo'
```

GUI와 server의 partition을 수동으로 맞추는 대신 `results/demo/logs/normal_runner.log`와
`results/demo/logs/gazebo_gui_normal.log`를 확인하십시오.


---

# v1.2 Normal E2E 3D 확인

```bash
source .venv-sim/bin/activate
source demo_3d/config/demo.env 2>/dev/null || true

./demo_3d/scripts/00_preflight_3d.sh
./demo_3d/scripts/01_normal_e2e_3d.sh
```

성공 기준:

```text
[3D DEMO] attached GUI to runtime-owned server ... warmup=4.0s
```

그리고 warm-up 동안 Gazebo `Entity Tree`에 world/model entity가 나타나야 합니다.

렌더링이 WSL 환경에서 늦을 때:

```bash
export DEMO_GUI_WARMUP_SECONDS=5.0
./demo_3d/scripts/01_normal_e2e_3d.sh
```

8초를 넘기지 않는 것을 권장합니다. 이 시간은 canonical runtime의 wall-clock startup budget에도 포함될 수 있기 때문입니다.


---

# v1.3 실행 원칙

Normal E2E의 Gazebo 3D는 **명령이 끝난 뒤 확인하는 화면이 아닙니다.**
canonical runner가 실행되는 동안 실제 world를 보는 화면입니다.

```bash
# 기존 GUI가 없는지 확인
pgrep -af 'gz sim -g'

# 실행
./demo_3d/scripts/01_normal_e2e_3d.sh
```

성공 판정:

```text
[3D DEMO] GUI transport verified ...
```

그리고 실행 중 Entity Tree / 3D scene이 표시되어야 합니다.

runner가 끝나면 runtime-owned Gazebo server가 bounded cleanup되므로 GUI도 자동으로 닫히는 것이 정상입니다.
