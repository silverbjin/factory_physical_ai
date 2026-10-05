# Canonical E2E qualification report

Actual non-interactive verifier result: **SIM_E2E_QUALIFIED**, exit0, stderr empty. All twenty required predicates reconstruct PASS.

Command: `python scripts/verify_simulation_e2e_qualification.py --output results/simulation/SIM-E2E-R01_qualification.json --report results/demo/resolution/track_b/continuation/B5_real_report.md` in the qualified environment. Final independent C4 rerun also returns QUALIFIED; raw stdout/stderr/JSON remain under `results/demo/resolution/track_b/continuation/C4_*`.

Canonical output: `results/simulation/SIM-E2E-R01_qualification.json`, SHA256 `f82c1241a1ac470bff467516592a5179eaba2b510dcd2c887cb5b11538516810`.

Candidate HEAD: `82b9a5e57ffd871a29b5ea60cb531e1b75e7631b`. Review binds 106 exact current canonical source/config/model/contract/test files; sorted compact-JSON manifest SHA256 `36e804685aee52c9e847cf5922ed7c9f25a4229b8e0154dfa90aec6b3a24e86e`. This is declared independent candidate-manifest authority, not a claim that dirty source exists in an accepted Git commit.

Initial failures and closure:

| Predicate/frontier | Proven cause | Correction | Result |
|---|---|---|---|
| SIM-007 required READY | Immutable predecessor genuinely BLOCKED | Fresh four-profile SIM-007-R01, independent review/new acceptance | READY |
| Predicate source ownership | Historical SIM-010 has no unique ownership index | Fresh SIM-010-R01 index binding all eight historical sources and twenty owners | PASS |
| Full regression green | Stale historical fixture provenance and SIGINT cleanup race | Exact reviewed Git fixture inputs; move child progress inside protected cleanup | PASS |
| Manipulation profile dispatch | Generic workspace destination sent to approved Navigation fixture | Separate approved line-b-drop fixture route and measured transfer-zone bench objective | PASS |
| Semantic reconstruction | Timestamp/request/source-action correlations incomplete | Reconstruct identities, completion order, backend destinations and observed hashes; negative tests | PASS |
| Complete source identity | Legacy config/ directory omitted | Include both config/ and configs/ in complete reviewed manifest | PASS |
| Fresh navigation execution | Cold CLI participant consumes five-second public action budget | Run-owned warmed ActionClient, same goal/QoS/environment/deadline and UUID-terminal proof | PASS |
| Real-xacro regression | Builder removed inherited ROS Python paths | Preserve PYTHONPATH and source installed Jazzy setup | PASS |

All failed live/profile/index artifacts and logs are retained under `results/demo/resolution/track_b/continuation/`.

- SIM-007: `results/simulation/SIM-007-R01_mission_integration.json`, SHA256 `68bfa79e46583ea863e818d28977adf65cff47cb39fc729ad15b7fd1c5d3f508`; new acceptance `results/reviews/SIM-007-R01_acceptance.json`, SHA256 `394ad1385f96d6d710c4cc37908e23f65009a807f03b81d08eeb8de2e929b005`.
- SIM-010: `results/simulation/SIM-010-R01_observability_regression.json`, SHA256 `69c789b03215005bc6e2cd3a17020ffb0f09e7b0ed3f07a3d6dc93ed00c01090`; new acceptance `results/reviews/SIM-010-R01_acceptance.json`, SHA256 `425dbe0d87a5e603aecdd7966548dc5357c03e3761f6acd3aca8ad9c10c8064c`.

Independent review: `results/demo/resolution/track_b/continuation/independent_canonical_review_final.json`, ACCEPT, no findings. Fresh full suite: **568 passed in59.62s**, exact `python -m pytest -q -p no:cacheprovider`, exit0. Regression stdout SHA256 `af065f3e18f2792b3fc78bd00414567a90a479cb8cf3b2bf91953223fdf9f275`; stderr empty SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

| Check | Expected | Actual | Evidence | Result |
|---|---|---|---|---|
| L0_contract_runtime | PASS | PASS | results/simulation/SIM-005_mujoco_vla_backend.json | PASS |
| accepted_contract_regression | PASS | PASS | results/simulation/SIM-003_baseline.json | PASS |
| cross_simulator_verification | PASS | PASS | results/simulation/SIM-006_verification_backend.json | PASS |
| dual_world_cosimulation_required | False | False | results/simulation/SIM-007-R01_mission_integration.json | PASS |
| evidence_reproducible | PASS | PASS | results/simulation/SIM-010-R01_observability_regression.json | PASS |
| forbidden_state_transition | False | False | results/simulation/SIM-009_failure_recovery.json | PASS |
| leaked_process | False | False | results/simulation/SIM-009_failure_recovery.json | PASS |
| manipulation_backend | PASS | PASS | results/simulation/SIM-005_mujoco_vla_backend.json | PASS |
| model_config_provenance | PASS | PASS | results/simulation/SIM-005_mujoco_vla_backend.json | PASS |
| normal_system_e2e | PASS | PASS | results/simulation/SIM-008_normal_system_e2e.json | PASS |
| observability_sufficient | PASS | PASS | results/simulation/SIM-010-R01_observability_regression.json | PASS |
| physical_dependency | False | False | results/simulation/SIM-009_failure_recovery.json | PASS |
| regression_green | PASS | PASS | results/simulation/SIM-010-R01_observability_regression.json | PASS |
| required_failure_cases | PASS | PASS | results/simulation/SIM-009_failure_recovery.json | PASS |
| required_manipulation_failures | PASS | PASS | results/simulation/SIM-005_mujoco_vla_backend.json | PASS |
| required_navigation_system_failures | PASS | PASS | results/simulation/SIM-009_failure_recovery.json | PASS |
| ros2_jazzy_gazebo_navigation | PASS | PASS | results/simulation/SIM-004_navigation_backend.json | PASS |
| sim_baseline_bound | PASS | PASS | results/simulation/SIM-003_baseline.json | PASS |
| timeout_reconciliation | PASS | PASS | results/simulation/SIM-004_navigation_backend.json | PASS |
| uncertain_never_auto_success | PASS | PASS | results/simulation/SIM-006_verification_backend.json | PASS |

All eight historical acceptance/Evidence bindings and accepted Git blobs remain unchanged. All original physical/training/hardware authorizations remain false. Gazebo is the integrated world, MuJoCo the component bench; no dual-world claim is added. The historical legacy evaluation remains SIM_E2E_NOT_QUALIFIED as required by immutable historical input; current qualification uses the explicit additive successor contract.

Candidate request disclosure: the fresh component mission requests declare60000ms and start after separately bounded readiness. The historical make_mission_request10000ms is a fixture default; frozen TASK-SIM-007 R2/R10 and the authoritative execution contract/schema permit1..60000ms and do not mandate that default. Actual completed mission bodies are0.009s deterministic,1.414s navigation physics and0.155s manipulation physics, all also within10s. Every component action retains its original5s limit. System Normal keeps its original30s mission request and completes9.443s. TrackA mission deadlines are unchanged. Supplemental authority review is retained separately; acceptedR01 evidence is not modified.
