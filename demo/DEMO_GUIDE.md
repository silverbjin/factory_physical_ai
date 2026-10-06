# DEMO_GUIDE — SIMULATION_FIRST_V1

## 1. 시연 전에 1회 설치

패키지의 `demo/` 폴더를 프로젝트 루트에 복사합니다.

```bash
cd ~/projects/factory_physical_ai_simE2E
cp -a /path/to/SIMULATION_FIRST_V1_demo_package/demo ./demo
chmod +x demo/scripts/*.sh
```

가상환경:

```bash
source .venv-sim/bin/activate
```

저장소 위치가 자동 탐지되지 않는 경우:

```bash
export REPO_ROOT="$HOME/projects/factory_physical_ai_simE2E"
```

## 2. 반드시 먼저 실행

```bash
./demo/scripts/demo_preflight.sh
```

PASS 조건:

```text
Canonical Evidence/acceptance tree is clean.
Demo outputs will be written only under results/demo/.
Preflight PASS.
```

`results/simulation/` 또는 `results/reviews/`가 dirty이면 먼저 원인을 확인합니다. 데모를 위해 accepted artifact를 수정하지 않습니다.

---

# 3. 권장 6분 포트폴리오 시연

## 0:00–0:40 — Architecture

화면:

```text
demo/assets/01_system_architecture.png
```

설명 포인트:

```text
Gazebo = integrated L2 world authority
MuJoCo = manipulation/component bench
No live dual-world co-simulation required
```

## 0:40–1:50 — Normal E2E live

화면 전환 전에:

```text
demo/assets/03_normal_e2e.png
```

실제 실행:

```bash
./demo/scripts/demo_normal_e2e.sh --live
```

새 Evidence:

```text
results/demo/SIM-008_normal_e2e_demo.json
```

주의: canonical accepted SIM-008 Evidence를 덮어쓰지 않습니다.

리허설 또는 시간이 부족할 때:

```bash
./demo/scripts/demo_normal_e2e.sh --accepted
```

이 경우는 live 실행이 아니라 accepted Evidence replay라고 명확히 말합니다.

## 1:50–3:10 — Navigation timeout/retry

화면:

```text
demo/assets/04_failure_recovery.png
demo/assets/02_mission_lifecycle.png
```

5~7분 발표에서는 accepted SIM-009 Evidence에서 대표 scenario를 즉시 재생:

```bash
./demo/scripts/demo_navigation_timeout.sh --accepted
```

대상 scenario:

```text
SIM009-NAV-TIMEOUT-RETRY
```

설명:

```text
attempt #1
→ timeout
→ original action reconciliation
→ retry authorization
→ attempt #2
```

기술 검토에서 full suite를 live로 새로 돌리려면:

```bash
./demo/scripts/demo_navigation_timeout.sh --live-suite
```

이 명령은 `results/demo/SIM-009_failure_recovery_demo.json`을 생성한 뒤 해당 scenario만 추출합니다.

## 3:10–3:50 — Verification uncertain

```bash
./demo/scripts/demo_verification_uncertain.sh --accepted
```

대상:

```text
SIM009-VERIFY-UNCERTAIN
```

핵심 확인:

```text
outcome_kind = uncertain
expected_decision = RECONCILE
decision = RECONCILE
mission_success_committed = false
mission_state = reconciling
verification_verdict = uncertain
```

기술 검토 모드:

```bash
./demo/scripts/demo_verification_uncertain.sh --live-suite
```

## 3:50–4:30 — SIM-010 Evidence / replay / regression

화면:

```text
demo/assets/05_evidence_qualification_pipeline.png
```

명령:

```bash
./demo/scripts/demo_evidence_summary.sh
```

원문 전체 확인:

```bash
python3 demo/tools/show_sim010.py \
  results/simulation/SIM-010_observability_regression.json \
  --full | less
```

여기서는 trace correlation, failure/recovery decision, hashes, replay/regression, Simulation-only claim을 설명합니다.

## 4:30–5:30 — Final Qualification live

```bash
./demo/scripts/demo_qualification.sh --live
```

새 출력:

```text
results/demo/SIM-E2E_qualification_demo.json
```

기대 stdout:

```text
SIM_E2E_QUALIFIED
```

accepted 결과만 빠르게 보여줄 때:

```bash
./demo/scripts/demo_qualification.sh --accepted
```

## 5:30–6:00 — Review REJECT → ACCEPT

화면:

```text
demo/assets/06_review_reject_to_accept.png
```

설명:

```text
Focused tests PASS
→ independent review REJECT
→ sparse SIM-009 semantic proof 발견
→ scenario-specific semantic validation
→ adversarial tests
→ re-review ACCEPT
```

마지막 문장:

```text
정상 동작을 보여준 것이 아니라,
정상·장애·복구·Evidence·Qualification까지 검증 가능한 체계로 만들었다.
```

---

# 4. 한 번에 리허설

Evidence 중심 5~7분 rehearsal:

```bash
DEMO_INTERACTIVE=1 ./demo/scripts/demo_all.sh --portfolio
```

`Enter`를 누를 때마다 다음 단계로 진행합니다.

기술 검토 live:

```bash
DEMO_INTERACTIVE=1 ./demo/scripts/demo_all.sh --technical-live
```

기술 검토 모드는 SIM-008 normal E2E와 SIM-009 full failure suite를 실제로 다시 실행하므로 발표 시간보다 길어질 수 있습니다.

---

# 5. 결과물을 어떻게 활용하는가

| 기존 결과물 | 시연에서의 역할 |
|---|---|
| `SIM-008_normal_system_e2e.json` 또는 `SIM-008_normal_e2e.json` | 정상 Mission의 lifecycle/provenance 증거 |
| `SIM-009_failure_recovery.json` | timeout/retry, VLA failure, Verification mismatch/stale/uncertain의 canonical failure proof |
| `SIM-010_observability_regression.json` | accepted-source index, trace/replay/regression/observability proof |
| `SIM-E2E_qualification.json` | 최종 qualification matrix와 gate decision |
| `SIM-E2E_acceptance.json` | independent review ACCEPT 증거 |
| `simulation_e2e_qualification_v1.md` | 사람이 읽는 최종 qualification 보고서 |
| `01~06 PNG` | README, Case Study, 발표 화면 전환 및 기술 면접 설명 |

## 발표용과 감사용을 구분

발표 화면:
- PNG
- demo script의 요약 출력
- `SIM_E2E_QUALIFIED`

질문/기술 면접:
- canonical Evidence 원문
- Acceptance JSON
- task history review/diagnosis
- SIM-010 source index

---

# 6. 중요한 운영 규칙

절대 다음처럼 실행하지 않습니다.

```bash
python3 scripts/run_simulation_failure_suite.py \
  --output results/simulation/SIM-009_failure_recovery.json
```

accepted Evidence를 새 실행 결과로 덮어쓸 수 있기 때문입니다.

대신:

```bash
python3 scripts/run_simulation_failure_suite.py \
  --output results/demo/SIM-009_failure_recovery_demo.json
```

를 사용합니다.

동일한 원칙을 SIM-008과 SIM-E2E demo 출력에도 적용합니다.

---

# 7. 발표 직전 최종 체크

```bash
./demo/scripts/demo_preflight.sh

git status --short -- results/simulation results/reviews

./demo/scripts/demo_navigation_timeout.sh --accepted
./demo/scripts/demo_verification_uncertain.sh --accepted
./demo/scripts/demo_qualification.sh --live
```

최종적으로:

```text
SIM_E2E_QUALIFIED
```

가 나오고 canonical artifact tree가 clean이어야 합니다.
