# SIM_BASELINE_V1 — Simulation Toolchain Baseline

> Task: `TASK-SIM-003`
> Result: `SIM_BASELINE_BLOCKED`
> Generated: `2026-09-15T15:09:28.290316Z`
> Git SHA: `ce412270fdce2975b3b688bc321dfed54936dcc3`
> Independent acceptance: `PENDING`

## Runtime result

| Runtime | Required | Measured | Status |
|---|---|---|---|
| ROS 2 | Jazzy | `jazzy` | PASS |
| Gazebo | Harmonic | `8.11.0` | PASS |
| MuJoCo | measured, headless model load + step | `None` | FAIL |
| Deterministic L0 | accepted contract + smoke regression | pytest | PASS |

## Frozen ROS/Gazebo and Nav2-facing entry points

| Package | Executable | Availability |
|---|---|---|
| `ros_gz_bridge` | `parameter_bridge` | PASS |
| `ros_gz_sim` | `gzserver` | PASS |
| `ros_gz_sim` | `create` | PASS |
| `nav2_amcl` | `amcl` | PASS |
| `nav2_behaviors` | `behavior_server` | PASS |
| `nav2_bt_navigator` | `bt_navigator` | PASS |
| `nav2_controller` | `controller_server` | PASS |
| `nav2_lifecycle_manager` | `lifecycle_manager` | PASS |
| `nav2_map_server` | `map_server` | PASS |
| `nav2_planner` | `planner_server` | PASS |

These identities are the minimum integration surface for `TASK-SIM-004`; they do not implement or execute Navigation behavior.

## Accepted predecessor bindings

| Task | Canonical path | SHA-256 |
|---|---|---|
| `TASK-SIM-C01` | `results/reviews/SIM-C01_acceptance.json` | `1aee7a19f24cf52da3a2c0b232872420aafe7f1e644ed5fb1a493a025c5ee2d5` |
| `TASK-SIM-001` | `results/reviews/SIM-001_acceptance.json` | `bf1fe8df30a73339fcdd90a5bbc3d0cf5963a0a02d538102e732054e175f5e53` |
| `TASK-SIM-002` | `results/reviews/SIM-002_acceptance.json` | `07ee8867208498719b1a5bed04fb7572a881e2e470b6d218648aaecaf5d02951` |
| `TASK-SIM-GATE` | `results/reviews/SIM-GATE_acceptance.json` | `31195148a649b142abae43fe91bc017744827615de1c3a1f662763262a0ced5a` |
| `TASK-SIM-GATE-EVIDENCE` | `results/simulation/SIM-GATE_readiness.json` | `82c837e519c37799cb5a88af14470d2b74ba5d75913e811eac752f8e80f8b312` |

## Source and simulator-input bindings

| Path | SHA-256 |
|---|---|
| `tasks/TASK-SIM-003.md` | `3e93cd85bc7903f1c1f947ad2dd817e217660f482753f068b284cd7d2349e61c` |
| `docs/contracts/simulation_execution_contract_v1.md` | `0451e9abae4cee911d9468d11e68b8bbb0e3aff1a1a2d9cf104ed64264d28caa` |
| `docs/contracts/schemas/simulation_execution_contract_v1.schema.json` | `112b1e2e0d1fefb03d7b353e8ed4d875b025fe342380d5ba1cbf050bcc7d944a` |
| `scripts/run_simulation_smoke.py` | `8a23aac92fd41fcc9b64d029df9e64fb2584d196cdbc848d81004fdde31dfce8` |
| `src/simulation_runtime/smoke.py` | `db682046baa092c36d9f1eca3bc720135a2f4ff9d969cbef90a659b567bea41a` |
| `tests/test_simulation_execution_contract.py` | `52b9e445207dd189a5dd76c2c31638b8ae90ef7c61493cc6c238313c0d945534` |
| `tests/test_simulation_smoke.py` | `c9128b6e4f670d60c61bfca5b09344cd8c697dc80742196265dcd987ec6ddb93` |
| `scripts/verify_simulation_toolchain_baseline.py` | `0d3dc91eed0b9729d836f37d544907a580949951f95330064b9f6096e3548b1b` |
| `tests/test_simulation_toolchain_baseline.py` | `fe7636a757c87e7336663a04c3b3ac77b5506c618113846498116e3b6857abd5` |
| `config/simulation/sim_baseline_empty.sdf` | `623c63b73f11eee1d6c3f2e197afdbd7cce35dccf0efc838b97d735ba1fcbe95` |
| `config/simulation/mujoco_baseline.xml` | `76c07b33fbc81474e34923372910999c0881ef1d40d63fdf2a2820cb0b85fd21` |

## Validation commands

- `baseline_verifier`: `/usr/bin/python3 scripts/verify_simulation_toolchain_baseline.py --pre-implementation-clean`
- `focused`: `/usr/bin/python3 -m pytest -q -p no:cacheprovider tests/test_simulation_toolchain_baseline.py tests/test_simulation_execution_contract.py tests/test_simulation_smoke.py`
- `deterministic_regression`: `/usr/bin/python3 -m pytest -q -p no:cacheprovider tests/test_simulation_execution_contract.py tests/test_simulation_smoke.py`

## Fidelity and authority

- `L0`: deterministic contract and lifecycle regression.
- `L1-NAV`: ROS 2 Jazzy + Gazebo Harmonic navigation component simulation.
- `L1-VLA`: MuJoCo manipulation-physics component bench.
- `L1-VERIFY`: simulator-neutral Verification adapter.
- `L2-SYSTEM`: Gazebo Harmonic authoritative integrated world.
- `dual_world_cosimulation = prohibited_v1`.
- Simulation evidence is not physical evidence and freezes no physical target.

## Blockers

- `mujoco_headless_step`

`SIM_BASELINE_READY` still requires independent acceptance before `TASK-SIM-004` or `TASK-SIM-005` becomes eligible. `SIM_BASELINE_BLOCKED` is non-authorizing.
