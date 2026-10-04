# SIMULATION_FIRST_V1 Demo Package

이 패키지는 `TASK-SIM-001 ~ TASK-SIM-E2E` 결과를 **5~7분 포트폴리오 시연**과 **기술 검토용 live 시연**에 재사용하기 위한 얇은 demo layer입니다.

## 핵심 원칙

- `results/simulation/` 및 `results/reviews/`의 accepted artifact는 **읽기 전용**입니다.
- 새 실행 결과는 반드시 `results/demo/`에 기록합니다.
- `SIM_E2E_QUALIFIED`는 Simulation-only qualification이며 physical motion/hardware freeze/Dataset/fine-tuning 권한을 부여하지 않습니다.
- accepted Evidence를 재생하는 것은 “live fault injection”과 구분해서 설명합니다.

## 설치 위치

권장: 저장소 루트에 이 패키지의 `demo/` 폴더를 복사합니다.

```text
factory_physical_ai/
├── demo/
├── scripts/
├── tests/
├── results/
└── ...
```

## 빠른 시작

```bash
cd ~/projects/factory_physical_ai_simE2E
source .venv-sim/bin/activate

chmod +x demo/scripts/*.sh

./demo/scripts/demo_preflight.sh
./demo/scripts/demo_all.sh --portfolio
```

기술 검토용 전체 live 실행:

```bash
./demo/scripts/demo_all.sh --technical-live
```

상세한 발표 순서와 화면 전환은 `DEMO_GUIDE.md`를 참고합니다.
