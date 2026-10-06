# Expected demo outcomes

이 디렉터리는 값 자체를 위조하거나 고정하기 위한 곳이 아닙니다.

Expected semantic outcomes:

```text
Normal E2E:
  task-specific result = SIM_NORMAL_E2E_READY

Navigation timeout:
  scenario = SIM009-NAV-TIMEOUT-RETRY
  timeout/unknown must reconcile before retry
  cleanup bounded
  no duplicate side effect

Verification uncertain:
  scenario = SIM009-VERIFY-UNCERTAIN
  outcome_kind = uncertain
  decision = RECONCILE
  mission_success_committed = false

Final qualification:
  stdout = SIM_E2E_QUALIFIED
```

실제 IDs, hashes, timestamps 및 run-local provenance는 실행/accepted Evidence에서 읽습니다.
