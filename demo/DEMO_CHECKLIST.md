# DEMO_CHECKLIST

## 전날
- [ ] `demo/scripts/demo_preflight.sh` PASS
- [ ] normal E2E live 실행 성공
- [ ] `SIM009-NAV-TIMEOUT-RETRY` accepted Evidence 출력 확인
- [ ] `SIM009-VERIFY-UNCERTAIN` accepted Evidence 출력 확인
- [ ] final qualification live = `SIM_E2E_QUALIFIED`
- [ ] `results/simulation/`, `results/reviews/` clean

## 발표 10분 전
- [ ] `.venv-sim` 활성화
- [ ] Terminal 글자 크기 확대
- [ ] `01`, `03`, `04`, `02`, `05`, `06` 이미지 순서 준비
- [ ] 불필요한 terminal/tab 종료
- [ ] `results/demo/` 이전 결과는 필요 시 별도 보관
- [ ] `DEMO_INTERACTIVE=1` rehearsal 1회

## 발표 중
- [ ] accepted Evidence replay와 live 실행을 구분해서 말하기
- [ ] `UNKNOWN != SUCCESS`
- [ ] `uncertain != success`
- [ ] accepted canonical Evidence는 수정하지 않음
- [ ] 최종 `SIM_E2E_QUALIFIED`
- [ ] Physical authorization = false 강조
