# Gazebo 3D execution guide

Run from `~/projects/factory_physical_ai_simDemo`:

```bash
source .venv-sim/bin/activate
./demo_3d/scripts/00_preflight_3d.sh
./demo_3d/scripts/01_normal_e2e_3d.sh
```

The GUI starts when the runner-owned server appears. Give the renderer time to load meshes. Its Entity Tree should contain `Depot`, `brake_ecu_type_b_001` and `turtlebot4`; the world inspector names `sim008_normal_system_world`. The simulation performs the real Normal mission, including the existing VLA surrogate's semantic placement. The world is visible while the bounded mission executes. The GUI closes as the runner cleans up.

The console reports the exact server/GUI PIDs, partition and domain, followed by gates A–H. Exit code zero requires all gates. Normal does not ask for Enter, pause the runner, or extend its startup budget.

During the run, use a second terminal with the same virtual environment:

```bash
./demo_3d/scripts/05_verify_3d_runtime.sh
```

This verifier selects the recorded owned server/GUI identities and requests live scene data. After cleanup it explicitly checks completed-run proof instead. It never chooses an arbitrary server by process age.

For a new package qualification run (the output directory must be unused):

```bash
export DEMO_VALIDATION_DIR="$PWD/results/demo/final_validation"
./demo_3d/scripts/00_preflight_3d.sh
./demo_3d/scripts/01_normal_e2e_3d.sh
./demo_3d/scripts/05_verify_3d_runtime.sh --validation-dir "$DEMO_VALIDATION_DIR"
```

An explicit directory containing previous proof is refused, preserving that proof. Use a fresh directory for subsequent runs. Default Normal runs create `results/demo/runs/<uuid>/` and atomically update `results/demo/latest_validation` to the current invocation. A lock rejects simultaneous Normal runs in this checkout. Pending or failed invocation metadata cannot reuse earlier passing gates.

The directory contains exact `/proc` identities, captured SDF and SHA256, live scene response, GUI and server logs, screenshot, mission output, lifecycle report, gates and canonical hashes. The desktop screenshot is captured from the attached GUI PID's X11 window. Rendered-content detection excludes toolbar and inspector areas; the screenshot also supports direct visual inspection of the populated tree and warehouse.

The demo uses `config/fastdds_loopback.xml` with FastDDS RMW and `ROS_AUTOMATIC_DISCOVERY_RANGE=SYSTEM_DEFAULT`. Both profile variable names reference that one file; FastDDS 2.14 uses the older `FASTRTPS_DEFAULT_PROFILES_FILE`. Participants communicate on loopback with unchanged reliability/QoS and mission bounds. This is **DEMO_MIDDLEWARE_ADAPTATION**, alongside the scene augmentation; remote ROS participants are outside this local demo path. Do not replace it with `LOCALHOST`, which Jazzy RMW uses to reintroduce shared-memory transport. Actual environment/profile hash is recorded in `middleware_configuration.json`.

The runner owns fresh `ROS_DOMAIN_ID`, `GZ_PARTITION` and ROS logs. GUI attachment copies those exact values. Existing unrelated servers remain untouched. Cleanup tracks PID plus process start time, closes the owned GUI and removes the detached worktree. Any orphaned owned ROS CLI daemon is terminated within a bounded supplementary cleanup. No global kill command is used.

## Optional presentation steps

```bash
./demo_3d/scripts/02_navigation_timeout_3d.sh
./demo_3d/scripts/03_verification_uncertain_3d.sh
./demo_3d/scripts/04_final_qualification_3d.sh
```

SIM-009 has no scenario-filter CLI in this repository. Each failure entry therefore runs the real full failure suite in an isolated augmented worktree and displays the selected result. The timeout entry follows the suite's live navigation server. Verification Uncertain can display a separate presentation context **after** suite completion; it is not a second co-simulated mission world. Final Qualification reads accepted Evidence and uses a paused presentation world; it does not execute a new mission or create canonical acceptance. These optional steps are outside the Normal A–H qualification claim.

`run_3d_showcase.sh` runs preflight, Normal and the optional steps in order. `DEMO_NO_WAIT=1` skips presentation prompts. `launch_3d_hud.sh` starts an optional secondary browser HUD.

## Diagnostic boundaries

The installed example `/opt/ros/jazzy/share/ros_gz_sim_demos/worlds/default.sdf` supplies the exact SceneBroadcaster definition. Demo augmentation runs the same headless xacro transformation first, then adds that plugin to the resolved world. Nav2's later transformation is idempotent for this resolved SDF. No installed launch or canonical source is edited. A demo entry imports the unchanged worktree runner and calls its `main`; it exports existing probe measurements after the original cleanup.

If a scene service check fails, inspect `04_runtime_world.sdf`, `05_plugins.txt`, `06_services.txt` and `08_server.log` before changing anything. If the live scene is correct but the screenshot is blank, inspect `09_gui.log`; isolate GUI configuration or rendering. `LIBGL_ALWAYS_SOFTWARE=1` is available for renderer comparisons on the same runtime transport, but was not needed for the proven run.

Ground-truth controls and failed observer cycles remain under `results/demo/diagnostics/`. `demo_3d/diagnostics/test_scene_augmentation.py` tests real headless xacro preservation, rewritten Gazebo process-title discovery and read-only CLI capability discovery.
