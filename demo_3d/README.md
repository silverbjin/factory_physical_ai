# Simulation First — Gazebo 3D demo 1.6

The primary demo runs the real SIM-008 Normal E2E mission in Gazebo Harmonic and attaches a GUI to its runtime-owned transport. It requires live scene publication, the Brake ECU entity, rendered window evidence, mission success and cleanup before returning success.

From the repository root:

```bash
source .venv-sim/bin/activate
./demo_3d/scripts/00_preflight_3d.sh
./demo_3d/scripts/01_normal_e2e_3d.sh
./demo_3d/scripts/05_verify_3d_runtime.sh
```

One authoritative path: disposable detached worktree → resolve `headless:=True` xacro → add the installed SceneBroadcaster at world scope → unchanged SIM-008 runner → unchanged installed Nav2 launch → capture its actual `/tmp/nav2_*.sdf` → attach GUI using server `/proc` environment → verify live scene and mission → bounded cleanup.

This is **DEMO_VISUALIZATION_AUGMENTATION**. The world is augmented for presentation. The mission, Nav2, semantic state and retry logic use the existing runtime. Demo children also use the proven **DEMO_MIDDLEWARE_ADAPTATION**: an explicit UDP-only loopback FastDDS profile. This avoids the observed middleware startup stalls without changing timeouts or QoS. Existing probe observations are exported after original cleanup. The generated demo Evidence differs from frozen accepted Evidence and grants no new canonical acceptance. MuJoCo remains supporting component Evidence, without a live Gazebo coupling.

Each Normal run writes fresh proof under `results/demo/runs/<uuid>/`; `results/demo/latest_validation` points to the current invocation. Set `DEMO_VALIDATION_DIR` to an unused directory for explicit output. Reuse and simultaneous Normal invocations are refused. The package qualification proof is in `results/demo/final_validation/` and summarized in [FINAL_VALIDATION.md](FINAL_VALIDATION.md). The GUI closes when the mission ends; it is expected to disappear after cleanup.

[3D_DEMO_GUIDE.md](3D_DEMO_GUIDE.md) explains live checks and the optional failure/qualification presentations. [FINAL_ROOT_CAUSE.md](FINAL_ROOT_CAUSE.md) explains the repair. The browser HUD is optional and secondary.

Prerequisites: the existing Ubuntu/WSL ROS 2 Jazzy + Gazebo Harmonic installation, `.venv-sim`, Fuel Depot resources, GUI display access and this Git repository's accepted runtime files. This package is an overlay for this repository, not a standalone simulator distribution.
