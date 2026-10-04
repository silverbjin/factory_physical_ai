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
